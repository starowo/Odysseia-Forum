"""测试 Banner 系统的 TextChannel 支持。

覆盖：Channel 模型、parse_thread_link、BannerApplicationRequest 兼容、
BannerService 自动检测 target_type。"""

import os
import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from api.v1.schemas.banner import BannerApplicationRequest
from banner.banner_service import BannerService
from banner.dto.application_result import ApplicationResult
from banner.views.application_form_modal import ApplicationFormModal
from models import BannerApplication, BannerCarousel, BannerWaitlist
from models.channel import Channel as ChannelModel
from shared.enum import ApplicationStatus, TargetType


class TestTargetType:
    """TargetType 枚举测试。"""

    def test_thread_value(self):
        assert TargetType.THREAD.value == 1

    def test_channel_value(self):
        assert TargetType.CHANNEL.value == 2

    def test_int_convertible(self):
        """IntEnum 可与 int 直接比较。"""
        assert TargetType.THREAD == 1
        assert TargetType.CHANNEL == 2


class TestChannelModel:
    """Channel 模型测试。"""

    @pytest.mark.asyncio
    async def test_create_channel(self, db_session_factory):
        """创建 Channel 记录并查询。"""
        async with db_session_factory() as session:
            channel = ChannelModel(
                channel_id=1374474903981527082,
                guild_id=1134557553011998840,
                name="赛事频道A",
                topic="某赛事讨论频道",
                category_id=1234567890123456789,
            )
            session.add(channel)
            await session.commit()
            await session.refresh(channel)

            assert channel.id is not None
            assert channel.name == "赛事频道A"
            assert channel.topic == "某赛事讨论频道"
            assert channel.category_id == 1234567890123456789
            assert channel.created_at is not None

    @pytest.mark.asyncio
    async def test_channel_unique_constraint(self, db_session_factory):
        """channel_id 唯一约束：重复插入应失败。"""
        async with db_session_factory() as session:
            c1 = ChannelModel(
                channel_id=1234567890123456789,
                guild_id=1,
                name="dup",
            )
            session.add(c1)
            await session.commit()

            c2 = ChannelModel(
                channel_id=1234567890123456789,
                guild_id=2,
                name="dup2",
            )
            session.add(c2)
            with pytest.raises(Exception):
                await session.commit()

    @pytest.mark.asyncio
    async def test_channel_created_at_auto_set(self, db_session_factory):
        """created_at 自动填充。"""
        async with db_session_factory() as session:
            channel = ChannelModel(
                channel_id=1,
                guild_id=1,
                name="test",
            )
            session.add(channel)
            await session.commit()
            await session.refresh(channel)
            assert channel.created_at is not None
            assert isinstance(channel.created_at, datetime)


class TestParseThreadLink:
    """parse_thread_link 解析测试。"""

    def _parse(self, link: str, main_guild_id: int = 1134557553011998840):
        from shared.thread_link_parser import ThreadLinkParser

        return ThreadLinkParser.parse_thread_link(link, main_guild_id)

    def test_full_url(self):
        """完整 Discord URL 解析。"""
        result = self._parse(
            "https://discord.com/channels/1134557553011998840/1234567890123456789"
        )
        assert result == (1134557553011998840, 1234567890123456789)

    def test_full_url_with_trailing_slash(self):
        result = self._parse(
            "https://discord.com/channels/1111111111111111111/2222222222222222222/"
        )
        assert result == (1111111111111111111, 2222222222222222222)

    def test_canary_url(self):
        """canary.discord.com 域名。"""
        result = self._parse(
            "https://canary.discord.com/channels/1134557553011998840/1374474903981527082"
        )
        assert result == (1134557553011998840, 1374474903981527082)

    def test_message_url(self):
        """带消息 ID 的 Discord URL 忽略末尾消息 ID。"""
        result = self._parse(
            "https://discord.com/channels/1134557553011998840/"
            "1374474903981527082/1417064059782000640"
        )
        assert result == (1134557553011998840, 1374474903981527082)

    def test_message_url_with_trailing_slash(self):
        """带消息 ID 和尾部斜杠的 Discord URL 正常解析。"""
        result = self._parse(
            "https://discord.com/channels/1134557553011998840/"
            "1374474903981527082/1417064059782000640/"
        )
        assert result == (1134557553011998840, 1374474903981527082)

    def test_plain_numeric_id(self):
        """纯数字 ID → 使用 main_guild_id 拼接。"""
        result = self._parse("1234567890123456789")
        assert result == (1134557553011998840, 1234567890123456789)

    def test_invalid_url(self):
        """无效 URL 返回 None。"""
        assert self._parse("https://example.com/foo") is None

    def test_invalid_format(self):
        """非数字非 URL 返回 None。"""
        assert self._parse("abc123") is None

    def test_no_main_guild_id(self):
        """未配置 main_guild_id 时纯数字 ID 返回 None。"""
        assert self._parse("1234567890123456789", main_guild_id=0) is None


class TestApplicationFormModal:
    """Discord BOT Banner 申请弹窗测试。"""

    @staticmethod
    def _interaction(guild_id: int = 1134557553011998840) -> MagicMock:
        """构造弹窗提交所需的 Discord 交互对象。"""
        interaction = MagicMock()
        interaction.guild_id = guild_id
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()
        interaction.client.dispatch = MagicMock()
        return interaction

    @pytest.mark.asyncio
    async def test_submit_message_url(self):
        """消息 URL 解析后分发中间的帖子或频道 ID。"""
        modal = ApplicationFormModal()
        modal.target_link._value = (
            "https://discord.com/channels/1134557553011998840/"
            "1374474903981527082/1417064059782000640"
        )
        modal.cover_image_url._value = "https://example.com/banner.png"
        interaction = self._interaction()

        await modal.on_submit(interaction)

        interaction.client.dispatch.assert_called_once_with(
            "banner_form_submit",
            interaction,
            1374474903981527082,
            "https://example.com/banner.png",
            1134557553011998840,
        )

    @pytest.mark.asyncio
    async def test_submit_plain_id(self):
        """纯数字 ID 使用当前交互的服务器 ID。"""
        modal = ApplicationFormModal()
        modal.target_link._value = "1374474903981527082"
        modal.cover_image_url._value = "https://example.com/banner.png"
        interaction = self._interaction()

        await modal.on_submit(interaction)

        interaction.client.dispatch.assert_called_once_with(
            "banner_form_submit",
            interaction,
            1374474903981527082,
            "https://example.com/banner.png",
            1134557553011998840,
        )

    @pytest.mark.asyncio
    async def test_reject_invalid_target(self):
        """无效链接不分发申请事件。"""
        modal = ApplicationFormModal()
        modal.target_link._value = "https://example.com/not-discord"
        modal.cover_image_url._value = "https://example.com/banner.png"
        interaction = self._interaction()

        await modal.on_submit(interaction)

        interaction.followup.send.assert_awaited_once_with(
            "❌ 请输入有效的 Discord 帖子/赛事频道链接或纯数字 ID",
            ephemeral=True,
        )
        interaction.client.dispatch.assert_not_called()


class TestBannerApplicationRequest:
    """BannerApplicationRequest Pydantic 模型测试。"""

    def test_valid_request_with_url(self):
        """使用 Discord URL 提交。"""

        req = BannerApplicationRequest(
            thread_link="https://discord.com/channels/1/2",
            cover_image_url="https://example.com/img.png",
            target_scope="global",
        )
        assert req.thread_link == "https://discord.com/channels/1/2"

    def test_valid_request_with_plain_id(self):
        """使用纯数字 ID 提交。"""

        req = BannerApplicationRequest(
            thread_link="1234567890123456789",
            cover_image_url="https://example.com/img.png",
            target_scope="global",
        )
        assert req.thread_link == "1234567890123456789"

    def test_backward_compat_thread_id(self):
        """旧接口：传 thread_id 自动转为 thread_link。"""

        req = BannerApplicationRequest(
            thread_id="1234567890123456789",  # type: ignore[call-arg]
            cover_image_url="https://example.com/img.png",
            target_scope="global",
        )
        assert req.thread_link == "1234567890123456789"
        assert not hasattr(req, "thread_id")

    def test_both_thread_id_and_thread_link(self):
        """同时传 thread_id 和 thread_link → thread_link 优先。"""

        req = BannerApplicationRequest(
            thread_link="1234567890123456789",
            thread_id="1111111111111111111",  # type: ignore[call-arg]
            cover_image_url="https://example.com/img.png",
            target_scope="global",
        )
        assert req.thread_link == "1234567890123456789"

    def test_thread_link_too_short(self):
        """thread_link 长度不足 17 应报错。"""

        with pytest.raises(ValidationError):
            BannerApplicationRequest(
                thread_link="12345",
                cover_image_url="https://example.com/img.png",
                target_scope="global",
            )


class TestBannerServiceTargetDetection:
    """BannerService 自动检测 target_type 测试。"""

    @pytest.mark.asyncio
    async def test_detect_forum_thread(self, db_session_factory):
        """Thread 表中找到 → target_type=THREAD，检查作者。"""
        # 需要一条 Thread 记录
        from models.thread import Thread

        async with db_session_factory() as session:
            thread = Thread(
                thread_id=1234567890123456789,
                guild_id=1134557553011998840,
                channel_id=1111111111111111111,
                title="测试帖子",
                author_id=999,
            )
            session.add(thread)
            await session.commit()

            service = BannerService(session)
            result = await service.validate_application_request(
                target_id=1234567890123456789,
                guild_id=1134557553011998840,
                applicant_id=999,
                cover_image_url="https://example.com/img.png",
            )
            assert result.success is True
            assert result.target_type == TargetType.THREAD.value
            assert result.target_name == "测试帖子"

    @pytest.mark.asyncio
    async def test_forum_thread_wrong_author(self, db_session_factory):
        """Thread 表中找到但作者不匹配 → 拒绝。"""
        from models.thread import Thread

        async with db_session_factory() as session:
            thread = Thread(
                thread_id=1234567890123456789,
                guild_id=1,
                channel_id=1,
                title="别人的帖子",
                author_id=888,
            )
            session.add(thread)
            await session.commit()

            service = BannerService(session)
            result = await service.validate_application_request(
                target_id=1234567890123456789,
                guild_id=1,
                applicant_id=999,  # 不匹配
                cover_image_url="https://example.com/img.png",
            )
            assert result.success is False
            assert "只能为自己的帖子" in result.message

    @pytest.mark.asyncio
    async def test_thread_without_custom_cover_persists_null(self, db_session_factory):
        """帖子有当前首图时允许空封面，并保持数据库字段为空。"""
        from models.thread import Thread

        async with db_session_factory() as session:
            session.add(
                Thread(
                    thread_id=1234567890123456701,
                    guild_id=1,
                    channel_id=2,
                    title="动态封面帖子",
                    author_id=999,
                    thumbnail_urls=["https://example.com/current.png"],
                )
            )
            await session.commit()
            result = await BannerService(session).validate_and_create_application(
                target_id=1234567890123456701,
                guild_id=1,
                applicant_id=999,
                cover_image_url=None,
                target_scope="global",
            )
            assert result.success is True
            assert result.application is not None
            assert result.application.cover_image_url is None

    @pytest.mark.asyncio
    async def test_thread_without_any_cover_is_rejected(self, db_session_factory):
        """帖子既无自定义封面也无当前首图时拒绝申请。"""
        from models.thread import Thread

        async with db_session_factory() as session:
            session.add(
                Thread(
                    thread_id=1234567890123456702,
                    guild_id=1,
                    channel_id=2,
                    title="无图帖子",
                    author_id=999,
                    thumbnail_urls=[],
                )
            )
            await session.commit()
            result = await BannerService(session).validate_application_request(
                target_id=1234567890123456702,
                guild_id=1,
                applicant_id=999,
                cover_image_url=None,
            )
            assert result.success is False
            assert "没有可用首图" in result.message

    @pytest.mark.asyncio
    async def test_channel_without_custom_cover_is_rejected(self, db_session_factory):
        """频道 Banner 不允许省略自定义封面。"""
        async with db_session_factory() as session:
            session.add(
                ChannelModel(
                    channel_id=1234567890123456703,
                    guild_id=1,
                    name="频道",
                )
            )
            await session.commit()
            result = await BannerService(session).validate_application_request(
                target_id=1234567890123456703,
                guild_id=1,
                applicant_id=999,
                cover_image_url=None,
            )
            assert result.success is False
            assert "频道Banner必须" in result.message

    @pytest.mark.asyncio
    async def test_detect_channel(self, db_session_factory):
        """Thread 表未找到但 Channel 表中有 → target_type=CHANNEL。"""
        async with db_session_factory() as session:
            channel = ChannelModel(
                channel_id=1374474903981527082,
                guild_id=1134557553011998840,
                name="赛事频道",
            )
            session.add(channel)
            await session.commit()

            service = BannerService(session)
            result = await service.validate_application_request(
                target_id=1374474903981527082,
                guild_id=1134557553011998840,
                applicant_id=123,  # 频道不校验作者
                cover_image_url="https://example.com/img.png",
            )
            assert result.success is True
            assert result.target_type == TargetType.CHANNEL.value
            assert result.target_name == "赛事频道"

    @pytest.mark.asyncio
    async def test_not_found_no_sync(self, db_session_factory):
        """Thread 和 Channel 都查不到且无 channel_sync → 返回错误。"""
        async with db_session_factory() as session:
            service = BannerService(session)
            result = await service.validate_application_request(
                target_id=1234567890123456789,
                guild_id=1,
                applicant_id=1,
                cover_image_url="https://example.com/img.png",
            )
            assert result.success is False
            assert "未被索引" in result.message

    @pytest.mark.asyncio
    async def test_auto_sync_channel(self, db_session_factory):
        """channel_sync 可用时，按需索引频道。"""
        mock_sync = MagicMock()
        mock_channel = ChannelModel(
            channel_id=1374474903981527082,
            guild_id=1134557553011998840,
            name="Discord赛事频道",
        )
        mock_sync.fetch_and_index = AsyncMock(return_value=mock_channel)

        async with db_session_factory() as session:
            service = BannerService(session, channel_sync=mock_sync)
            result = await service.validate_application_request(
                target_id=1374474903981527082,
                guild_id=1134557553011998840,
                applicant_id=123,
                cover_image_url="https://example.com/img.png",
            )
            assert result.success is True
            assert result.target_type == TargetType.CHANNEL.value
            assert result.target_name == "Discord赛事频道"
            mock_sync.fetch_and_index.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_sync_failed(self, db_session_factory):
        """channel_sync 也失败 → 返回错误。"""
        mock_sync = MagicMock()
        mock_sync.fetch_and_index = AsyncMock(return_value=None)

        async with db_session_factory() as session:
            service = BannerService(session, channel_sync=mock_sync)
            result = await service.validate_application_request(
                target_id=1234567890123456789,
                guild_id=1,
                applicant_id=1,
                cover_image_url="https://example.com/img.png",
            )
            assert result.success is False


class TestBannerApplicationWithTargetType:
    """Banner 申请创建时 target_type 正确写入。"""

    @pytest.mark.asyncio
    async def test_create_application_with_target_type(self, db_session_factory):
        """申请记录包含 target_type。"""
        async with db_session_factory() as session:
            app = BannerApplication(
                thread_id=1234567890123456789,
                channel_id=1,
                applicant_id=1,
                cover_image_url="https://example.com/img.png",
                target_scope="global",
                target_type=TargetType.CHANNEL.value,
                status=ApplicationStatus.PENDING.value,
            )
            session.add(app)
            await session.commit()
            await session.refresh(app)

            assert app.target_type == TargetType.CHANNEL.value

    @pytest.mark.asyncio
    async def test_default_target_type_is_thread(self, db_session_factory):
        """不传 target_type 时默认为 THREAD (1)。"""
        async with db_session_factory() as session:
            app = BannerApplication(
                thread_id=1234567890123456789,
                channel_id=1,
                applicant_id=1,
                cover_image_url="https://example.com/img.png",
                target_scope="global",
                status=ApplicationStatus.PENDING.value,
            )
            session.add(app)
            await session.commit()
            await session.refresh(app)

            assert app.target_type == TargetType.THREAD.value


class TestBannerCarouselWithTargetType:
    """BannerCarousel target_type 测试。"""

    @pytest.mark.asyncio
    async def test_carousel_item_has_target_type(self, db_session_factory):
        """轮播项包含 target_type。"""
        async with db_session_factory() as session:
            item = BannerCarousel(
                thread_id=1374474903981527082,
                channel_id=None,
                cover_image_url="https://example.com/img.png",
                title="赛事频道",
                target_type=TargetType.CHANNEL.value,
                start_time=datetime.now(timezone.utc).replace(tzinfo=None),
                end_time=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            session.add(item)
            await session.commit()
            await session.refresh(item)

            assert item.target_type == TargetType.CHANNEL.value


class TestBannerWaitlistWithTargetType:
    """BannerWaitlist target_type 测试。"""

    @pytest.mark.asyncio
    async def test_waitlist_item_has_target_type(self, db_session_factory):
        """等待列表项包含 target_type。"""
        async with db_session_factory() as session:
            item = BannerWaitlist(
                thread_id=1374474903981527082,
                channel_id=None,
                cover_image_url="https://example.com/img.png",
                title="赛事频道",
                target_type=TargetType.CHANNEL.value,
            )
            session.add(item)
            await session.commit()
            await session.refresh(item)

            assert item.target_type == TargetType.CHANNEL.value


class TestActiveBannerChannelFilters:
    """活跃 Banner 接口的新旧频道参数兼容测试。"""

    def test_normalize_merges_and_stably_deduplicates_ids(self):
        """字符串、整数及旧参数按首次出现顺序合并。"""
        from api.v1.routers.banner import _normalize_banner_channel_ids

        result = _normalize_banner_channel_ids(["20", 10, "20"], "30")

        assert result == [20, 10, 30]

    def test_normalize_rejects_invalid_id(self):
        """非法频道 ID 返回 HTTP 400。"""
        from api.v1.routers.banner import _normalize_banner_channel_ids
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _normalize_banner_channel_ids(["invalid"], None)

        assert exc_info.value.status_code == 400
        assert "invalid" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_service_sorts_candidates_by_global_id(self, db_session_factory):
        """各范围保留数量上限，合并结果按全局轮播记录 ID 排序。"""
        now = datetime.now()
        channel_10_banners = [
            BannerCarousel(
                thread_id=1000 + position,
                channel_id=10,
                cover_image_url=f"https://example.com/10-{position}.png",
                title=f"频道10-{position}",
                start_time=now,
                end_time=now + timedelta(days=1),
                position=position,
            )
            for position in range(6)
        ]
        channel_20_banners = [
            BannerCarousel(
                thread_id=2000 + position,
                channel_id=20,
                cover_image_url=f"https://example.com/20-{position}.png",
                title=f"频道20-{position}",
                start_time=now,
                end_time=now + timedelta(days=1),
                position=position,
            )
            for position in range(2)
        ]
        global_banners = [
            BannerCarousel(
                thread_id=3000 + position,
                channel_id=None,
                cover_image_url=f"https://example.com/global-{position}.png",
                title=f"全局-{position}",
                start_time=now,
                end_time=now + timedelta(days=1),
                position=position,
            )
            for position in range(4)
        ]
        async with db_session_factory() as session:
            session.add_all(channel_10_banners + channel_20_banners + global_banners)
            await session.commit()

            service = BannerService(session)
            result = await service.get_active_banners(
                channel_id=10,
                channel_ids=[20, 10, 20],
            )
            legacy_result = await service.get_active_banners(channel_id=20)
            global_only_result = await service.get_active_banners()

        assert [banner.thread_id for banner in result] == [
            1000,
            1001,
            1002,
            1003,
            1004,
            2000,
            2001,
            3000,
            3001,
            3002,
        ]
        assert [banner.thread_id for banner in legacy_result] == [
            2000,
            2001,
            3000,
            3001,
            3002,
        ]
        assert [banner.thread_id for banner in global_only_result] == [
            3000,
            3001,
            3002,
        ]


class TestBannerCapacity:
    """单频道容量控制与候补补位测试。"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("current_count", "entered_carousel"),
        [(2, True), (3, False)],
    )
    async def test_approval_uses_channel_capacity(
        self, monkeypatch, current_count, entered_carousel
    ):
        """频道少于三个时直接展示，达到三个后进入等待队列。"""
        session = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        service = BannerService(session)
        application = SimpleNamespace(
            thread_id=100,
            target_scope="10",
            target_type=TargetType.THREAD.value,
            cover_image_url=None,
            status=ApplicationStatus.PENDING.value,
            reviewed_at=None,
            reviewer_id=None,
        )
        service.app_repo.get_by_id = AsyncMock(return_value=application)
        service.carousel_repo.get_count = AsyncMock(return_value=current_count)
        service.carousel_repo.add = AsyncMock()
        service.waitlist_repo.add = AsyncMock()
        thread_repo = MagicMock()
        thread_repo.get_thread_with_tags = AsyncMock(
            return_value=SimpleNamespace(title="测试帖子")
        )
        monkeypatch.setattr(
            "banner.banner_service.ThreadRepository", lambda _: thread_repo
        )

        _, actual_entered = await service.approve_application(1, 2)

        assert actual_entered is entered_carousel
        if entered_carousel:
            service.carousel_repo.add.assert_awaited_once()
            service.waitlist_repo.add.assert_not_awaited()
        else:
            service.carousel_repo.add.assert_not_awaited()
            service.waitlist_repo.add.assert_awaited_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("active_count", "promoted"),
        [(4, False), (2, True)],
    )
    async def test_cleanup_refills_only_below_capacity(
        self, active_count, promoted
    ):
        """活跃数量达到容量时不补位，少于容量时才补位。"""
        session = MagicMock()
        session.commit = AsyncMock()
        service = BannerService(session)
        expired = SimpleNamespace(channel_id=10)
        waiting = SimpleNamespace(
            thread_id=200,
            channel_id=10,
            cover_image_url=None,
            title="等待项",
            target_type=TargetType.THREAD.value,
        )
        service.carousel_repo.get_expired = AsyncMock(return_value=[expired])
        service.carousel_repo.delete = AsyncMock()
        service.carousel_repo.get_count = AsyncMock(return_value=active_count)
        service.carousel_repo.add = AsyncMock()
        service.waitlist_repo.pop = AsyncMock(return_value=waiting)

        assert await service.cleanup_expired_banners() == 1

        if promoted:
            service.waitlist_repo.pop.assert_awaited_once_with(10)
            service.carousel_repo.add.assert_awaited_once()
        else:
            service.waitlist_repo.pop.assert_not_awaited()
            service.carousel_repo.add.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("active_count", "promoted"),
        [(4, False), (2, True)],
    )
    async def test_manual_delete_refills_only_below_capacity(
        self, active_count, promoted
    ):
        """人工删除后按容量补位，并准确报告是否发生晋升。"""
        session = MagicMock()
        session.commit = AsyncMock()
        service = BannerService(session)
        banner = SimpleNamespace(thread_id=100, channel_id=10, title="展示项")
        waiting = SimpleNamespace(
            thread_id=200,
            channel_id=10,
            cover_image_url=None,
            title="等待项",
            target_type=TargetType.THREAD.value,
        )
        service.carousel_repo.get_by_thread = AsyncMock(return_value=[banner])
        service.waitlist_repo.get_by_thread = AsyncMock(return_value=[])
        service.carousel_repo.delete = AsyncMock()
        service.carousel_repo.get_count = AsyncMock(return_value=active_count)
        service.carousel_repo.add = AsyncMock()
        service.waitlist_repo.pop = AsyncMock(return_value=waiting)

        result = await service.delete_banner_by_thread(100)

        assert result.success is True
        assert result.promoted_from_waitlist is promoted
        if promoted:
            service.waitlist_repo.pop.assert_awaited_once_with(10)
            service.carousel_repo.add.assert_awaited_once()
        else:
            service.waitlist_repo.pop.assert_not_awaited()
            service.carousel_repo.add.assert_not_awaited()


class TestBannerPreferenceFiltering:
    """Banner 帖子复用搜索反选规则。"""

    @pytest.mark.asyncio
    async def test_batch_filter_uses_all_search_exclusions(self, db_session_factory):
        """作者、真实标签、关键词、豁免和可见性在一次查询中生效。"""
        from core.tag_cache_service import TagCacheService
        from dto.preferences import UserSearchPreferencesDTO
        from models import Tag, Thread, TagBinding
        from search.search_service import SearchService

        blocked_tag = Tag(id=9001, name="屏蔽标签")
        threads = [
            Thread(
                thread_id=100,
                guild_id=1,
                channel_id=10,
                title="普通帖子",
                author_id=1,
            ),
            Thread(
                thread_id=101,
                guild_id=1,
                channel_id=10,
                title="排除作者帖子",
                author_id=2,
            ),
            Thread(
                thread_id=102,
                guild_id=1,
                channel_id=10,
                title="排除标签帖子",
                author_id=1,
            ),
            Thread(
                thread_id=103,
                guild_id=1,
                channel_id=10,
                title="关于百合破坏的讨论",
                author_id=1,
            ),
            Thread(
                thread_id=104,
                guild_id=1,
                channel_id=10,
                title="🈲百合破坏",
                author_id=1,
            ),
            Thread(
                thread_id=105,
                guild_id=1,
                channel_id=10,
                title="隐藏帖子",
                author_id=1,
                show_flag=False,
            ),
            Thread(
                thread_id=106,
                guild_id=1,
                channel_id=10,
                title="失效帖子",
                author_id=1,
                not_found_count=1,
            ),
        ]
        thread_ids = [thread.thread_id for thread in threads]

        async with db_session_factory() as session:
            session.add(blocked_tag)
            session.add_all(threads)
            await session.flush()
            tagged_thread = next(
                thread for thread in threads if thread.thread_id == 102
            )
            session.add(
                TagBinding(
                    target_type="thread",
                    binding_source="local",
                    target_id=tagged_thread.id,
                    tag_id=blocked_tag.id,
                )
            )
            await session.commit()

            tag_cache = TagCacheService(db_session_factory)
            await tag_cache.build_cache()
            service = SearchService(session, tag_cache)
            prefs = UserSearchPreferencesDTO(
                user_id=42,
                exclude_authors=[2],
                exclude_tags=["屏蔽标签"],
                exclude_keywords="百合破坏",
                exclude_keyword_exemption_markers=["禁", "🈲"],
            )

            result = await service.get_preference_filtered_thread_guilds(
                thread_ids + [999],
                prefs=prefs,
                channel_mappings_config={},
            )

        assert set(result) == {100, 104}

    @pytest.mark.asyncio
    async def test_virtual_exclude_tag_filters_source_channel(self, db_session_factory):
        """虚拟反选标签转换为源频道过滤，真实标签列表不被误用。"""
        from core.tag_cache_service import TagCacheService
        from dto.preferences import UserSearchPreferencesDTO
        from models import Thread
        from search.search_service import SearchService

        threads = [
            Thread(
                thread_id=200,
                guild_id=1,
                channel_id=20,
                title="虚拟标签源频道帖子",
                author_id=1,
            ),
            Thread(
                thread_id=300,
                guild_id=1,
                channel_id=30,
                title="其他频道帖子",
                author_id=1,
            ),
        ]
        mappings = {
            999: [
                {
                    "tag_name": "虚拟屏蔽",
                    "source_channel_ids": [20],
                }
            ]
        }

        async with db_session_factory() as session:
            session.add_all(threads)
            await session.commit()

            tag_cache = TagCacheService(db_session_factory)
            await tag_cache.build_cache()
            service = SearchService(session, tag_cache)
            prefs = UserSearchPreferencesDTO(
                user_id=42,
                exclude_tags=["虚拟屏蔽"],
            )

            result = await service.get_preference_filtered_thread_guilds(
                [200, 300],
                prefs=prefs,
                channel_mappings_config=mappings,
            )

        assert set(result) == {300}

    @pytest.mark.asyncio
    async def test_active_endpoint_preserves_order_and_channel_banner(
        self, db_session_factory, monkeypatch
    ):
        """频道 Banner 保留，帖子过滤后维持数据库返回的轮播顺序。"""
        from api.v1.routers import banner as banner_router
        from core.tag_cache_service import TagCacheService
        from dto.preferences import UserSearchPreferencesDTO
        from models import Thread

        now = datetime.now()
        channel = ChannelModel(channel_id=900, guild_id=1, name="频道 Banner")
        allowed_thread = Thread(
            thread_id=100,
            guild_id=1,
            channel_id=10,
            title="保留帖子",
            author_id=1,
        )
        blocked_thread = Thread(
            thread_id=101,
            guild_id=1,
            channel_id=10,
            title="屏蔽作者帖子",
            author_id=2,
        )
        banners = [
            BannerCarousel(
                thread_id=900,
                channel_id=10,
                cover_image_url="https://example.com/channel.png",
                title="频道 Banner",
                target_type=TargetType.CHANNEL.value,
                start_time=now,
                end_time=now + timedelta(days=1),
                position=0,
            ),
            BannerCarousel(
                thread_id=100,
                channel_id=10,
                cover_image_url="https://example.com/allowed.png",
                title="保留帖子",
                target_type=TargetType.THREAD.value,
                start_time=now,
                end_time=now + timedelta(days=1),
                position=1,
            ),
            BannerCarousel(
                thread_id=101,
                channel_id=10,
                cover_image_url="https://example.com/blocked.png",
                title="屏蔽作者帖子",
                target_type=TargetType.THREAD.value,
                start_time=now,
                end_time=now + timedelta(days=1),
                position=2,
            ),
        ]

        async with db_session_factory() as session:
            session.add(channel)
            session.add_all([allowed_thread, blocked_thread])
            session.add_all(banners)
            await session.commit()

        tag_cache = TagCacheService(db_session_factory)
        await tag_cache.build_cache()
        monkeypatch.setattr(banner_router, "async_session_factory", db_session_factory)
        monkeypatch.setattr(banner_router, "tag_cache_service_instance", tag_cache)
        monkeypatch.setattr(banner_router, "channel_mappings_config", {})
        monkeypatch.setattr(banner_router, "main_guild_id", 1)
        monkeypatch.setattr(
            banner_router,
            "get_user_preferences_cached",
            AsyncMock(
                return_value=UserSearchPreferencesDTO(
                    user_id=42,
                    exclude_authors=[2],
                )
            ),
        )

        result = await banner_router.get_active_banners(
            channel_ids=["10"],
            channel_id="10",
            current_user={"id": "42"},
        )

        assert [item.thread_id for item in result] == [900, 100]
        assert result[0].target_type == TargetType.CHANNEL.value

    @pytest.mark.asyncio
    async def test_preference_failure_degrades_to_visible_threads(
        self, db_session_factory, monkeypatch
    ):
        """偏好读取失败时不应用反选，但仍移除不可搜索帖子。"""
        from api.v1.routers import banner as banner_router
        from core.tag_cache_service import TagCacheService
        from models import Thread

        now = datetime.now()
        visible_thread = Thread(
            thread_id=400,
            guild_id=1,
            channel_id=10,
            title="可见帖子",
            author_id=1,
        )
        hidden_thread = Thread(
            thread_id=401,
            guild_id=1,
            channel_id=10,
            title="隐藏帖子",
            author_id=1,
            show_flag=False,
        )
        banners = [
            BannerCarousel(
                thread_id=400,
                channel_id=None,
                cover_image_url="https://example.com/visible.png",
                title="可见帖子",
                target_type=TargetType.THREAD.value,
                start_time=now,
                end_time=now + timedelta(days=1),
                position=0,
            ),
            BannerCarousel(
                thread_id=401,
                channel_id=None,
                cover_image_url="https://example.com/hidden.png",
                title="隐藏帖子",
                target_type=TargetType.THREAD.value,
                start_time=now,
                end_time=now + timedelta(days=1),
                position=1,
            ),
        ]

        async with db_session_factory() as session:
            session.add_all([visible_thread, hidden_thread])
            session.add_all(banners)
            await session.commit()

        tag_cache = TagCacheService(db_session_factory)
        await tag_cache.build_cache()
        monkeypatch.setattr(banner_router, "async_session_factory", db_session_factory)
        monkeypatch.setattr(banner_router, "tag_cache_service_instance", tag_cache)
        monkeypatch.setattr(banner_router, "channel_mappings_config", {})
        monkeypatch.setattr(
            banner_router,
            "get_user_preferences_cached",
            AsyncMock(side_effect=RuntimeError("cache unavailable")),
        )

        result = await banner_router.get_active_banners(
            channel_ids=None,
            channel_id=None,
            current_user={"id": "42"},
        )

        assert [item.thread_id for item in result] == [400]

    def test_search_router_has_no_banner_return_helper(self):
        """搜索路由不再保留旧 Banner 返回路径。"""
        from api.v1.routers import search as search_router

        assert not hasattr(search_router, "_get_banner_and_unread_async")


class TestApplicationResult:
    """ApplicationResult dataclass 测试。"""

    def test_defaults(self):
        result = ApplicationResult(success=True, message="ok")
        assert result.target_type == 1
        assert result.guild_id == 0
        assert result.target_name == ""

    def test_channel_result(self):
        result = ApplicationResult(
            success=True,
            message="验证通过",
            target_type=TargetType.CHANNEL.value,
            guild_id=1134557553011998840,
            target_name="赛事频道A",
        )
        assert result.target_type == 2
        assert result.guild_id == 1134557553011998840
        assert result.target_name == "赛事频道A"
