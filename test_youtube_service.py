import unittest
from unittest.mock import patch

import youtube_service


class YouTubeOptionsTests(unittest.TestCase):
    @patch('youtube_service.YOUTUBE_COOKIES_FILE', None)
    def test_does_not_use_cookies_when_not_configured(self):
        options = youtube_service._get_ydl_options()

        self.assertNotIn('cookiefile', options)

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


if __name__ == '__main__':
    unittest.main()
