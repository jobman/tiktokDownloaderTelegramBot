import logging


def disable_all_logging():
    """Disable Python logging for this low-priority background service."""
    logging.disable(logging.CRITICAL)


class SilentYtDlpLogger:
    """Discard messages emitted directly by yt-dlp."""

    def debug(self, *args, **kwargs):
        pass

    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


YT_DLP_LOGGER = SilentYtDlpLogger()
