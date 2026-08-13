import unittest
from unittest.mock import MagicMock, patch

import youtube_service


class YouTubeOptionsTests(unittest.TestCase):
    @patch('youtube_service.YOUTUBE_COOKIES_FILE', None)
    def test_does_not_use_cookies_when_not_configured(self):
        options = youtube_service._get_ydl_options()

        self.assertNotIn('cookiefile', options)
        self.assertEqual(options['js_runtimes'], {'node': {}})

    @patch('youtube_service.os.path.isfile', return_value=True)
    @patch('youtube_service.YOUTUBE_COOKIES_FILE', '/run/secrets/youtube-cookies.txt')
    def test_uses_configured_cookie_file(self, isfile):
        options = youtube_service._get_ydl_options()

        self.assertEqual(
            options['cookiefile'],
            '/run/secrets/youtube-cookies.txt',
        )
        isfile.assert_called_once_with('/run/secrets/youtube-cookies.txt')

    @patch('youtube_service.os.path.isfile', return_value=False)
    @patch('youtube_service.YOUTUBE_COOKIES_FILE', '/missing/youtube-cookies.txt')
    def test_rejects_missing_cookie_file(self, isfile):
        with self.assertRaisesRegex(FileNotFoundError, 'YouTube cookies file not found'):
            youtube_service._get_ydl_options()

        isfile.assert_called_once_with('/missing/youtube-cookies.txt')


class YouTubeDownloadTests(unittest.TestCase):
    @patch('youtube_service.YouTube')
    def test_downloads_progressive_stream_with_pytubefix(self, youtube):
        stream = MagicMock()
        stream.stream_to_buffer.side_effect = lambda buffer: buffer.write(b'video')
        youtube.return_value.streams.get_highest_resolution.return_value = stream

        result = youtube_service._get_youtube_video_with_pytubefix(
            'https://www.youtube.com/shorts/video-id'
        )

        self.assertEqual(result, b'video')
        youtube.assert_called_once_with(
            'https://www.youtube.com/shorts/video-id',
            client='ANDROID_VR',
        )
        stream.stream_to_buffer.assert_called_once()

    @patch('youtube_service.YOUTUBE_PYTUBEFIX_ATTEMPTS', 3)
    @patch('youtube_service.time.sleep')
    @patch(
        'youtube_service._download_with_pytubefix_client',
        side_effect=[RuntimeError('bot'), RuntimeError('blocked'), b'video'],
    )
    def test_retries_pytubefix_with_alternate_clients(self, download, sleep):
        url = 'https://www.youtube.com/shorts/video-id'

        result = youtube_service._get_youtube_video_with_pytubefix(url)

        self.assertEqual(result, b'video')
        self.assertEqual(
            [call.args for call in download.call_args_list],
            [(url, 'ANDROID_VR'), (url, 'WEB'), (url, 'ANDROID_VR')],
        )
        self.assertEqual(sleep.call_count, 2)

    @patch('youtube_service._get_youtube_video_with_yt_dlp', return_value=b'fallback')
    @patch(
        'youtube_service._get_youtube_video_with_pytubefix',
        side_effect=RuntimeError('blocked'),
    )
    def test_falls_back_to_yt_dlp(self, pytubefix_download, yt_dlp_download):
        url = 'https://www.youtube.com/shorts/video-id'

        result = youtube_service.get_youtube_video(url)

        self.assertEqual(result, b'fallback')
        pytubefix_download.assert_called_once_with(url)
        yt_dlp_download.assert_called_once_with(url)


if __name__ == '__main__':
    unittest.main()
