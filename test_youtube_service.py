import os
import unittest
from unittest.mock import MagicMock, mock_open, patch

import youtube_service


class YouTubeOptionsTests(unittest.TestCase):
    @patch('youtube_service._get_node_runtime_options', return_value={})
    @patch('youtube_service.YOUTUBE_COOKIES_FILE', None)
    def test_does_not_use_cookies_when_not_configured(self, runtime):
        options = youtube_service._get_ydl_options()

        self.assertNotIn('cookiefile', options)
        self.assertEqual(options['js_runtimes'], {'node': {}})

    @patch('youtube_service._get_node_runtime_options', return_value={'path': '/bundled/node'})
    @patch('youtube_service.os.path.isfile', return_value=True)
    @patch('youtube_service.YOUTUBE_COOKIES_FILE', '/run/secrets/youtube-cookies.txt')
    def test_uses_configured_cookie_file(self, isfile, runtime):
        options = youtube_service._get_ydl_options()

        self.assertEqual(
            options['cookiefile'],
            '/run/secrets/youtube-cookies.txt',
        )
        isfile.assert_called_once_with('/run/secrets/youtube-cookies.txt')
        self.assertEqual(options['js_runtimes'], {'node': {'path': '/bundled/node'}})

    @patch('youtube_service._get_node_runtime_options', return_value={})
    @patch('youtube_service.os.path.isfile', return_value=False)
    @patch('youtube_service.YOUTUBE_COOKIES_FILE', '/missing/youtube-cookies.txt')
    def test_rejects_missing_cookie_file(self, isfile, runtime):
        with self.assertRaisesRegex(FileNotFoundError, 'YouTube cookies file not found'):
            youtube_service._get_ydl_options()

        isfile.assert_called_once_with('/missing/youtube-cookies.txt')


class NodeRuntimeTests(unittest.TestCase):
    @patch('youtube_service.os.path.isfile', return_value=True)
    @patch('youtube_service.os.name', 'posix')
    @patch('youtube_service.nodejs_wheel.__file__', '/packages/nodejs_wheel/__init__.py')
    def test_prefers_bundled_node_on_linux(self, isfile):
        executable = os.path.join('/packages/nodejs_wheel', 'bin', 'node')
        self.assertEqual(youtube_service._get_node_runtime_options(), {'path': executable})
        isfile.assert_called_once_with(executable)

    @patch('youtube_service.os.path.isfile', return_value=True)
    @patch('youtube_service.os.name', 'nt')
    @patch('youtube_service.nodejs_wheel.__file__', 'C:/packages/nodejs_wheel/__init__.py')
    def test_prefers_bundled_node_on_windows(self, isfile):
        executable = os.path.join('C:/packages/nodejs_wheel', 'node.exe')
        self.assertEqual(youtube_service._get_node_runtime_options(), {'path': executable})
        isfile.assert_called_once_with(executable)

    @patch('youtube_service.os.path.isfile', return_value=False)
    def test_falls_back_to_path_if_bundled_executable_is_missing(self, isfile):
        self.assertEqual(youtube_service._get_node_runtime_options(), {})


class YouTubeDownloadTests(unittest.TestCase):
    @patch('youtube_service._get_ydl_options', return_value={'format': 'best'})
    @patch('youtube_service._download_with_yt_dlp_options')
    def test_retries_403_with_hls(self, download, options):
        download.side_effect = [
            youtube_service.yt_dlp.utils.DownloadError('HTTP Error 403: Forbidden'),
            b'hls-video',
        ]
        result = youtube_service._get_youtube_video_with_yt_dlp('url')
        self.assertEqual(result, b'hls-video')
        self.assertEqual(download.call_count, 2)
        fallback_options = download.call_args.args[1]
        self.assertEqual(fallback_options['format'], youtube_service.YOUTUBE_HLS_FORMAT)
        self.assertEqual(fallback_options['merge_output_format'], 'mp4')
        self.assertFalse(fallback_options['skip_unavailable_fragments'])

    @patch('youtube_service._get_ydl_options', return_value={'format': 'best'})
    @patch('youtube_service._download_with_yt_dlp_options')
    def test_does_not_retry_unrelated_errors_with_hls(self, download, options):
        download.side_effect = youtube_service.yt_dlp.utils.DownloadError('Video unavailable')
        with self.assertRaises(youtube_service.yt_dlp.utils.DownloadError):
            youtube_service._get_youtube_video_with_yt_dlp('url')
        download.assert_called_once()

    @patch('youtube_service.open', new_callable=mock_open, read_data=b'video')
    @patch('youtube_service.yt_dlp.YoutubeDL')
    @patch('youtube_service.tempfile.TemporaryDirectory')
    def test_download_uses_temporary_directory_and_final_filename(self, directory, youtube_dl, video):
        directory.return_value.__enter__.return_value = '/temporary'
        downloader = youtube_dl.return_value.__enter__.return_value
        downloader.extract_info.return_value = {'id': 'video', 'ext': 'mp4'}
        downloader.prepare_filename.return_value = '/temporary/video.mp4'
        result = youtube_service._download_with_yt_dlp_options('url', {'format': 'best'})
        self.assertEqual(result, b'video')
        self.assertEqual(
            youtube_dl.call_args.args[0]['outtmpl'],
            os.path.join('/temporary', '%(id)s.%(ext)s'),
        )
        video.assert_called_once_with('/temporary/video.mp4', 'rb')
        directory.return_value.__exit__.assert_called_once()

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
            client='MWEB',
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
            [(url, 'MWEB'), (url, 'ANDROID_VR'), (url, 'MWEB')],
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
