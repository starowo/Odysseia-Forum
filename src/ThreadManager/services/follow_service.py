import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, func
from sqlmodel import col

from shared.models.thread_follow import ThreadFollow
from shared.models.thread import Thread

logger = logging.getLogger(__name__)


class FollowService:
    """关注列表服务"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def add_follow(
        self,
        user_id: int,
        thread_id: int,
        auto_view: bool = False
    ) -> bool:
        """
        添加关注
        
        Args:
            user_id: 用户Discord ID
            thread_id: 帖子Discord ID
            auto_view: 是否自动标记为已查看（用于用户主动加入的情况）
        
        Returns:
            是否成功添加（如果已存在则返回False）
        """
        try:
            # 检查是否已关注
            statement = select(ThreadFollow).where(
                and_(
                    ThreadFollow.user_id == user_id,
                    ThreadFollow.thread_id == thread_id
                )
            )
            result = await self.session.execute(statement)
            existing = result.scalar_one_or_none()
            
            if existing:
                logger.debug(f"用户 {user_id} 已关注帖子 {thread_id}")
                return False
            
            # 创建关注记录
            now = datetime.now(timezone.utc)
            follow = ThreadFollow(
                user_id=user_id,
                thread_id=thread_id,
                followed_at=now,
                last_viewed_at=now if auto_view else None
            )
            
            self.session.add(follow)
            await self.session.commit()
            
            logger.info(f"用户 {user_id} 已关注帖子 {thread_id}")
            return True
            
        except Exception as e:
            logger.error(f"添加关注失败: {e}", exc_info=True)
            await self.session.rollback()
            return False
    
    async def batch_add_follows(
        self,
        thread_id: int,
        user_ids: List[int]
    ) -> int:
        """
        批量添加关注（用于首次检测到帖子时）
        
        Args:
            thread_id: 帖子Discord ID
            user_ids: 用户Discord ID列表
        
        Returns:
            成功添加的数量
        """
        if not user_ids:
            return 0
        
        try:
            # 查询已存在的关注记录
            statement = select(ThreadFollow.user_id).where(
                and_(
                    ThreadFollow.thread_id == thread_id,
                    col(ThreadFollow.user_id).in_(user_ids)
                )
            )
            result = await self.session.execute(statement)
            existing_user_ids = set(result.scalars().all())
            
            # 过滤出需要添加的用户
            new_user_ids = [uid for uid in user_ids if uid not in existing_user_ids]
            
            if not new_user_ids:
                logger.debug(f"帖子 {thread_id} 的所有用户都已关注")
                return 0
            
            # 批量创建关注记录
            now = datetime.now(timezone.utc)
            follows = [
                ThreadFollow(
                    user_id=user_id,
                    thread_id=thread_id,
                    followed_at=now,
                    last_viewed_at=None  # 首次添加时不标记为已查看
                )
                for user_id in new_user_ids
            ]
            
            self.session.add_all(follows)
            await self.session.commit()
            
            logger.info(f"为帖子 {thread_id} 批量添加了 {len(new_user_ids)} 个关注")
            return len(new_user_ids)
            
        except Exception as e:
            logger.error(f"批量添加关注失败: {e}", exc_info=True)
            await self.session.rollback()
            return 0
    
    async def remove_follow(
        self,
        user_id: int,
        thread_id: int
    ) -> bool:
        """
        取消关注
        
        Args:
            user_id: 用户Discord ID
            thread_id: 帖子Discord ID
        
        Returns:
            是否成功取消
        """
        try:
            statement = delete(ThreadFollow).where(
                and_(
                    ThreadFollow.user_id == user_id,
                    ThreadFollow.thread_id == thread_id
                )
            )
            result = await self.session.execute(statement)
            await self.session.commit()
            
            if result.rowcount > 0:
                logger.info(f"用户 {user_id} 已取消关注帖子 {thread_id}")
                return True
            else:
                logger.debug(f"用户 {user_id} 未关注帖子 {thread_id}")
                return False
                
        except Exception as e:
            logger.error(f"取消关注失败: {e}", exc_info=True)
            await self.session.rollback()
            return False
    
    async def update_last_viewed(
        self,
        user_id: int,
        thread_id: Optional[int] = None
    ) -> bool:
        """
        更新最后查看时间
        
        Args:
            user_id: 用户Discord ID
            thread_id: 帖子Discord ID，如果为None则更新所有关注
        
        Returns:
            是否成功更新
        """
        try:
            now = datetime.now(timezone.utc)
            
            if thread_id is not None:
                # 更新单个帖子
                statement = select(ThreadFollow).where(
                    and_(
                        ThreadFollow.user_id == user_id,
                        ThreadFollow.thread_id == thread_id
                    )
                )
                result = await self.session.execute(statement)
                follow = result.scalar_one_or_none()
                
                if follow:
                    follow.last_viewed_at = now
                    self.session.add(follow)
                    await self.session.commit()
                    logger.debug(f"已更新用户 {user_id} 对帖子 {thread_id} 的查看时间")
                    return True
                else:
                    logger.warning(f"用户 {user_id} 未关注帖子 {thread_id}")
                    return False
            else:
                # 更新所有关注
                statement = select(ThreadFollow).where(
                    ThreadFollow.user_id == user_id
                )
                result = await self.session.execute(statement)
                follows = result.scalars().all()
                
                for follow in follows:
                    follow.last_viewed_at = now
                    self.session.add(follow)
                
                await self.session.commit()
                logger.debug(f"已更新用户 {user_id} 的所有关注查看时间")
                return True
                
        except Exception as e:
            logger.error(f"更新查看时间失败: {e}", exc_info=True)
            await self.session.rollback()
            return False
    
    async def get_user_follows(
        self,
        user_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        获取用户关注的帖子列表
        
        Args:
            user_id: 用户Discord ID
            limit: 返回数量限制
            offset: 偏移量
        
        Returns:
            (帖子列表, 总数)
        """
        try:
            # 构建查询，使用selectinload加载tags，joinedload加载author
            from sqlalchemy.orm import selectinload, joinedload
            
            statement = (
                select(Thread, ThreadFollow)
                .join(ThreadFollow, Thread.thread_id == ThreadFollow.thread_id)
                .where(ThreadFollow.user_id == user_id)
                .options(
                    selectinload(Thread.tags),  # 预加载tags
                    joinedload(Thread.author),  # 预加载author
                )
                .order_by(ThreadFollow.followed_at.desc())
                .limit(limit)
                .offset(offset)
            )
            
            result = await self.session.execute(statement)
            rows = result.all()
            
            # 统计总数
            count_statement = (
                select(func.count())
                .select_from(ThreadFollow)
                .where(ThreadFollow.user_id == user_id)
            )
            count_result = await self.session.execute(count_statement)
            total = count_result.scalar() or 0
            
            # 转换为字典格式（ID转为字符串以避免JavaScript精度丢失）
            threads = []
            for thread, follow in rows:
                # 构建author对象
                author_data = None
                if thread.author:
                    author_data = {
                        "id": str(thread.author.id),
                        "name": thread.author.name,
                        "global_name": thread.author.global_name,
                        "display_name": thread.author.display_name,
                        "avatar_url": thread.author.avatar_url,
                    }
                
                thread_dict = {
                    "thread_id": str(thread.thread_id),
                    "channel_id": str(thread.channel_id),
                    "title": thread.title,
                    "author": author_data,
                    "created_at": thread.created_at,
                    "last_active_at": thread.last_active_at,
                    "latest_update_at": thread.latest_update_at,
                    "latest_update_link": thread.latest_update_link,
                    "reaction_count": thread.reaction_count,
                    "reply_count": thread.reply_count,
                    "first_message_excerpt": thread.first_message_excerpt,
                    "thumbnail_urls": thread.thumbnail_urls or [],
                    "tags": [tag.name for tag in thread.tags],
                    "followed_at": follow.followed_at,
                    "last_viewed_at": follow.last_viewed_at,
                    "has_update": (
                        thread.latest_update_at is not None and
                        (follow.last_viewed_at is None or
                         thread.latest_update_at > follow.last_viewed_at)
                    )
                }
                threads.append(thread_dict)
            
            return threads, total
            
        except Exception as e:
            logger.error(f"获取关注列表失败: {e}", exc_info=True)
            return [], 0
    
    async def get_unread_count(self, user_id: int) -> int:
        """
        获取用户未读更新的数量
        
        Args:
            user_id: 用户Discord ID
        
        Returns:
            未读更新数量
        """
        try:
            # 查询有更新且未查看的帖子数量
            statement = (
                select(func.count())
                .select_from(ThreadFollow)
                .join(Thread, ThreadFollow.thread_id == Thread.thread_id)
                .where(
                    and_(
                        ThreadFollow.user_id == user_id,
                        Thread.latest_update_at.isnot(None),
                        # 未查看 或 更新时间晚于查看时间
                        (
                            (ThreadFollow.last_viewed_at.is_(None)) |
                            (Thread.latest_update_at > ThreadFollow.last_viewed_at)
                        )
                    )
                )
            )
            
            result = await self.session.execute(statement)
            count = result.scalar() or 0
            
            return count
            
        except Exception as e:
            logger.error(f"获取未读数量失败: {e}", exc_info=True)
            return 0
    
    async def is_following(
        self,
        user_id: int,
        thread_id: int
    ) -> bool:
        """
        检查用户是否关注了某个帖子
        
        Args:
            user_id: 用户Discord ID
            thread_id: 帖子Discord ID
        
        Returns:
            是否关注
        """
        try:
            statement = select(ThreadFollow).where(
                and_(
                    ThreadFollow.user_id == user_id,
                    ThreadFollow.thread_id == thread_id
                )
            )
            result = await self.session.execute(statement)
            follow = result.scalar_one_or_none()
            
            return follow is not None
            
        except Exception as e:
            logger.error(f"检查关注状态失败: {e}", exc_info=True)
            return False