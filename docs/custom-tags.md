# 自定义标签接口与部署


社区征集数据的批量导入见 [批量导入自定义 TAG](custom-tags-import.md)，支持容器内只读预检、整批事务提交和重复执行检查。

### 深渊向标签

`add_abyss_tag_flag` 接在 `add_tag_description` 后，为统一 `tag` 表新增 `is_abyss BOOLEAN NOT NULL DEFAULT FALSE`。该字段同时适用于 DC 与自定义概念，但 DC 同步不会根据频道自动修改；BOT 管理员可在创建或更新标签时显式维护。

`is_abyss` 只控制候选发现，不改变既有绑定：无 `abyss.required_role_id` 的用户不会在标签池、关系、统计、搜索建议和搜索可用标签中看到深渊向实体，但帖子、书单、通知、搜索结果及目标标签快照仍按事实返回已绑定标签。已知名称或内部 ID 仍可用于筛选。作者审核、管理审计和 BOT 管理写入沿用各自原权限，不额外要求深渊身份组。

所有标签实体响应及本地绑定响应返回 `is_abyss`。创建请求省略时默认为 `false`；PATCH 未传保持原值，显式 `null` 拒绝。切换方向不结束绑定或申请；合并方向不同的同名标签时沿用目标标签方向。

Discord BOT 的全局搜索和搜索偏好下拉候选只列虚拟标签与有效 DC 标签，不列自定义标签；频道搜索仍使用频道原生标签。作者和收藏搜索继续按实际绑定提供候选。已保存的自定义标签偏好虽不作为全局/偏好下拉选项，仍显示为已选条件、继续参与查询，并在编辑其他选项时保留。结果页继续显示全部已绑定标签。

### 标签含义描述

`add_tag_description` 接在 `normalize_discord_tags` 后，为 `tag` 新增 `description TEXT NOT NULL DEFAULT ''`；其后再执行 `add_abyss_tag_flag`。按现有维护流程备份数据库、完成迁移后再启动新代码；相应降级会删除新增字段内容。

创建标签可传 `description`，省略默认为空字符串。PATCH 可单独提交 `{"description":"标签的含义说明"}`，未传保持原值，`{"description":""}` 清空，显式 `null` 拒绝。描述为最多 2000 字的纯文本，清理首尾空白、保留内部换行；BOT `/tag_manage` 的 create/update 支持相同字段与校验，仍仅 BOT 管理员可操作。

标签实体、标签池及继承标签公共响应的绑定快照返回 `description`，无描述返回 `""`。描述不参与搜索。DC 标签描述允许人工维护，DC 同步不覆盖；合并保留目标描述，旧描述保留在软删除源实体中，不拼接。管理审计记录描述前后值。

## 部署

禁止让旧 BOT/API 与迁移同时写入；先停止服务并备份完整数据库，再运行迁移、校验并统一启动新版本。当前迁移链为 `add_custom_tag_governance` → `normalize_discord_tags` → `add_tag_description` → `add_abyss_tag_flag`；已上线数据库直接升级，不需要删库，也不改写旧 revision。升级后旧版本代码不能继续使用该数据库。

首次统一绑定迁移 `add_custom_tag_governance` 保留原始 `thread_tag_link`（含旧票数）作为只读操作备份，清空旧投票并建立轮次投票表。本次归一迁移继续原样保留备份表和所有已有轮次投票，不再清空票数；被合并的旧轮次结束，目标已有轮次保留，新建轮次从零票开始。最终不创建 `custom_tag_binding`、`custom_tag_vote`。备份表不含上线后的变更，不能代替完整回滚备份。

所有 TAG 表不使用数据库外键；引用检查、依赖清理在代码事务中执行。目标绑定、申请、重提限制和新操作日志的帖子目标使用内部 `Thread.id`；API、站内通知和网页链接继续使用 Discord 帖子 ID。日志 `detail.target_id_kind="internal"` 标明新记录语义，不改写既有审计事实。

### 标准标签与 DC 来源

| 表 | 职责及主要字段 |
| --- | --- |
| `tag` | 标准概念：`id`、`name`、`source`、`category`、`is_abyss`、`enabled`、`deleted_at`；`originated_from_discord` 标记是否允许转换后暂时未分类 |
| `discord_tag_source` | DC 身份映射：BIGINT `id`、唯一 `discord_tag_id`、`channel_id`、标准 `tag_id`、原始 `name`、`synced_at`、`deleted_at` |
| `discord_tag_sync_state` | 完整频道快照检查点：`channel_id`、`observed_at`，空标签列表也更新，拒绝较旧事件覆盖 |
| `tag_binding` | 一轮绑定：BIGINT `id`、目标类型及内部 ID、标准 `tag_id`、`binding_source`、可空 `discord_source_id`、操作者、起止时间、结束原因及汇总票数 |

不同频道中**名称完全相同**的 DC 标签映射到一个标准标签，不忽略大小写、空白，也不按别名归一。一个频道中的一个标准概念最多对应一个有效 DC 来源。搜索和书单挂标都使用标准 `tag.id`；搜索绑定无需联查来源表。现有别名、关系、申请、重提限制、投票、通知任务和审计表继续保留各自职责。

DC 改名会将该来源映射到新名称的标准概念，并切换该来源对应的帖子绑定；其他频道和书单的旧概念绑定不变。确认 DC 来源删除后，其帖子绑定转为本地绑定。最后一个有效来源因删除或改名离开时，旧概念转为自定义来源；分类冲突则清空分类并通知 BOT 管理员，保留名称、ID 和绑定。以后 DC 再出现同名标签时建立 DC 概念，遇到同名自定义概念只提醒管理员，不自动合并。

完整频道抓取失败、无权限不视为删除。启动及完整同步补偿离线变更。来源未知的历史记录允许 `channel_id=null`，成功获取频道快照后补齐。

### 前端如何判断能否操作

- `source` 表示**标准概念的当前来源**。帖子新增候选选 `source=custom`；书单不限制来源。
- `binding_source` 表示**这个标签如何绑定到当前内容**。`discord_sync` 对应 `readonly=true`，不可编辑、删除或投票；`local` 对应 `readonly=false`，按作者、管理组和社区治理规则操作。
- 书单绑定始终为 `local`。不能仅凭 `source=discord` 锁定书单标签。
- 标签池、完整标签快照和标签建议的 `discord_sources` 返回有效来源数组，包含来源记录 `id`、`discord_tag_id`、可空 `channel_id` 和 `name`。原先单个 `discord_tag_id` 字段移入该数组；一个标准概念可以有多个 DC 来源。
- DC 绑定另有 `discord_source_id`，指出当前帖子对应的来源记录。帖子、书单摘要的 `custom_tags` 仍表示本地绑定，包含 `binding_source=local` 和 `readonly=false`。
- 快照新增 `over_limit` 和 `conflicting_pairs`（互斥标签 ID 对）。DC 同步可能留下超限或互斥状态，接口保留事实并提示；纯删除可执行，含新增的本地操作必须满足上限和互斥规则。

DC 接管已有本地绑定时，旧轮次结束，新建零票 DC 轮次；以后从帖子上移除 DC 标签不会恢复旧本地轮次。

### 同名标签合并

仅 BOT 管理员可以执行，且两个标签的标准名必须完全相同。包含 DC 概念时保留 DC 概念。先调用 `GET /v1/tags/{旧标签ID}/merge-preview?target_tag_id={保留标签ID}`，获取影响数量、`can_merge`、`conflicts` 和 `version`；确认后调用 `POST /v1/tags/{旧标签ID}/merge`：

```json
{"target_tag_id":"456","version":"预检返回的版本"}
```

预检与执行之间相关数据发生变化时返回 409，要求重新预检；关系自环、包含循环等冲突会阻止整个合并。迁移别名、关系和来源映射，重复项去重。原目标上的永久禁止重提限制取并集；旧标签待审核申请标记 `failed/tag_merged`，取消待发送提醒，重新申请仍检查权限与限制。目标已有绑定保留票数，旧轮次和历史投票不改写。

合并后的旧标签直接软删除，**没有 `merged_into_tag_id`，不自动重定向旧 ID**。前端提交失效 ID 收到 `409 / tags_changed` 后提示“标签已发生变化，请刷新后重试”，重新获取候选和目标快照，不自动重试。合并审计保存前后 ID 和轮次，沿用管理权限；已合并标签不能通过恢复接口复活。

归一迁移会将现有同名 DC 实体以及同名未删除自定义实体并入 DC 概念，关系冲突时整个迁移回滚。维护窗口前应备份并核对这些同名实体。迁移不提供自动拆分降级，回滚使用维护窗口完整备份。


## 公共约定

- 所有接口位于 `/v1/tags`，需要现有登录认证。
- 新接口的 ID 响应均为十进制字符串；请求 ID 在 OpenAPI 中声明为 `string | integer`，支持十进制字符串或整数，后端在进入业务层前统一转换为整数。这一约定同样适用于路径 ID、`tag_ids`、帖子搜索及书单筛选的 `include_tag_ids` / `exclude_tag_ids` 数组。前端请使用字符串保存和提交 BIGINT ID，避免 JavaScript Number 丢失精度；非法 ID 返回 422。
- `target_type` 为 `thread` 或 `booklist`。
- 时间均为 UTC；七天期限从提议提交时开始，不依赖通知是否成功。
- 分类：1 癖好、2 作品、3 角色、4 特质、5 情节、6 背景、7 玩法。
- DC 同步绑定只读、不可投票，占用帖子 12 个名额。帖子手动选标仅允许自定义实体；书单可选择 DC 或自定义实体，以本地绑定参与治理。
- 当前自定义票数始终读取数据库；前端自行决定高亮，搜索不按票数排序。

## 当前用户的管理身份

前端通过 `GET /v1/meta/role` 查询**当前登录用户**的管理身份，无需请求体或用户 ID 参数：

```json
{
  "is_management_member": false,
  "is_bot_admin": false
}
```

| 字段 | 含义 |
| --- | --- |
| `is_management_member` | 当前用户是否拥有**主服务器**配置的 `management_role_id` 身份组 |
| `is_bot_admin` | 当前用户的 Discord ID 是否在 `bot_admin_user_ids` 配置中 |

两项独立判断，可以都为 true、都为 false，或仅一项为 true；BOT 管理员不会自动被标记为管理组成员。管理组字段不代表其他服务器的身份，也不表示当前用户是某个帖子的作者或某个书单的所有者。

前端可根据这两个身份决定是否显示管理入口，例如只有 `is_bot_admin=true` 时显示标签池维护入口。具体操作接口仍执行原有权限校验，按钮显示不能替代后端授权。

未登录返回 401。用户不是主服务器成员时，`is_management_member=false`，BOT 管理员身份仍按配置返回；未配置管理组身份组时也返回 false。成员查询暂时失败或服务未初始化返回 503，前端应提示或重试，不要将查询失败当成确定没有管理身份。响应包含 `Cache-Control: private, no-store`，不要跨用户缓存结果。

## 标签池与管理

以下路径均接在 `/v1/tags` 后，所有写接口均仅允许 BOT 管理员使用。

| 方法和路径 | 含义 |
| --- | --- |
| GET /categories | 分类值和中文名 |
| GET / | 完整标签池，支持 q、source、category、selectable、include_deleted |
| GET /relations | 未删除标签之间的全部直接关系边 |
| POST / | 创建标签，成功返回 201 |
| PATCH /{tag_id} | 部分修改名称、分类、启用状态 |
| DELETE /{tag_id} | 软删除标签 |
| POST /{tag_id}/restore | 恢复标签实体 |
| PUT /{tag_id}/aliases | 完整替换别名 |
| POST /{tag_id}/relations | 添加关系 |
| DELETE /{tag_id}/relations/{kind}/{target_tag_id} | 删除关系 |

标签池省略 `source` 时同时返回 DC 和自定义实体；`source=custom` 仅返回自定义标签（包括 DC 删除后转换的标签），`source=discord` 仅返回 DC 原生标签。来源筛选可与关键词、分类和状态条件组合，非法来源值返回 422。帖子挂标候选可请求 `GET /v1/tags?source=custom&selectable=true`；书单挂标候选省略 `source` 即可。接口不分页，一次按分类、名称和 ID 排序返回当前权限与筛选条件下的全部匹配项。默认 `selectable=true`，只列出启用且未删除标签；`selectable=false` 包括停用标签。查询已删除记录需 BOT 管理员，并设置 `include_deleted=true`。别名可同时命中多个标准标签。

标签池响应使用统一包装，`total` 直接取完整 `results` 的长度，不执行额外计数查询，因此两者数量始终相等：

```json
{
  "results": [],
  "total": 0
}
```

服务端仅缓存无关键词、无分类且不包含已删除记录的书单候选、帖子自定义候选和管理池；缓存按深渊标签可见权限隔离，标签实体或 Discord 来源实际变化后失效。其他筛选直接查询数据库，Redis 不可用时也会自动回源数据库。

创建 `POST /v1/tags`，名称和分类必填，别名可选：

```json
{"name":"爱丽丝(BA)","category":3,"aliases":["Alice","アリス"]}
```

修改 `PATCH /v1/tags/123`，未传字段保持不变。`name`、`category`、`enabled` 均可省略，但传入时不能为 `null`；空对象 `{}` 也会被拒绝，返回 422。`{"enabled":false}` 是有效的停用请求。OpenAPI 中这些字段为可选且不可为 null。名称、分类和启用状态在同一事务中修改：

```json
{"name":"爱丽丝(蔚蓝档案)","enabled":false}
```

`enabled=false` 为停用，`true` 为重新启用。停用保留现有展示和搜索。已软删除标签必须通过恢复接口恢复，不能通过 `enabled` 绕过。

仍有有效 DC 来源的标准标签可以修改分类、别名、关系和启用状态；不能单独改名或软删除。停用不阻止 DC 同步。来源全部失效并转为自定义后，才适用普通自定义标签的改名与软删除规则。

替换别名 `PUT /v1/tags/123/aliases`，空列表表示清空：

```json
{"aliases":["Alice","アリス"]}
```

软删除使用 `DELETE /v1/tags/123`，恢复使用 `POST /v1/tags/123/restore`，均无请求体。软删除结束现有绑定、隐藏搜索、结束待审核项。恢复仅恢复实体，不恢复绑定。分类与标准名唯一性包括软删除记录；冲突时返回 `deleted_tag_exists` 和原标签 ID，提示恢复。

添加关系 `POST /v1/tags/123/relations`：

```json
{"target_tag_id":"456","kind":"implies"}
```

`kind` 为 `implies` 或 `excludes`，删除上述关系使用 `DELETE /v1/tags/123/relations/implies/456`。包含关系禁止循环，互斥关系对称。前端自行计算层级与选择父标签，后端只校验最终选择的集合。

手动创建、修改的自定义标准名进行 NFC 规范化和首尾空白清理，不自动翻译或识别同义词。DC 标准名严格跟随原始名称，维护其他字段不会改变名称。

BOT 的 `/tag_manage payload` 仍保留命令形式，与 HTTP 拆分互不影响。例如 `{"operation":"create","name":"爱丽丝(BA)","category":3}`。支持 create、update、disable、enable、delete、restore、add_relation、remove_relation；已有标签操作携带 tag_id，关系操作再携带 target_tag_id 和 kind。命令仅允许配置中的 BOT 管理员使用，不会发布公共消息。

## 帖子和书单治理

### 路径怎么读

以下路径均省略了统一前缀 `/v1/tags`。花括号中的内容是占位参数，调用时需要换成实际值，不要保留花括号。

| 路径参数 | 含义与取值 |
| --- | --- |
| `{target_type}` | 内容类型：`thread` 表示帖子，`booklist` 表示书单 |
| `{target_id}` | 当类型为 `thread` 时使用 **Discord 帖子 ID**；当类型为 `booklist` 时使用书单 ID |
| `{tag_id}` | 标签池中标签实体的内部 ID，不是 `discord_tag_id` |
| `{proposal_id}` | 一条添加标签申请的 ID，由提议接口及申请列表返回 |
| `{binding_id}` | 某个标签挂到该内容上的**本轮绑定 ID**，由标签读取接口返回；不是标签 ID。解绑后重新挂标会产生新的绑定 ID |

`proposals` 表示添加标签的申请，`votes` 表示本轮投票，`audit` 表示操作记录。`review_queue=true` 是查询参数，不是路径的一部分，用于切换到作者／管理组的待审核队列。

下面路径中的 `tag` 是固定文字，不是需要替换的参数：`/tag/{tag_id}/audit` 查询标签实体的管理历史，例如重命名、停用和恢复；`/thread/{target_id}/audit` 或 `/booklist/{target_id}/audit` 查询该内容上的挂标、解绑、审核和投票历史。

### 接口路径表

| 方法和路径 | 含义 |
| --- | --- |
| GET /{target_type}/{target_id} | 原生标签、自定义标签、票数、本人投票与版本 |
| PUT /{target_type}/{target_id} | 作者或管理组替换全部自定义标签 |
| POST /{target_type}/{target_id}/proposals | 提议一个标签 |
| GET /{target_type}/{target_id}/proposals | 本人的申请历史 |
| GET /{target_type}/{target_id}/proposals?review_queue=true | 作者或管理组的待审核队列 |
| PUT /{target_type}/{target_id}/proposals/{proposal_id} | 同意或拒绝 |
| PUT /{target_type}/{target_id}/votes/{binding_id} | 设置本轮投票 |
| GET /{target_type}/{target_id}/audit | 管理组/BOT 管理员的操作记录 |
| GET /tag/{tag_id}/audit | BOT 管理员的标签池操作记录 |

### 完整请求示例

以下数字仅作示例，实际调用需使用接口返回或目标内容对应的 ID。

| 完整请求 | 含义 |
| --- | --- |
| `GET /v1/tags/thread/123` | 查看 Discord 帖子 123 的标签、票数和版本 |
| `PUT /v1/tags/thread/123` | 作者或管理组替换帖子 123 的全部自定义标签 |
| `POST /v1/tags/thread/123/proposals` | 为帖子 123 提议标签，请求体为 `{"tag_id":"456"}` |
| `GET /v1/tags/thread/123/proposals` | 查看我为帖子 123 提交的申请 |
| `GET /v1/tags/thread/123/proposals?review_queue=true` | 作者或管理组查看帖子 123 的待审核申请 |
| `PUT /v1/tags/thread/123/proposals/789` | 审核帖子 123 的申请 789，请求体为 `{"approve":true}` 或 `{"approve":false}` |
| `PUT /v1/tags/thread/123/votes/321` | 对帖子 123 的挂标轮次 321 投票，请求体为 `{"vote":1}`、`{"vote":-1}` 或 `{"vote":0}` |
| `GET /v1/tags/thread/123/audit` | 管理组／BOT 管理员查看帖子 123 的标签操作记录 |
| `GET /v1/tags/booklist/42` | 查看书单 42 自身的标签，不是查询书单内所有帖子的标签 |
| `POST /v1/tags/booklist/42/proposals` | 为书单 42 提议标签，其余审核、投票路径同样将 `thread/123` 换成 `booklist/42` |
| `GET /v1/tags/tag/456/audit` | BOT 管理员查看标签实体 456 的管理历史 |

### 请求体与操作规则

#### `version` 是什么

`version` 是后端返回的**当前标签集合的版本标记**，用于判断用户编辑期间，标签是否已被其他操作修改。它不是作品的版本号，也不是标签 ID。

之所以需要它，是因为 PUT 会替换全部本地绑定标签。例如你读取到标签 A、B，准备修改为 A、B、D；此时管理组已经添加了 C。如果直接保存你的集合，就会误删 C。携带读取时的 `version` 后，后端可以识别这种冲突并拒绝覆盖。

前端将它当作一个不透明字符串即可：**保存 GET 返回的值，PUT 时原样传回，不自行生成、解析或递增。** 即使标签列表为空，也必须使用 GET 返回的版本标记。每个帖子／书单分别保存自己的版本，不要跨目标复用。

#### 前端对接步骤

1. 打开编辑页时调用 `GET /v1/tags/thread/123`。书单对应 `GET /v1/tags/booklist/42`。
2. 从响应中保存 `version`，并用 `tags` 初始化编辑状态。响应结构示意如下，版本字符串仅为占位示例，实际值以接口返回为准：

```json
{
  "version": "后端返回的版本标记",
  "tags": []
}
```

3. 用户确认修改后，向同一路径发送 PUT，提交完整的目标本地绑定标签 ID 集合（帖子限自定义实体，书单也可选择 DC 实体），以及打开编辑页时保存的版本：

```json
{
  "version": "后端返回的版本标记",
  "tag_ids": ["123", "456"]
}
```

4. 保存成功后，使用 PUT 响应中的 `tags` 和 `version` 更新页面状态；后续编辑使用这次响应的新版本。

#### 版本冲突时怎么处理

如果读取后发生了挂标、解绑或原生标签同步变更，旧版本提交会被拒绝，**本次替换不会生效**。后端返回 HTTP 409，错误体为：

```json
{
  "detail": {
    "code": "stale_version",
    "message": "标签已变化，请刷新后重试"
  }
}
```

前端应提示用户标签已变化，重新 GET 最新集合及版本，并让用户确认最终选择后再提交。可以保留本地编辑内容用于对比，但**不要仅替换成新 `version` 就自动重试旧集合**，否则仍可能覆盖别人刚完成的修改。

通过 `detail.code == "stale_version"` 识别版本冲突，不要把所有 409 都当成版本过期：数量超限、互斥关系等也可能返回 409，应展示相应错误原因。

#### 其他操作规则

完整替换不提交 `binding_source=discord_sync` 的只读绑定；书单本地绑定的 DC 标签需要提交。交集保留票数，未传入的本地绑定标签解绑，新绑定开启零票轮次。纯删除允许处理历史超限或冲突；含新增标签的操作要求最终集合合法。`version` 仅用于完整集合替换；提议、审核和投票接口不需要此字段。

提议提交 `{"tag_id":"123"}`，审核提交 `{"approve":true}` 或 `{"approve":false}`。同目标同标签最多一条待审核申请，重复提议不延长期限。拒绝或手动删除后可立即重提。曾被投票移除的标签永久禁止普通用户重新提议，作者与管理组可直接添加。

投票提交 `{"vote":1}`、`{"vote":-1}` 或 `{"vote":0}`，分别表示赞、踩、撤票。重复请求幂等，改票同时更新双方计数。净负票超过 5 时自动解绑，包括作者和管理组添加的标签。旧轮次 ID 不可用于新轮次。

提议和审计分页使用 `offset`，每页最多 100 条。普通响应不返回他人的投票身份。管理组只查询其授权目标的操作记录，BOT 管理员可查询全部目标。

## 搜索与详情

帖子和书单统一使用 `include_tag_ids`、`exclude_tag_ids`，取值为内部标签 ID，不按来源拆分参数。帖子可在同一列表混合原生和自定义标签，`tag_logic` 的 AND/OR 对整个列表生效。书单按自身实际绑定匹配，不继承单内帖子的标签。旧的按名称筛选参数保留兼容；同时提供名称和 ID 条件时，两组条件共同约束结果。

公开和我的书单列表新增同名查询参数，以及 `tag_logic=and|or`；多个 ID 使用重复查询参数。帖子详情展示上下文、书单摘要和书单详情新增 `custom_tags`，包含标准名、分类、挂标轮次及正负票数。

别名既可用于标签池候选检索，也可直接通过帖子和书单的 `include_tags` / `exclude_tags` 筛选；不沿关系扩大匹配。停用标签的现存绑定仍能筛选，软删除标签不再命中。

## 后台任务与通知

BOT 每分钟处理到期申请，锁定目标后重新检查；容量、互斥、停用、权限等业务失败进入 `failed` 状态，并在 `reason` 返回原因。数据库或权限服务临时故障留待下轮重试。

提议通知持久化入库。BOT 优先私信作者，私信禁止时在原帖发送不含具体待审核标签的提醒；书单或不可写帖子使用内部 notifications。临时网络故障指数退避重试。Discord 发送与数据库提交无法组成原子事务，极端崩溃窗口下提醒可能重复，业务申请与挂标不会因此重复。

内部通知新增 `type=tag_review`，返回 `target_type`、字符串 `target_id` 和 `proposal_id`，`thread` 可为空。新增 `POST /v1/notifications/{notification_id}/read`，只标记当前用户拥有的通知。



## 帖子与书单按别名筛选

标签标准名为“测试”、别名为“试测”时，帖子搜索请求可直接传 `"include_tags": ["试测"]`，响应仍展示标准名“测试”。普通 `keywords` 不会自动转为标签筛选。标签池与搜索建议仍支持模糊匹配。

书单公开列表 `GET /v1/booklist/list/page`、我的列表 `GET /v1/booklist/my/list/page` 支持重复查询参数，例如 `?include_tags=试测&include_tags=纯爱&tag_logic=and`。只匹配书单自身绑定，不继承单内帖子的标签。

一个名称命中多个实体时组内 OR，不同名称组按 `tag_logic` 组合。AND 中有未知名称则无结果；OR 中未知名称不妨碍其他名称命中。排除名称命中任一实体即排除，未知排除名称不影响结果。名称与 ID 筛选同时传入时两组条件共同生效，ID 仍精确匹配。停用实体的已有绑定仍可搜索，软删除实体和结束绑定不参与匹配。
