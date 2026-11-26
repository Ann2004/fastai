from furl import furl

from env_settings import SCREENSHOT_EXT, settings


def _object_url(key: str) -> str:
    return f"{settings.s3.endpoint_url.rstrip('/')}/{settings.s3.bucket}/{key}"


def _download_object_url(key: str) -> str:
    url = furl(_object_url(key))
    url.args["response-content-disposition"] = "attachment"
    return url.url


def _screenshot_key() -> str:
    return f"screenshot.{SCREENSHOT_EXT[settings.gotenberg.screenshot_format]}"


SITE_HTML_KEY = "index.html"
SITE_SCREENSHOT_KEY = _screenshot_key()

HTML_CODE_URL = _object_url(SITE_HTML_KEY)
HTML_CODE_DOWNLOAD_URL = _download_object_url(SITE_HTML_KEY)
SCREENSHOT_URL = _object_url(SITE_SCREENSHOT_KEY)
