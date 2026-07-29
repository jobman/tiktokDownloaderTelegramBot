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


if __name__ == '__main__':
    unittest.main()
