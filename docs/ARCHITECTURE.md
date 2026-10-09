# 项目架构

项目由 **Discord Bot** 和 **FastAPI 服务** 两大运行时组成，共享同一个 PostgreSQL 数据库和 Redis 缓存。

## 模块总览

```
src/
├── bot_main.py                  # Discord 机器人入口
├── api_main.py                  # FastAPI 服务入口
│
├── api/                         # FastAPI RESTful 接口层，OAuth2 + JWT
│   └── v1/
│       ├── routers/             # 路由层（auth / search / discovery / ...）
│       ├── schemas/             # Pydantic 请求/响应模型
│       └── dependencies/        # 认证、限流依赖
│
├── auditor/                     # 数据库 Discord 对账、幽灵数据清理
├── author/                      # 异步用户信息拉取与缓存
├── backup/                      # 定时数据库备份至 S3
├── banner/                      # Banner 轮播申请与审核系统
├── booklist/                    # 书单创建与帖子批量管理
├── collection/                  # 帖子收藏 / 右键菜单
├── config/                      # 运行时配置管理（UCB1 排序算法配置 / 互斥标签）
├── core/                        # 数据仓库层、同步服务、缓存
├── discovery/                   # 首页广场多轨道推荐
├── dto/                         # 数据传输对象定义
├── indexer/                     # 论坛频道索引构建与实时更新
├── meta/                        # 元数据(频道、用户身份组)
├── models/                      # 数据库实体定义
├── preferences/                 # 用户搜索偏好管理
├── search/                      # 关键词搜索、标签过滤、排序
├── shared/                      # 公共基础设施（API 调度器、DB 引擎、工具类）
├── tag/                         # 标签服务
├── ThreadManager/               # 帖子生命周期管理、事件监听、互斥标签规则
├── tournament/                  # 赛事书单管理
└── update_detector/             # AI 更新检测（DeepSeek）与 Token 试算
```
