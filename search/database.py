import aiosqlite
from ranking_config import RankingConfig

DB_PATH = "forum_search.db"

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS threads(
    thread_id INTEGER PRIMARY KEY,
    channel_id INTEGER,
    title TEXT,
    author_id INTEGER,
    created_at TEXT,
    last_active_at TEXT,
    reaction_count INTEGER DEFAULT 0,
    reply_count INTEGER DEFAULT 0,
    tags TEXT,
    first_message_excerpt TEXT,
    thumbnail_url TEXT
);

CREATE TABLE IF NOT EXISTS tags(
    tag_id INTEGER PRIMARY KEY,
    name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS thread_tags(
    thread_id INTEGER,
    tag_id INTEGER,
    PRIMARY KEY(thread_id, tag_id)
);

CREATE TABLE IF NOT EXISTS tag_votes(
    user_id INTEGER,
    tag_id INTEGER,
    vote INTEGER,
    PRIMARY KEY(user_id, tag_id)
);

CREATE TABLE IF NOT EXISTS user_preferences(
    user_id INTEGER PRIMARY KEY,
    results_per_page INTEGER DEFAULT 6
);

CREATE TABLE IF NOT EXISTS user_search_preferences(
    user_id INTEGER PRIMARY KEY,
    include_authors TEXT,
    exclude_authors TEXT,
    after_date TEXT,
    before_date TEXT,
    tag_logic TEXT DEFAULT 'and',
    preview_image_mode TEXT DEFAULT 'thumbnail'
);
"""

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(CREATE_TABLES_SQL)
        
        # 数据库迁移：检查并添加缺失的字段
        await migrate_database(db)
        
        await db.commit()

async def migrate_database(db):
    """数据库迁移函数：添加缺失的字段"""
    # 检查 user_search_preferences 表是否有 tag_logic 字段
    async with db.execute("PRAGMA table_info(user_search_preferences)") as cursor:
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'tag_logic' not in column_names:
            print("正在添加 tag_logic 字段...")
            await db.execute("ALTER TABLE user_search_preferences ADD COLUMN tag_logic TEXT DEFAULT 'and'")
            print("已添加 tag_logic 字段")
            
        if 'preview_image_mode' not in column_names:
            print("正在添加 preview_image_mode 字段...")
            await db.execute("ALTER TABLE user_search_preferences ADD COLUMN preview_image_mode TEXT DEFAULT 'thumbnail'")
            print("已添加 preview_image_mode 字段")

async def add_or_update_thread(info: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO threads(thread_id, channel_id, title, author_id,
                            created_at, last_active_at, reaction_count,
                            reply_count, tags, first_message_excerpt,
                            thumbnail_url)
        VALUES(:thread_id, :channel_id, :title, :author_id,
               :created_at, :last_active_at, :reaction_count,
               :reply_count, :tags, :first_message_excerpt,
               :thumbnail_url)
        ON CONFLICT(thread_id) DO UPDATE SET
            last_active_at=excluded.last_active_at,
            reaction_count=excluded.reaction_count,
            reply_count=excluded.reply_count,
            tags=excluded.tags,
            first_message_excerpt=excluded.first_message_excerpt,
            thumbnail_url=excluded.thumbnail_url;
        """, info)
        await db.commit()

async def ensure_tag(tag_id: int, name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO tags(tag_id, name) VALUES(?, ?)", (tag_id, name))
        await db.commit()
        return tag_id

async def link_thread_tag(thread_id: int, tag_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO thread_tags(thread_id, tag_id) VALUES(?, ?)", (thread_id, tag_id))
        await db.commit()

async def record_tag_vote(user_id: int, tag_id: int, vote: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO tag_votes(user_id, tag_id, vote)
        VALUES(?, ?, ?)
        ON CONFLICT(user_id, tag_id) DO UPDATE SET vote=excluded.vote;
        """, (user_id, tag_id, vote))
        await db.commit()

async def get_results_per_page(user_id: int) -> int:
    """返回用户设置的每页结果数量，默认 6"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT results_per_page FROM user_preferences WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 6

async def set_results_per_page(user_id: int, num: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO user_preferences(user_id, results_per_page) VALUES(?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET results_per_page = excluded.results_per_page",
            (user_id, num),
        )
        await db.commit()

async def get_tags_for_channel(channel_id: int):
    """获取频道内出现过的所有标签 (返回 List[(tag_id, name)])"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT DISTINCT tags.tag_id, tags.name FROM tags "
            "JOIN thread_tags ON thread_tags.tag_id = tags.tag_id "
            "JOIN threads ON threads.thread_id = thread_tags.thread_id "
            "WHERE threads.channel_id = ?",
            (channel_id,),
        ) as cursor:
            return await cursor.fetchall()

async def search_threads(
    include_tags: list[str],
    exclude_tags: list[str],
    keywords: str,
    channel_ids: list[int] | None,
    include_authors: list[int] | None,
    exclude_authors: list[int] | None,
    after_ts: str | None,
    before_ts: str | None,
    offset: int,
    limit: int,
    sort_method: str = "comprehensive",  # 新增参数：comprehensive, created_time, active_time, reaction_count
    sort_order: str = "desc",  # 新增参数：desc, asc
    tag_logic: str = "and",  # 新增参数：and, or
    exclude_keywords: str = ""  # 新增：排除关键词
):
    """搜索帖子并按指定方式排序。

    排序方式：
    • comprehensive: 智能混合权重排序（时间+标签+反应）
    • created_time: 按发帖时间排序
    • active_time: 按最近活跃时间排序  
    • reaction_count: 按反应数排序
    
    排序方向：
    • desc: 降序（默认）
    • asc: 升序
    """
    conditions: list[str] = []
    params: list = []

    if channel_ids:
        placeholders = ",".join(["?"] * len(channel_ids))
        conditions.append(f"threads.channel_id IN ({placeholders})")
        params.extend(channel_ids)

    if include_authors:
        placeholders = ",".join(["?"] * len(include_authors))
        conditions.append(f"author_id IN ({placeholders})")
        params.extend(include_authors)
    if exclude_authors:
        placeholders = ",".join(["?"] * len(exclude_authors))
        conditions.append(f"author_id NOT IN ({placeholders})")
        params.extend(exclude_authors)

    if after_ts:
        conditions.append("last_active_at >= ?")
        params.append(after_ts)
    if before_ts:
        conditions.append("last_active_at <= ?")
        params.append(before_ts)

    # 关键词过滤将在Python中处理，不在SQL中处理

    # 标签过滤将在Python中处理，所以这里不需要复杂的JOIN
    # 但综合排序仍需要标签评分，所以保留JOIN（仅当需要时）
    if sort_method == "comprehensive" and include_tags:
        join_clause = " LEFT JOIN thread_tags tt ON tt.thread_id = threads.thread_id "\
                      "LEFT JOIN tags tg ON tg.tag_id = tt.tag_id "\
                      "LEFT JOIN tag_votes tv ON tv.tag_id = tg.tag_id "
    else:
        join_clause = ""

    where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""

    # 根据排序方式决定查询和处理逻辑
    if sort_method == "comprehensive":
        # 智能综合排序 - 需要计算权重
        if include_tags:
            inc_placeholders = ",".join(["?"] * len(include_tags))
            
            # 计算标签的总点赞数、总点踩数、总评价数
            tag_score_expr = f"""
            -- 计算选中标签的综合评分
            SUM(CASE WHEN tg.name IN ({inc_placeholders}) AND tv.vote = 1 THEN 1 ELSE 0 END) AS total_upvotes,
            SUM(CASE WHEN tg.name IN ({inc_placeholders}) AND tv.vote = -1 THEN 1 ELSE 0 END) AS total_downvotes,
            SUM(CASE WHEN tg.name IN ({inc_placeholders}) AND tv.vote IS NOT NULL THEN 1 ELSE 0 END) AS total_votes
            """
            tag_params = include_tags * 3  # 占用三次
        else:
            tag_score_expr = "0 AS total_upvotes, 0 AS total_downvotes, 0 AS total_votes"
            tag_params = []

        select_clause = f"""
        SELECT threads.*, 
               {tag_score_expr},
               -- 时间权重：指数衰减
               EXP(-? * (JULIANDAY('now') - JULIANDAY(last_active_at))) AS time_weight,
               -- 当前时间戳，用于调试
               JULIANDAY('now') - JULIANDAY(last_active_at) AS days_since_active
        FROM threads{join_clause}{where_clause} 
        GROUP BY threads.thread_id
        """

        all_params = tag_params + [RankingConfig.TIME_DECAY_RATE] + params

        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(select_clause, all_params) as cursor:
                rows = await cursor.fetchall()
                
                # 在Python中计算最终评分并排序
                scored_rows = []
                for row in rows:
                    row_dict = dict(row)
                    
                    # 计算标签权重 (Wilson Score Lower Bound)
                    upvotes = row_dict['total_upvotes']
                    downvotes = row_dict['total_downvotes']
                    total_votes = row_dict['total_votes']
                    
                    if total_votes > 0:
                        # Wilson Score Lower Bound算法
                        # 更保守的评估，考虑样本量的置信度
                        positive_rate = upvotes / total_votes
                        z = RankingConfig.WILSON_CONFIDENCE_LEVEL  # 置信区间
                        n = total_votes
                        
                        # Wilson Score公式
                        wilson_center = (positive_rate + z*z/(2*n)) / (1 + z*z/n)
                        wilson_radius = z * ((positive_rate*(1-positive_rate) + z*z/(4*n)) / n)**0.5 / (1 + z*z/n)
                        tag_weight = max(0, wilson_center - wilson_radius)  # 下界，更保守
                    else:
                        # 无评价时给予默认评分
                        tag_weight = RankingConfig.DEFAULT_TAG_SCORE
                    
                    # 时间权重 (已在SQL中计算)
                    time_weight = row_dict['time_weight']
                    
                    # 反应权重 (基于对数归一化)
                    reaction_count = row_dict['reaction_count']
                    import math
                    if reaction_count > 0:
                        # 使用对数函数归一化：log(reactions + 1) / log(base + 1)
                        reaction_weight = min(
                            RankingConfig.MAX_REACTION_SCORE,
                            math.log(reaction_count + 1) / math.log(RankingConfig.REACTION_LOG_BASE + 1)
                        )
                    else:
                        reaction_weight = 0.0
                    
                    # 综合评分：使用配置的权重因子
                    time_factor = RankingConfig.TIME_WEIGHT_FACTOR
                    tag_factor = RankingConfig.TAG_WEIGHT_FACTOR
                    reaction_factor = RankingConfig.REACTION_WEIGHT_FACTOR
                    base_score = time_factor * time_weight + tag_factor * tag_weight + reaction_factor * reaction_weight
                    
                    # 恶评惩罚：如果标签评分过低，额外降权
                    if tag_weight < RankingConfig.SEVERE_PENALTY_THRESHOLD and total_votes >= RankingConfig.SEVERE_PENALTY_MIN_VOTES:
                        penalty_factor = RankingConfig.SEVERE_PENALTY_FACTOR
                        final_score = base_score * penalty_factor
                    elif tag_weight < RankingConfig.MILD_PENALTY_THRESHOLD and total_votes >= RankingConfig.MILD_PENALTY_MIN_VOTES:
                        penalty_factor = RankingConfig.MILD_PENALTY_FACTOR
                        final_score = base_score * penalty_factor
                    else:
                        final_score = base_score
                    
                    # 添加评分信息到结果中
                    row_dict['final_score'] = final_score
                    row_dict['tag_weight'] = tag_weight
                    row_dict['time_weight'] = time_weight
                    row_dict['reaction_weight'] = reaction_weight
                    
                    scored_rows.append(row_dict)
                
                # 按最终评分降序排序
                scored_rows.sort(key=lambda x: x['final_score'], reverse=(sort_order == "desc"))
                
                # 在Python中应用标签和关键词过滤
                filtered_rows = _filter_threads(scored_rows, include_tags, exclude_tags, keywords, exclude_keywords, tag_logic)
                
                # 应用分页
                start_idx = offset
                end_idx = offset + limit
                
                return filtered_rows[start_idx:end_idx]
    
    else:
        # 简单排序方式 - 直接在SQL中排序，不需要JOIN
        select_clause = f"SELECT threads.* FROM threads{where_clause}"
        
        # 根据排序方式添加ORDER BY子句
        sort_direction = "DESC" if sort_order == "desc" else "ASC"
        if sort_method == "created_time":
            order_clause = f" ORDER BY datetime(created_at) {sort_direction}"
        elif sort_method == "active_time":
            order_clause = f" ORDER BY datetime(last_active_at) {sort_direction}"
        elif sort_method == "reaction_count":
            order_clause = f" ORDER BY reaction_count {sort_direction}, datetime(last_active_at) DESC"
        else:
            # 默认按活跃时间排序
            order_clause = f" ORDER BY datetime(last_active_at) {sort_direction}"
        
        # 先获取所有符合条件的数据，然后在Python中过滤标签和分页
        final_query = select_clause + order_clause
        
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(final_query, params) as cursor:
                rows = await cursor.fetchall()
                dict_rows = [dict(row) for row in rows]
                
                # 在Python中应用标签和关键词过滤
                filtered_rows = _filter_threads(dict_rows, include_tags, exclude_tags, keywords, exclude_keywords, tag_logic)
                
                # 应用分页
                start_idx = offset
                end_idx = offset + limit
                
                return filtered_rows[start_idx:end_idx]

async def count_threads_for_search(
    include_tags: list[str],
    exclude_tags: list[str],
    keywords: str,
    channel_ids: list[int] | None,
    include_authors: list[int] | None,
    exclude_authors: list[int] | None,
    after_ts: str | None,
    before_ts: str | None,
    tag_logic: str = "and",
    exclude_keywords: str = ""  # 新增：排除关键词
):
    """统计搜索结果总数"""
    conditions = []
    params = []

    if channel_ids:
        placeholders = ",".join(["?"] * len(channel_ids))
        conditions.append(f"threads.channel_id IN ({placeholders})")
        params.extend(channel_ids)

    if include_authors:
        placeholders = ",".join(["?"] * len(include_authors))
        conditions.append(f"author_id IN ({placeholders})")
        params.extend(include_authors)
    if exclude_authors:
        placeholders = ",".join(["?"] * len(exclude_authors))
        conditions.append(f"author_id NOT IN ({placeholders})")
        params.extend(exclude_authors)

    if after_ts:
        conditions.append("last_active_at >= ?")
        params.append(after_ts)
    if before_ts:
        conditions.append("last_active_at <= ?")
        params.append(before_ts)

    # 关键词过滤将在Python中处理，不在SQL中处理

    # 标签和关键词过滤将在Python中处理，不在SQL中处理
    where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""

    # 如果有标签或关键词过滤条件，需要获取所有符合其他条件的帖子，然后在Python中过滤
    if include_tags or exclude_tags or keywords:
        query = f"SELECT thread_id, tags, title, first_message_excerpt FROM threads{where_clause}"
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                dict_rows = [dict(row) for row in rows]
                
                # 在Python中应用标签和关键词过滤
                filtered_rows = _filter_threads(dict_rows, include_tags, exclude_tags, keywords, exclude_keywords, tag_logic)
                
                return len(filtered_rows)
    else:
        # 没有标签或关键词过滤条件，直接统计
        query = f"SELECT COUNT(*) FROM threads{where_clause}"
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(query, params) as cursor:
                (cnt,) = await cursor.fetchone()
                return cnt

async def get_tag_vote_stats(thread_id: int):
    """返回该线程各标签的投票统计 (tag_name, up, down, total)"""
    query = """
    SELECT tags.name,
           SUM(CASE WHEN vote = 1 THEN 1 ELSE 0 END) AS up_votes,
           SUM(CASE WHEN vote = -1 THEN 1 ELSE 0 END) AS down_votes,
           COALESCE(SUM(vote), 0) AS total_score
    FROM thread_tags
    JOIN tags ON tags.tag_id = thread_tags.tag_id
    LEFT JOIN tag_votes ON tag_votes.tag_id = tags.tag_id
    WHERE thread_tags.thread_id = ?
    GROUP BY tags.name
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(query, (thread_id,)) as cursor:
            return await cursor.fetchall()

async def get_user_search_preferences(user_id: int):
    """获取用户搜索偏好"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT include_authors, exclude_authors, after_date, before_date, tag_logic, preview_image_mode FROM user_search_preferences WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    'include_authors': [int(x) for x in row[0].split(',') if x] if row[0] else [],
                    'exclude_authors': [int(x) for x in row[1].split(',') if x] if row[1] else [],
                    'after_date': row[2],
                    'before_date': row[3],
                    'tag_logic': row[4],
                    'preview_image_mode': row[5] if row[5] else 'thumbnail'
                }
            return {
                'include_authors': [],
                'exclude_authors': [],
                'after_date': None,
                'before_date': None,
                'tag_logic': 'and',
                'preview_image_mode': 'thumbnail'
            }

async def save_user_search_preferences(user_id: int, include_authors: list[int], exclude_authors: list[int], after_date: str | None, before_date: str | None, tag_logic: str, preview_image_mode: str = 'thumbnail'):
    """保存用户搜索偏好"""
    async with aiosqlite.connect(DB_PATH) as db:
        include_str = ','.join(map(str, include_authors)) if include_authors else ''
        exclude_str = ','.join(map(str, exclude_authors)) if exclude_authors else ''
        
        await db.execute("""
            INSERT INTO user_search_preferences(user_id, include_authors, exclude_authors, after_date, before_date, tag_logic, preview_image_mode)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                include_authors = excluded.include_authors,
                exclude_authors = excluded.exclude_authors,
                after_date = excluded.after_date,
                before_date = excluded.before_date,
                tag_logic = excluded.tag_logic,
                preview_image_mode = excluded.preview_image_mode
        """, (user_id, include_str, exclude_str, after_date, before_date, tag_logic, preview_image_mode))
        await db.commit()

async def get_thread_basic_info(thread_id: int):
    """获取帖子的基本信息（用于避免重复抓取首楼内容）"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT first_message_excerpt, thumbnail_url, reaction_count FROM threads WHERE thread_id = ?",
            (thread_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {}

async def delete_thread_index(thread_id: int):
    """删除帖子的所有相关索引数据"""
    async with aiosqlite.connect(DB_PATH) as db:
        # 删除帖子记录
        await db.execute("DELETE FROM threads WHERE thread_id = ?", (thread_id,))
        # 删除标签关联
        await db.execute("DELETE FROM thread_tags WHERE thread_id = ?", (thread_id,))
        # 删除标签投票（如果需要的话，也可以保留投票历史）
        # await db.execute("DELETE FROM tag_votes WHERE tag_id IN (SELECT tag_id FROM thread_tags WHERE thread_id = ?)", (thread_id,))
        await db.commit()

async def get_indexed_channel_ids():
    """获取所有已索引的频道ID列表"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT DISTINCT channel_id FROM threads") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def get_tags_for_author(author_id: int):
    """获取指定作者所有帖子中出现过的标签"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT DISTINCT tags FROM threads 
            WHERE author_id = ? AND tags IS NOT NULL AND tags != ''
        """, (author_id,)) as cursor:
            rows = await cursor.fetchall()
            
            # 收集所有标签名
            all_tags = set()
            for row in rows:
                tags_str = row[0] or ''
                tag_names = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
                all_tags.update(tag_names)
            
            # 返回格式：[(tag_id, tag_name)]，tag_id设为0因为我们主要用名称搜索
            return [(0, tag_name) for tag_name in sorted(all_tags)]

def _filter_threads(threads: list[dict], include_tags: list[str], exclude_tags: list[str], keywords: str, exclude_keywords: str = "", tag_logic: str = "and") -> list[dict]:
    """在Python中过滤帖子的标签和关键词
    
    Args:
        threads: 帖子列表，每个帖子必须包含tags字段，并可能包含title和first_message_excerpt字段
        include_tags: 必须包含的标签列表
        exclude_tags: 必须排除的标签列表（OR逻辑）
        keywords: 关键词字符串，支持混合AND/OR逻辑
                 - 逗号（,或，）分隔AND组：必须满足所有组
                 - 每组内斜杠（/）分隔OR选项：只需满足组内任一关键词
                 - 示例："纯爱/甜，校园，男生/女生/学生"
                   表示：必须包含（纯爱或甜）且包含校园且包含（男生或女生或学生）
        exclude_keywords: 排除关键词字符串，支持AND（逗号分隔）和OR（斜杠分隔）逻辑
        tag_logic: 标签逻辑，"and"表示AND逻辑，"or"表示OR逻辑
    
    Returns:
        过滤后的帖子列表
    """
    if not include_tags and not exclude_tags and not keywords:
        return threads
    
    filtered_threads = []
    
    for thread in threads:
        # 检查标签过滤
        tags_str = thread.get('tags', '') or ''
        # 将标签字符串分割为标签列表，并去除空白
        thread_tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
        thread_tag_set = set(thread_tags)
        
        # 检查包含标签（根据tag_logic参数决定使用AND或OR逻辑）
        if include_tags:
            include_tag_set = set(include_tags)
            if tag_logic == "and":
                # AND逻辑：必须包含所有指定标签
                if not include_tag_set.issubset(thread_tag_set):
                    continue  # 不包含所有必需标签，跳过
            else:  # OR逻辑
                # OR逻辑：只需包含任意一个指定标签
                if not include_tag_set.intersection(thread_tag_set):
                    continue  # 不包含任何必需标签，跳过
        
        # 检查排除标签（OR逻辑：不能包含任何排除标签）
        if exclude_tags:
            exclude_tag_set = set(exclude_tags)
            if exclude_tag_set.intersection(thread_tag_set):
                continue  # 包含排除标签，跳过
        
        # 检查关键词过滤
        if keywords:
            title = (thread.get('title', '') or '').lower()
            excerpt = (thread.get('first_message_excerpt', '') or '').lower()
            
            # 支持混合AND/OR逻辑：
            # 1. 逗号分隔AND组（必须都满足）
            # 2. 每组内斜杠分隔OR选项（满足其中一个即可）
            # 例如：纯爱/甜，校园，男生/女生/学生
            
            # 支持中文逗号"，"和英文逗号","
            keywords_replaced = keywords.replace('，', ',')  # 统一转换为英文逗号
            and_groups = [group.strip() for group in keywords_replaced.split(',') if group.strip()]
            
            # 检查每个AND组是否满足
            all_groups_satisfied = True
            for group in and_groups:
                if '/' in group:
                    # OR逻辑：组内只需满足任意一个关键词
                    or_keywords = [kw.strip().lower() for kw in group.split('/') if kw.strip()]
                    group_satisfied = False
                    for keyword in or_keywords:
                        if keyword in title or keyword in excerpt:
                            group_satisfied = True
                            break
                    if not group_satisfied:
                        all_groups_satisfied = False
                        break
                else:
                    # 单个关键词：必须包含
                    keyword = group.strip().lower()
                    if keyword not in title and keyword not in excerpt:
                        all_groups_satisfied = False
                        break
            
            if not all_groups_satisfied:
                continue  # 不满足关键词条件，跳过
        
        # 检查排除关键词
        if exclude_keywords:
            # 排除关键词使用OR逻辑：包含任何一个排除关键词就排除该帖子
            # 支持中文逗号"，"和英文逗号","
            exclude_keywords_replaced = exclude_keywords.replace('，', ',')  # 统一转换为英文逗号
            exclude_keywords_list = [kw.strip().lower() for kw in exclude_keywords_replaced.split(',') if kw.strip()]
            
            # 检查是否包含任何排除关键词
            exclude_found = False
            for exclude_keyword in exclude_keywords_list:
                if exclude_keyword in title or exclude_keyword in excerpt:
                    exclude_found = True
                    break
            if exclude_found:
                continue  # 包含排除关键词，跳过该帖子
        
        # 通过所有过滤条件
        filtered_threads.append(thread)
    
    return filtered_threads