# 🏗️ Models 模块 (数据模型层)

## 📖 简介
`models` 模块定义了 BOT 所有的数据库实体模型。

本项目采用 [SQLModel](https://sqlmodel.tiangolo.com/) (基于 SQLAlchemy 和 Pydantic) 进行开发，底层数据库采用 SQLite

---

## 🗺️ 核心实体分类

### 1. 核心内容模型
*系统中最基础的实体，代表了从 Discord 抓取的数据。*

- `thread.py`: 核心模型。存储 Discord 论坛帖子的所有元数据，包括标题、回复数、反应数、首楼摘要、图片链接列表等。
- `author.py`: 存储 Discord 用户/作者信息。通过 `author_id` 与帖子关联。
- `tag.py`: 存储 Discord 标签。一个帖子可以有多个标签，一个标签也可以属于多个帖子。

### 2. 标签与评价系统
*负责标签投票及互斥逻辑。*

- `thread_tag_link.py`: 已废弃，仅作迁移备份；保留旧绑定和旧票数原貌，业务不再读写。
- `tag_binding.py`: 帖子与书单的统一标签绑定轮次，区分 DC 同步和本地绑定，保存有效状态及汇总票数。
- `tag_vote.py`: 按绑定轮次与用户保存本地绑定的当前投票。
- `tag_vote.py`: 记录具体用户对某个帖子下某个标签的投票行为（赞成/反对）。
- `mutex_tag_group.py` & `mutex_tag_rule.py`: 定义互斥标签组（如“同人”和“原创”互斥）。用于冲突时提醒管理组。

### 3. 用户互动与偏好 (User Engagement)
*存储用户个人的操作数据和定制设置。*

- `user_collection.py`: 通用收藏记录。支持收藏“帖子”或“书单”。
- `thread_follow.py`: 帖子关注记录。用于追踪帖子的更新状态及未读统计。
- `user_search_preferences.py`: 用户的搜索偏好设置。记录用户习惯的排序方式、过滤频道、每页展示数量等。
- `user_update_preference.py`: 记录用户对特定帖子更新提醒的特殊偏好（如“不再提醒”、“自动同步”）。

### 4. 社区策展 (Curation Features)
*用于内容分发。*

- `booklist.py` & `booklist_item.py`: “书单”功能。允许用户将多个帖子聚合在一起并添加评论。
- `banner_application.py` / `carousel.py` / `waitlist.py`: 轮播图管理系统。包含申请记录、当前展示列表和候补队列。

### 5. 系统配置 (System Config)
- `bot_config.py`: 存储全局配置项。如 UCB1 算法的探索因子、全局总展示次数 $N$ 等。

---

## 🛠️ 开发规范

### 1. Discord ID 处理
由于 Discord ID 是超长整数 (Snowflake)，在 SQLModel 中定义时应明确使用 `BigInteger` 映射，以防止 32 位溢出：
```python
from sqlmodel import BigInteger, Column, Field
# ...
id: int = Field(sa_column=Column(BigInteger, primary_key=True))
```

### 2. 时间戳处理
系统统一使用 UTC 时间。
- `default_factory=lambda: datetime.now(timezone.utc)`：用于记录创建时间。
- `sa_column_kwargs={"onupdate": ...}`：用于记录更新时间。
