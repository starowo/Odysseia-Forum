"""分离标准标签与 DC 来源；维护窗口内执行，保留历史轮次和旧表备份。"""

from alembic import op
import sqlalchemy as sa

revision = "normalize_discord_tags"
down_revision = "add_custom_tag_governance"
branch_labels = None
depends_on = None


def upgrade():
    """将完全同名 DC 实体归一，迁移当前关联并校验完整性。"""
    op.execute("SELECT pg_advisory_xact_lock(73902141)")
    op.execute("ALTER TABLE tag DROP CONSTRAINT ck_tag_source_category")
    op.execute(
        "ALTER TABLE tag ADD COLUMN originated_from_discord BOOLEAN NOT NULL DEFAULT FALSE"
    )
    op.execute(
        "UPDATE tag SET originated_from_discord = TRUE WHERE discord_tag_id IS NOT NULL OR source='discord'"
    )
    op.execute("""CREATE TABLE discord_tag_source (
        id BIGSERIAL PRIMARY KEY, discord_tag_id BIGINT NOT NULL UNIQUE,
        channel_id BIGINT, tag_id BIGINT NOT NULL, name VARCHAR NOT NULL,
        synced_at TIMESTAMP, deleted_at TIMESTAMP)""")
    op.execute(
        "CREATE INDEX ix_discord_tag_source_channel_id ON discord_tag_source(channel_id)"
    )
    op.execute(
        "CREATE INDEX ix_discord_tag_source_tag_id ON discord_tag_source(tag_id)"
    )
    op.execute(
        "CREATE TABLE discord_tag_sync_state (channel_id BIGINT PRIMARY KEY, observed_at TIMESTAMP NOT NULL)"
    )
    op.execute("ALTER TABLE tag_binding ADD COLUMN discord_source_id BIGINT")
    op.execute(
        "CREATE INDEX ix_tag_binding_discord_source_id ON tag_binding(discord_source_id)"
    )
    # 每个原生身份独立保留；转换后的历史来源不再视为有效。
    op.execute("""INSERT INTO discord_tag_source(discord_tag_id,channel_id,tag_id,name,synced_at,deleted_at)
        SELECT discord_tag_id,discord_channel_id,id,name,discord_synced_at,
          CASE WHEN source='discord' AND deleted_at IS NULL THEN NULL
               ELSE COALESCE(deleted_at,discord_synced_at,CURRENT_TIMESTAMP AT TIME ZONE 'UTC') END
        FROM tag WHERE discord_tag_id IS NOT NULL""")
    op.execute("""UPDATE tag_binding b SET discord_source_id=s.id FROM discord_tag_source s
        WHERE b.tag_id=s.tag_id AND b.binding_source='discord_sync'""")
    op.execute("""DO $$ BEGIN IF EXISTS(SELECT 1 FROM tag_binding WHERE binding_source='discord_sync' AND discord_source_id IS NULL)
        THEN RAISE EXCEPTION 'DC binding has no source; repair before migration'; END IF; END $$""")
    # 同名 DC 保留最小内部 ID；当前同名自定义测试实体并入该标准概念。
    op.execute("""CREATE TEMP TABLE normalized_tag_map ON COMMIT DROP AS
        SELECT t.id AS old_id,COALESCE(d.keep_id,t.id) AS new_id
        FROM tag t LEFT JOIN (SELECT name,MIN(id) AS keep_id FROM tag
          WHERE source='discord' AND deleted_at IS NULL GROUP BY name) d
          ON t.name=d.name AND t.deleted_at IS NULL""")
    op.execute("CREATE UNIQUE INDEX ON normalized_tag_map(old_id)")
    op.execute("""DO $$ BEGIN IF EXISTS(SELECT 1 FROM discord_tag_source s JOIN normalized_tag_map m ON m.old_id=s.tag_id
        WHERE s.deleted_at IS NULL AND s.channel_id IS NOT NULL GROUP BY s.channel_id,m.new_id HAVING count(*)>1)
        THEN RAISE EXCEPTION 'Multiple live DC sources in one channel map to same concept'; END IF; END $$""")
    op.execute("""CREATE TEMP TABLE normalized_relations ON COMMIT DROP AS SELECT DISTINCT
        CASE WHEN r.kind='excludes' THEN LEAST(a.new_id,b.new_id) ELSE a.new_id END source_id,
        CASE WHEN r.kind='excludes' THEN GREATEST(a.new_id,b.new_id) ELSE b.new_id END target_id,r.kind
        FROM tag_relation r JOIN normalized_tag_map a ON a.old_id=r.source_id JOIN normalized_tag_map b ON b.old_id=r.target_id""")
    op.execute("""DO $$ BEGIN IF EXISTS(SELECT 1 FROM normalized_relations WHERE source_id=target_id)
        THEN RAISE EXCEPTION 'Tag merge creates self relation; resolve before migration'; END IF;
        IF (SELECT count(*) FROM tag_relation r LEFT JOIN tag a ON a.id=r.source_id LEFT JOIN tag b ON b.id=r.target_id WHERE a.id IS NULL OR b.id IS NULL)>0
        THEN RAISE EXCEPTION 'Orphan tag relation; repair before migration'; END IF; END $$""")
    # 用迁移自身的拓扑校验，避免依赖未来版本的业务代码。
    edges = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT source_id,target_id FROM normalized_relations WHERE kind='implies'"
            )
        )
        .all()
    )
    graph, degree = {}, {}
    for a, b in edges:
        graph.setdefault(a, []).append(b)
        degree.setdefault(a, 0)
        degree[b] = degree.get(b, 0) + 1
    roots = [a for a, n in degree.items() if n == 0]
    visited = 0
    while roots:
        a = roots.pop()
        visited += 1
        for b in graph.get(a, []):
            degree[b] -= 1
            if degree[b] == 0:
                roots.append(b)
    if visited != len(degree):
        raise RuntimeError("标签归一产生包含循环，迁移已回滚，请先处理关系")
    # 提前保存有效关系用于迁移后逐对核对，不触碰已结束轮次。
    op.execute("""CREATE TEMP TABLE normalized_bindings ON COMMIT DROP AS
        SELECT b.*,m.new_id,ROW_NUMBER() OVER(PARTITION BY b.target_type,b.target_id,m.new_id
          ORDER BY (b.binding_source='discord_sync') DESC,(b.tag_id=m.new_id) DESC,b.id) AS priority
        FROM tag_binding b JOIN normalized_tag_map m ON m.old_id=b.tag_id WHERE b.ended_at IS NULL""")
    op.execute("""UPDATE tag_binding b SET ended_at=CURRENT_TIMESTAMP AT TIME ZONE 'UTC',end_reason='tag_merged'
        FROM normalized_bindings n WHERE n.id=b.id AND (n.tag_id<>n.new_id OR n.priority<>1)""")
    op.execute("""INSERT INTO tag_binding(target_type,target_id,tag_id,binding_source,discord_source_id,actor_id,created_at,upvotes,downvotes)
        SELECT target_type,target_id,new_id,binding_source,discord_source_id,NULL,CURRENT_TIMESTAMP AT TIME ZONE 'UTC',0,0
        FROM normalized_bindings WHERE priority=1 AND tag_id<>new_id""")
    op.execute(
        """UPDATE discord_tag_source s SET tag_id=m.new_id FROM normalized_tag_map m WHERE s.tag_id=m.old_id"""
    )
    op.execute("""INSERT INTO tag_alias(tag_id,name) SELECT m.new_id,a.name FROM tag_alias a JOIN normalized_tag_map m ON m.old_id=a.tag_id
        WHERE m.old_id<>m.new_id ON CONFLICT DO NOTHING""")
    op.execute(
        "DELETE FROM tag_alias a USING normalized_tag_map m WHERE a.tag_id=m.old_id AND m.old_id<>m.new_id"
    )
    op.execute("DELETE FROM tag_relation")
    op.execute("INSERT INTO tag_relation SELECT * FROM normalized_relations")
    op.execute("""INSERT INTO tag_proposal_block(target_type,target_id,tag_id,created_at)
        SELECT b.target_type,b.target_id,m.new_id,MIN(b.created_at) FROM tag_proposal_block b JOIN normalized_tag_map m ON m.old_id=b.tag_id
        WHERE m.old_id<>m.new_id GROUP BY b.target_type,b.target_id,m.new_id ON CONFLICT DO NOTHING""")
    op.execute("""UPDATE tag_proposal p SET status='failed',reason='tag_merged',resolved_at=CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
        FROM normalized_tag_map m WHERE p.tag_id=m.old_id AND m.old_id<>m.new_id AND p.status='pending'""")
    op.execute("""UPDATE tag_proposal p SET status='failed',reason='tags_changed',resolved_at=CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
        WHERE p.status='pending' AND (EXISTS(SELECT 1 FROM tag_proposal_block b WHERE b.target_type=p.target_type AND b.target_id=p.target_id AND b.tag_id=p.tag_id)
        OR (p.target_type='thread' AND EXISTS(SELECT 1 FROM tag t WHERE t.id=p.tag_id AND t.source='discord')))""")
    op.execute("""UPDATE tag_notification_task n SET status='cancelled' FROM tag_proposal p
        WHERE n.proposal_id=p.id AND n.status='pending' AND p.status='failed' AND p.reason IN ('tag_merged','tags_changed')""")
    op.execute("""INSERT INTO operation_log(type,actor_id,target_type,target_id,tag_id,detail,created_at)
        SELECT 'tag.pool.merge',NULL,'tag',t.id,t.id,json_build_object('source_tag_id',t.id::text,'target_tag_id',m.new_id::text,
        'source_name',t.name,'target_id_kind','internal','reason','normalize_discord_tags_migration'),CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
        FROM tag t JOIN normalized_tag_map m ON t.id=m.old_id WHERE m.old_id<>m.new_id""")
    op.execute("""INSERT INTO operation_log(type,actor_id,target_type,target_id,tag_id,detail,created_at)
        SELECT 'tag.binding.merge',NULL,n.target_type,n.target_id,n.new_id,
        json_build_object('source_tag_id',n.tag_id::text,'target_tag_id',n.new_id::text,'old_binding_id',n.id::text,
        'new_binding_id',b.id::text,'target_id_kind','internal','reason','normalize_discord_tags_migration'),CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
        FROM normalized_bindings n JOIN tag_binding b ON b.target_type=n.target_type AND b.target_id=n.target_id AND b.tag_id=n.new_id AND b.ended_at IS NULL
        WHERE n.tag_id<>n.new_id OR n.priority<>1""")
    op.execute("""UPDATE tag t SET deleted_at=CURRENT_TIMESTAMP AT TIME ZONE 'UTC',enabled=FALSE
        FROM normalized_tag_map m WHERE t.id=m.old_id AND m.old_id<>m.new_id""")
    op.execute(
        "CREATE UNIQUE INDEX uq_discord_source_channel_concept ON discord_tag_source(channel_id,tag_id) WHERE deleted_at IS NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_live_discord_tag_name ON tag(name) WHERE source='discord' AND deleted_at IS NULL"
    )
    # 不从旧标签最大时间推断完整快照检查点，启动时重新完整抓取。
    op.execute(
        "ALTER TABLE tag DROP COLUMN discord_tag_id, DROP COLUMN discord_channel_id, DROP COLUMN discord_synced_at"
    )
    op.execute("""ALTER TABLE tag ADD CONSTRAINT ck_tag_source_category CHECK
        (source IN ('custom','discord') AND (category BETWEEN 1 AND 7 OR category IS NULL)
        AND (source<>'custom' OR category IS NOT NULL OR originated_from_discord))""")
    op.execute("ALTER TABLE tag_binding DROP CONSTRAINT ck_tag_binding")
    op.execute("""ALTER TABLE tag_binding ADD CONSTRAINT ck_tag_binding CHECK (
        target_type IN ('thread','booklist') AND binding_source IN ('discord_sync','local')
        AND (binding_source<>'discord_sync' OR (target_type='thread' AND discord_source_id IS NOT NULL))
        AND (binding_source<>'local' OR discord_source_id IS NULL) AND upvotes>=0 AND downvotes>=0)""")
    op.execute("""DO $$ BEGIN
        IF EXISTS(SELECT target_type,target_id,new_id FROM normalized_bindings EXCEPT SELECT target_type,target_id,tag_id FROM tag_binding WHERE ended_at IS NULL)
        OR EXISTS(SELECT target_type,target_id,tag_id FROM tag_binding WHERE ended_at IS NULL EXCEPT SELECT target_type,target_id,new_id FROM normalized_bindings)
        THEN RAISE EXCEPTION 'Canonical binding comparison failed'; END IF;
        END $$""")


def downgrade():
    """恢复需使用维护窗口完整备份，禁止自动丢弃归一后的业务数据。"""
    raise RuntimeError("请恢复停写维护窗口的完整数据库备份")
