from __future__ import annotations

import re
import time
from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import parse_qs, urlsplit, urlunsplit


IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp")
CONTENT_URL_PATTERN = re.compile(r"https?://[^\s<>\[\]\"']+", re.IGNORECASE)
DISCORD_ATTACHMENT_PATTERN = re.compile(
    r"/attachments/(?P<channel_id>\d+)/(?P<attachment_id>\d+)/(?P<filename>[^/?#]+)",
    re.IGNORECASE,
)
DISCORD_IMAGE_HOSTS = {"cdn.discordapp.com", "media.discordapp.net"}


def is_http_url(url: str | None) -> bool:
    """判断 URL 是否为合法的 HTTP(S) 地址。"""
    if not isinstance(url, str) or not url:
        return False
    parsed = urlsplit(url)
    return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)


def is_image_url(url: str | None) -> bool:
    """判断 HTTP(S) URL 是否指向支持的图片类型。"""
    if not is_http_url(url):
        return False
    assert url is not None
    path = urlsplit(url).path.lower()
    return path.endswith(IMAGE_EXTENSIONS)


def extract_content_image_urls(content: str | None) -> list[str]:
    """从正文提取保留完整查询参数的图片 URL。"""
    if not content:
        return []

    urls: list[str] = []
    for match in CONTENT_URL_PATTERN.finditer(content):
        candidate = match.group(0).rstrip(".,;:!?，。；：！？)")
        if is_image_url(candidate):
            urls.append(candidate)
    return urls


def discord_attachment_identity(url: str | None) -> str | None:
    """返回 Discord 附件在 cdn 与 media 域名间稳定的图片身份。"""
    if not is_http_url(url):
        return None
    assert url is not None
    parsed = urlsplit(url)
    if (parsed.hostname or "").lower() not in DISCORD_IMAGE_HOSTS:
        return None
    match = DISCORD_ATTACHMENT_PATTERN.search(parsed.path)
    if not match:
        return None
    return "attachments/{channel_id}/{attachment_id}/{filename}".format(
        channel_id=match.group("channel_id"),
        attachment_id=match.group("attachment_id"),
        filename=match.group("filename").lower(),
    )


def discord_expiry_epoch(url: str | None) -> int | None:
    """解析 Discord 签名 URL 的十六进制 ex 到期时间。"""
    if discord_attachment_identity(url) is None:
        return None
    assert url is not None
    values = parse_qs(urlsplit(url).query).get("ex")
    if not values or not values[0]:
        return None
    try:
        return int(values[0], 16)
    except (TypeError, ValueError):
        return None


def discord_expiry_remaining_seconds(
    url: str | None, *, now_epoch: float | None = None
) -> float | None:
    """返回 Discord 附件 URL 的剩余有效秒数。"""
    expiry_epoch = discord_expiry_epoch(url)
    if expiry_epoch is None:
        return None
    return expiry_epoch - (time.time() if now_epoch is None else now_epoch)


def image_url_identity(url: str | None) -> str | None:
    """按 Discord 附件身份或规范化完整 URL 返回稳定的图片去重键。"""
    if not is_http_url(url):
        return None
    assert url is not None

    # Discord 的 cdn 与 media 地址指向同一附件时必须共享身份。
    attachment_identity = discord_attachment_identity(url)
    if attachment_identity is not None:
        return f"discord:{attachment_identity}"

    # 其他图床保留路径、查询参数与片段，只规范化协议和主机大小写。
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    port = f":{parsed.port}" if parsed.port else ""
    normalized_url = urlunsplit(
        (
            parsed.scheme.lower(),
            f"{host}{port}",
            parsed.path,
            parsed.query,
            parsed.fragment,
        )
    )
    return f"url:{normalized_url}"


def deduplicate_image_urls(urls: Iterable[str]) -> list[str]:
    """按附件身份或规范化完整 URL 去重，并保留更晚到期的 Discord URL。"""
    deduped: list[str] = []
    positions: dict[str, int] = {}

    for url in urls:
        if not is_image_url(url):
            continue
        identity = discord_attachment_identity(url)
        key = image_url_identity(url)
        if key is None:
            continue
        existing_position = positions.get(key)
        if existing_position is None:
            positions[key] = len(deduped)
            deduped.append(url)
            continue

        if identity:
            candidate_expiry = discord_expiry_epoch(url)
            existing_expiry = discord_expiry_epoch(deduped[existing_position])
            if candidate_expiry is not None and (
                existing_expiry is None or candidate_expiry > existing_expiry
            ):
                deduped[existing_position] = url

    return deduped


def extract_message_image_urls(
    *, attachments: Iterable[Any], embeds: Iterable[Any], content: str | None
) -> list[str]:
    """按结构化来源优先、正文兜底的规则提取消息图片。"""
    structured_urls: list[str] = []

    for attachment in attachments:
        if isinstance(attachment, Mapping):
            content_type = str(attachment.get("content_type") or "").lower()
            filename = str(attachment.get("filename") or "").lower()
            attachment_url = attachment.get("url")
            attachment_proxy_url = attachment.get("proxy_url")
        else:
            content_type = str(getattr(attachment, "content_type", None) or "").lower()
            filename = str(getattr(attachment, "filename", None) or "").lower()
            attachment_url = getattr(attachment, "url", None)
            attachment_proxy_url = getattr(attachment, "proxy_url", None)

        is_image_attachment = content_type.startswith("image/") or filename.endswith(
            IMAGE_EXTENSIONS
        )
        if not is_image_attachment:
            continue
        if isinstance(attachment_url, str) and attachment_url:
            structured_urls.append(attachment_url)
        if isinstance(attachment_proxy_url, str) and attachment_proxy_url:
            structured_urls.append(attachment_proxy_url)

    for embed in embeds:
        for block_name in ("image", "thumbnail"):
            if isinstance(embed, Mapping):
                block = embed.get(block_name)
            else:
                block = getattr(embed, block_name, None)
            if not block:
                continue

            if isinstance(block, Mapping):
                image_url = block.get("url")
                proxy_url = block.get("proxy_url")
            else:
                image_url = getattr(block, "url", None)
                proxy_url = getattr(block, "proxy_url", None)
            if isinstance(image_url, str) and image_url:
                structured_urls.append(image_url)
            if isinstance(proxy_url, str) and proxy_url:
                structured_urls.append(proxy_url)

    structured_result = deduplicate_image_urls(structured_urls)
    if structured_result:
        return structured_result
    return deduplicate_image_urls(extract_content_image_urls(content))
