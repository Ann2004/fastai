import logging
import os
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import anyio
import httpx
from html_page_generator import AsyncPageGenerator

from env_settings import SCREENSHOT_MIME, settings
from urls import SITE_HTML_KEY, SITE_SCREENSHOT_KEY

logger = logging.getLogger("app.site_generation")

BASE_DIR = Path(__file__).resolve().parent
GENERATED_HTML = BASE_DIR / "index.html"
SCREENSHOT_CONTENT_TYPE = SCREENSHOT_MIME[settings.gotenberg.screenshot_format]


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".index-", suffix=".html", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


async def _make_screenshot(client: httpx.AsyncClient, html: str) -> bytes:
    files = {
        "files": ("index.html", html.encode("utf-8"), "text/html"),
    }
    data = {
        "width": str(settings.gotenberg.screenshot_width),
        "format": settings.gotenberg.screenshot_format,
        "waitDelay": f"{settings.gotenberg.wait_delay}s",
    }
    response = await client.post(
        "/forms/chromium/screenshot/html",
        files=files,
        data=data,
    )
    response.raise_for_status()
    return response.content


HTML_START_MARKERS = ("<!DOCTYPE", "<html")
HTML_END_MARKER = "</html>"


async def stream_generated_site(
    user_prompt: str,
    *,
    s3_client,
    gotenberg_client: httpx.AsyncClient,
) -> AsyncGenerator[str, None]:
    generator = AsyncPageGenerator(debug_mode=settings.debug)

    collected_chunks: list[str] = []
    title_printed = False

    pre_html_buffer = ""
    html_started = False
    html_finished = False

    try:
        async for chunk in generator(user_prompt):
            if not isinstance(chunk, str):
                continue

            collected_chunks.append(chunk)

            if not html_started:
                pre_html_buffer += chunk
                start_idx = -1
                for marker in HTML_START_MARKERS:
                    idx = pre_html_buffer.find(marker)
                    if idx != -1 and (start_idx == -1 or idx < start_idx):
                        start_idx = idx
                if start_idx == -1:
                    continue

                html_started = True
                tail = pre_html_buffer[start_idx:]
                pre_html_buffer = ""

                if not title_printed and generator.html_page.title:
                    logger.info("Заголовок страницы: %r", generator.html_page.title)
                    title_printed = True

                end_idx = tail.find(HTML_END_MARKER)
                if end_idx != -1:
                    yield tail[: end_idx + len(HTML_END_MARKER)]
                    html_finished = True
                    break

                yield tail
                continue

            if html_finished:
                continue

            end_idx = chunk.find(HTML_END_MARKER)
            if end_idx != -1:
                yield chunk[: end_idx + len(HTML_END_MARKER)]
                html_finished = True
                break

            yield chunk

    except anyio.get_cancelled_exc_class():
        logger.warning("Генерация отменена. Сохраняется best-effort результат.")
        raise

    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        logger.exception("Ошибка внешнего сервиса: %s", exc)
        if not html_started:
            yield "[ОШИБКА] Внешний сервис недоступен. Попробуйте позже."
        return

    except Exception:
        logger.exception("Непредвиденная ошибка генерации")
        if not html_started:
            yield "[ОШИБКА] Внутренняя ошибка генерации."
        return

    finally:
        html_to_save: str | None = None

        try:
            page = getattr(generator, "html_page", None)
            if page is not None and page.html_code:
                html_to_save = page.html_code
        except Exception:
            logger.exception("Не удалось прочитать generator.html_page.html_code")

        if not html_to_save and collected_chunks:
            html_to_save = "".join(collected_chunks)

        if html_to_save is not None:
            with anyio.CancelScope(shield=True):
                try:
                    _atomic_write_text(GENERATED_HTML, html_to_save)
                    logger.info("HTML сохранён в %s (%d байт)", GENERATED_HTML, len(html_to_save))
                except Exception:
                    logger.exception("Не удалось сохранить %s", GENERATED_HTML)

                try:
                    await s3_client.put_object(
                        Bucket=settings.s3.bucket,
                        Key=SITE_HTML_KEY,
                        Body=html_to_save.encode("utf-8"),
                        ContentType="text/html; charset=utf-8",
                        ContentDisposition="inline",
                    )
                    logger.info(
                        "HTML загружен в S3: %s/%s (%d байт)",
                        settings.s3.bucket, SITE_HTML_KEY, len(html_to_save),
                    )
                except Exception:
                    logger.exception("Не удалось загрузить HTML в S3")

                try:
                    screenshot_bytes = await _make_screenshot(gotenberg_client, html_to_save)
                    await s3_client.put_object(
                        Bucket=settings.s3.bucket,
                        Key=SITE_SCREENSHOT_KEY,
                        Body=screenshot_bytes,
                        ContentType=SCREENSHOT_CONTENT_TYPE,
                        ContentDisposition="inline",
                    )
                    logger.info(
                        "Скриншот загружен в S3: %s/%s (%d байт)",
                        settings.s3.bucket, SITE_SCREENSHOT_KEY, len(screenshot_bytes),
                    )
                except Exception:
                    logger.exception("Не удалось создать/загрузить скриншот")
        else:
            logger.warning("Нечего сохранять: генератор не вернул HTML.")
