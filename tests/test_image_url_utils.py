import time

from shared.image_url_utils import (
    discord_attachment_identity,
    extract_message_image_urls,
)


def _discord_url(host: str, expiry_epoch: int) -> str:
    """构造带签名参数的 Discord 附件 URL。"""
    return (
        f"https://{host}/attachments/123/456/cover.png"
        f"?ex={expiry_epoch:x}&is=abc&hm=signature"
    )


def test_structured_images_skip_content_and_keep_later_attachment_url():
    """结构化图片存在时不扫描正文，并保留同一附件更晚的签名。"""
    now = int(time.time())
    earlier = _discord_url("cdn.discordapp.com", now + 300)
    later = _discord_url("media.discordapp.net", now + 600)

    result = extract_message_image_urls(
        attachments=[
            {
                "filename": "cover.png",
                "content_type": "image/png",
                "url": earlier,
                "proxy_url": later,
            }
        ],
        embeds=[],
        content="https://example.com/ignored.jpg?keep=this",
    )

    assert result == [later]
    assert discord_attachment_identity(earlier) == discord_attachment_identity(later)


def test_content_fallback_preserves_complete_query_string():
    """没有结构化图片时正文兜底保留完整签名参数。"""
    url = "https://cdn.example.com/picture.webp?ex=abc&is=def&hm=ghi"
    result = extract_message_image_urls(
        attachments=[], embeds=[], content=f"正文图片：{url}。"
    )
    assert result == [url]


def test_image_embed_is_structured_and_suppresses_content_fallback():
    """可用 image embed 属于结构化来源，并阻止正文图片混入。"""
    embed_url = "https://images.example.com/embed.jpeg?size=large"
    result = extract_message_image_urls(
        attachments=[],
        embeds=[{"image": {"url": embed_url}}],
        content="https://images.example.com/content.png?should=be-ignored",
    )
    assert result == [embed_url]


def test_empty_message_returns_empty_list():
    """无图片消息保存为空数组所需的提取结果。"""
    assert extract_message_image_urls(attachments=[], embeds=[], content="纯文本") == []
