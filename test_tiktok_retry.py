import io
import json
import unittest
from unittest.mock import MagicMock, patch

import tiktok_service


class TikTokRetryTests(unittest.TestCase):
    @patch('tiktok_service.requests.get')
    def test_resolves_short_url(self, get):
        response = MagicMock()
        response.url = 'https://www.tiktok.com/@creator/video/123?_r=1&_t=tracking'
        get.return_value.__enter__.return_value = response

        result = tiktok_service._resolve_tiktok_url('https://vt.tiktok.com/short/')

        self.assertEqual(result, 'https://www.tiktok.com/@creator/video/123')
        response.raise_for_status.assert_called_once_with()

    @patch('tiktok_service._request_with_retry')
    def test_downloads_video_from_embed_metadata(self, request):
        video_url = 'https://video.example/video.mp4'
        state = {
            'source': {
                'data': {
                    '/embed/v2/123': {
                        'videoData': {
                            'itemInfos': {'video': {'urls': [video_url]}},
                        },
                    },
                },
            },
        }
        metadata_response = MagicMock()
        metadata_response.text = (
            '<script id="__FRONTITY_CONNECT_STATE__" type="application/json">'
            f'{json.dumps(state)}'
            '</script>'
        )
        video_response = MagicMock()
        video_response.content = b'video'
        request.side_effect = [metadata_response, video_response]

        result = tiktok_service._get_tiktok_video_from_embed(
            'https://www.tiktok.com/@creator/video/123'
        )

        self.assertEqual(result, b'video')
        self.assertEqual(request.call_count, 2)
        self.assertEqual(request.call_args_list[1].args[0], video_url)

    @patch('tiktok_service.TELEGRAM_VIDEO_MAX_BYTES', 5)
    @patch('tiktok_service._request_with_retry')
    def test_prefers_embed_variant_below_telegram_limit(self, request):
        state = {
            'source': {
                'data': {
                    '/embed/v2/123': {
                        'videoData': {
                            'itemInfos': {
                                'video': {
                                    'urls': [
                                        'https://video.example/large.mp4',
                                        'https://video.example/small.mp4',
                                    ],
                                },
                            },
                        },
                    },
                },
            },
        }
        metadata_response = MagicMock()
        metadata_response.text = (
            '<script id="__FRONTITY_CONNECT_STATE__" type="application/json">'
            f'{json.dumps(state)}'
            '</script>'
        )
        large_response = MagicMock(content=b'123456')
        small_response = MagicMock(content=b'1234')
        request.side_effect = [metadata_response, large_response, small_response]

        result = tiktok_service._get_tiktok_video_from_embed(
            'https://www.tiktok.com/@creator/video/123'
        )

        self.assertEqual(result, b'1234')
        self.assertEqual(request.call_count, 3)

    @patch('tiktok_service.yt_dlp.YoutubeDL')
    @patch('tiktok_service._get_tiktok_video_from_embed', return_value=b'video')
    @patch('tiktok_service._resolve_tiktok_url')
    def test_uses_embed_before_ytdlp(self, resolve_url, get_from_embed, youtube_dl):
        resolve_url.return_value = 'https://www.tiktok.com/@creator/video/123'

        result = tiktok_service.get_tiktok_video_by_yt_dlp('https://vt.tiktok.com/short/')

        self.assertEqual(result, b'video')
        get_from_embed.assert_called_once_with(resolve_url.return_value)
        youtube_dl.assert_not_called()

    @patch('tiktok_service.YT_DLP_DOWNLOAD_ATTEMPTS', 8)
    @patch('tiktok_service.time.sleep')
    @patch('tiktok_service.os.remove')
    @patch('tiktok_service.open', return_value=io.BytesIO(b'video'))
    @patch('tiktok_service._find_downloaded_file')
    @patch('tiktok_service._remove_downloaded_files')
    @patch('tiktok_service._get_tiktok_video_from_embed', side_effect=ValueError('blocked'))
    @patch('tiktok_service._resolve_tiktok_url')
    @patch('tiktok_service.yt_dlp.YoutubeDL')
    def test_reuses_session_until_download_succeeds(
        self,
        youtube_dl,
        resolve_url,
        get_from_embed,
        remove_downloaded_files,
        find_downloaded_file,
        open_file,
        remove_file,
        sleep,
    ):
        resolved_url = 'https://www.tiktok.com/@creator/video/123'
        resolve_url.return_value = resolved_url
        ydl = youtube_dl.return_value.__enter__.return_value
        ydl.extract_info.side_effect = [RuntimeError('blocked'), RuntimeError('blocked'), None]
        find_downloaded_file.side_effect = [None, None, 'downloaded_tiktok_video']

        result = tiktok_service.get_tiktok_video_by_yt_dlp('https://vt.tiktok.com/short/')

        self.assertEqual(result, b'video')
        youtube_dl.assert_called_once()
        self.assertEqual(ydl.extract_info.call_count, 3)
        ydl.extract_info.assert_called_with(resolved_url, download=True)
        self.assertEqual(sleep.call_args_list[0].args, (1.0,))
        self.assertEqual(sleep.call_args_list[1].args, (1.5,))
        remove_file.assert_called_once_with('downloaded_tiktok_video')
        selected_format = youtube_dl.call_args.args[0]['format']
        self.assertIn('filesize<', selected_format)
        self.assertIn('filesize_approx<', selected_format)


class TikTokSizeTests(unittest.TestCase):
    @patch('tiktok_service.TELEGRAM_VIDEO_MAX_BYTES', 5)
    @patch('tiktok_service._compress_video_bytes', return_value=b'small')
    def test_compresses_video_above_telegram_limit(self, compress):
        result = tiktok_service._ensure_tiktok_video_size(b'123456')

        self.assertEqual(result, b'small')
        compress.assert_called_once_with(b'123456')

    @patch('tiktok_service.TELEGRAM_VIDEO_MAX_BYTES', 5)
    @patch('tiktok_service._compress_video_bytes')
    def test_keeps_video_below_telegram_limit(self, compress):
        result = tiktok_service._ensure_tiktok_video_size(b'12345')

        self.assertEqual(result, b'12345')
        compress.assert_not_called()

    def test_calculates_bitrates_with_container_headroom(self):
        video_bitrate, audio_bitrate = tiktok_service._target_bitrates(
            duration=60,
            max_bytes=48_000_000,
        )

        self.assertGreater(video_bitrate, 100_000)
        self.assertEqual(audio_bitrate, 96_000)
        self.assertLessEqual(
            (video_bitrate + audio_bitrate) * 60,
            48_000_000 * 8 * 0.90,
        )


if __name__ == '__main__':
    unittest.main()
