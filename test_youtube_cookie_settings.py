import os
import unittest
from unittest.mock import patch

import settings


class YouTubeCookieSettingsTests(unittest.TestCase):
    @patch.dict(os.environ, {'YOUTUBE_COOKIES_FILE': '/configured/cookies.txt'})
    @patch('settings.os.path.isfile')
    def test_explicit_configuration_takes_precedence(self, isfile):
        self.assertEqual(settings._get_youtube_cookies_file(), '/configured/cookies.txt')
        isfile.assert_not_called()

    @patch.dict(os.environ, {}, clear=True)
    @patch('settings._ENV_FILE', '/release/.env')
    @patch('settings.os.path.realpath', return_value='/shared/.env')
    @patch('settings.os.path.isfile', side_effect=[False, True])
    def test_finds_cookie_file_beside_shared_environment(self, isfile, realpath):
        self.assertEqual(
            settings._get_youtube_cookies_file(),
            os.path.join('/shared', 'www.youtube.com_cookies.txt'),
        )

    @patch.dict(os.environ, {}, clear=True)
    @patch('settings._ENV_FILE', '')
    @patch('settings.os.path.isfile', return_value=False)
    def test_allows_missing_optional_cookie_file(self, isfile):
        self.assertIsNone(settings._get_youtube_cookies_file())


if __name__ == '__main__':
    unittest.main()
