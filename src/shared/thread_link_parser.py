"""Discord thread link parsing utilities."""

import re


class ThreadLinkParser:
    """Parse Discord thread/channel links without maintaining state."""

    _THREAD_LINK_PATTERN = re.compile(
        r"^https?://(?:.*\.)?discord\.com/channels/(\d{17,20})/(\d{17,20})"
        r"(?:/\d{17,20})?/?$"
    )
    _THREAD_URL_PATTERN = re.compile(
        r"https?://(?:www\.)?discord\.com/channels/(\d+)/(\d+)"
    )

    @staticmethod
    def parse_thread_link(link: str, main_guild_id: int) -> tuple[int, int] | None:
        """Parse a Banner target URL or ID, returning ``None`` when invalid."""
        link = link.strip()
        match = ThreadLinkParser._THREAD_LINK_PATTERN.match(link)
        if match:
            return int(match.group(1)), int(match.group(2))
        if link.isdigit():
            if main_guild_id:
                return main_guild_id, int(link)
            return None
        return None

    @staticmethod
    def parse_thread_url(thread_url: str) -> tuple[int, int]:
        """Parse a Booklist Discord thread URL or raise ``ValueError``."""
        match = ThreadLinkParser._THREAD_URL_PATTERN.match(thread_url.strip())
        if not match:
            raise ValueError(
                "无效的 Discord 讨论帖 URL，格式应为: "
                "https://discord.com/channels/{guild_id}/{thread_id}"
            )
        return int(match.group(1)), int(match.group(2))
