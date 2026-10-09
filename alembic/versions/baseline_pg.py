"""PG 基线迁移 —— 从生产 PostgreSQL 16 快照复现。

Revision ID: baseline_pg
Revises:
Create Date: 2026-06-08 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "baseline_pg"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 序列 ─────────────────────────────────────────
    op.execute(
        "CREATE SEQUENCE public.author_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1"
    )
    op.execute(
        "CREATE SEQUENCE public.banner_application_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1"
    )
    op.execute(
        "CREATE SEQUENCE public.banner_carousel_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1"
    )
    op.execute(
        "CREATE SEQUENCE public.banner_waitlist_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1"
    )
    op.execute(
        "CREATE SEQUENCE public.booklist_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1"
    )
    op.execute(
        "CREATE SEQUENCE public.booklist_item_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1"
    )
    op.execute(
        "CREATE SEQUENCE public.bot_config_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1"
    )
    op.execute(
        "CREATE SEQUENCE public.mutex_tag_group_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1"
    )
    op.execute(
        "CREATE SEQUENCE public.mutex_tag_rule_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1"
    )
    op.execute(
        "CREATE SEQUENCE public.tag_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1"
    )
    op.execute(
        "CREATE SEQUENCE public.tag_vote_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1"
    )
    op.execute(
        "CREATE SEQUENCE public.thread_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1"
    )
    op.execute(
        "CREATE SEQUENCE public.thread_follow_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1"
    )
    op.execute(
        "CREATE SEQUENCE public.user_collection_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1"
    )
    op.execute(
        "CREATE SEQUENCE public.usersearchpreferences_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1"
    )
    op.execute(
        "CREATE SEQUENCE public.user_update_preference_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1"
    )

    # ── 表 ───────────────────────────────────────────
    op.execute("""
        CREATE TABLE public.author (
            id bigint NOT NULL,
            name character varying NOT NULL,
            global_name character varying,
            display_name character varying NOT NULL,
            avatar_url character varying,
            last_updated timestamp without time zone NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE public.banner_application (
            id bigint NOT NULL,
            thread_id bigint NOT NULL,
            channel_id bigint NOT NULL,
            applicant_id bigint NOT NULL,
            cover_image_url character varying NOT NULL,
            target_scope character varying NOT NULL,
            status character varying NOT NULL,
            applied_at timestamp without time zone NOT NULL,
            reviewed_at timestamp without time zone,
            reviewer_id bigint,
            reject_reason character varying,
            review_message_id bigint,
            review_thread_id bigint
        )
    """)
    op.execute("""
        CREATE TABLE public.banner_carousel (
            id bigint NOT NULL,
            thread_id bigint NOT NULL,
            channel_id bigint,
            cover_image_url character varying NOT NULL,
            title character varying NOT NULL,
            start_time timestamp without time zone NOT NULL,
            end_time timestamp without time zone NOT NULL,
            "position" integer NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE public.banner_waitlist (
            id bigint NOT NULL,
            thread_id bigint NOT NULL,
            channel_id bigint,
            cover_image_url character varying NOT NULL,
            title character varying NOT NULL,
            queued_at timestamp without time zone NOT NULL,
            "position" integer NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE public.booklist (
            id bigint NOT NULL,
            owner_id bigint NOT NULL,
            title character varying NOT NULL,
            description character varying,
            cover_image_url character varying,
            is_public boolean NOT NULL,
            is_anonymous boolean NOT NULL,
            is_default boolean NOT NULL,
            is_tournament boolean NOT NULL,
            tournament_channel_id bigint,
            display_type integer NOT NULL,
            item_count integer NOT NULL,
            view_count integer NOT NULL,
            collection_count integer NOT NULL,
            display_thread_id bigint,
            display_channel_id bigint,
            display_guild_id bigint,
            created_at timestamp without time zone NOT NULL,
            updated_at timestamp without time zone NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE public.booklist_item (
            id bigint NOT NULL,
            owner_id bigint NOT NULL,
            booklist_id bigint NOT NULL,
            thread_id bigint NOT NULL,
            display_order integer NOT NULL,
            comment character varying,
            tournament_participated_at timestamp without time zone,
            display_message_id bigint,
            created_at timestamp without time zone NOT NULL,
            updated_at timestamp without time zone NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE public.bot_config (
            id bigint NOT NULL,
            type integer NOT NULL,
            type_str character varying NOT NULL,
            value_int bigint,
            value_float double precision,
            config_str character varying NOT NULL,
            tips character varying NOT NULL,
            update_time timestamp without time zone NOT NULL,
            update_user_id bigint
        )
    """)
    op.execute("""
        CREATE TABLE public.mutex_tag_group (
            id bigint NOT NULL,
            override_tag_name character varying
        )
    """)
    op.execute("""
        CREATE TABLE public.mutex_tag_rule (
            id bigint NOT NULL,
            group_id bigint NOT NULL,
            tag_name character varying NOT NULL,
            priority integer NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE public.tag (
            id bigint NOT NULL,
            name character varying NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE public.tag_vote (
            id bigint NOT NULL,
            user_id bigint NOT NULL,
            tag_id bigint NOT NULL,
            thread_id bigint NOT NULL,
            vote integer NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE public.thread (
            id bigint NOT NULL,
            guild_id bigint NOT NULL,
            channel_id bigint NOT NULL,
            thread_id bigint NOT NULL,
            title character varying NOT NULL,
            author_id bigint NOT NULL,
            created_at timestamp without time zone NOT NULL,
            last_active_at timestamp without time zone,
            reaction_count integer NOT NULL,
            reply_count integer NOT NULL,
            first_message_excerpt character varying,
            thumbnail_urls json,
            latest_update_at timestamp without time zone,
            latest_update_link character varying,
            collection_count integer NOT NULL,
            show_flag boolean NOT NULL,
            not_found_count integer NOT NULL,
            display_count bigint,
            search_vector tsvector
        )
    """)
    op.execute("""
        CREATE TABLE public.thread_follow (
            id bigint NOT NULL,
            user_id bigint NOT NULL,
            thread_id bigint NOT NULL,
            followed_at timestamp without time zone NOT NULL,
            last_viewed_at timestamp without time zone
        )
    """)
    op.execute("""
        CREATE TABLE public.thread_tag_link (
            thread_id bigint NOT NULL,
            tag_id bigint NOT NULL,
            upvotes integer NOT NULL,
            downvotes integer NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE public.user_collection (
            id bigint NOT NULL,
            user_id bigint,
            target_type integer NOT NULL,
            target_id bigint,
            created_at timestamp without time zone NOT NULL,
            note character varying
        )
    """)
    op.execute("""
        CREATE TABLE public.user_search_preferences (
            id bigint NOT NULL,
            user_id bigint NOT NULL,
            guild_id bigint NOT NULL,
            preferred_channels json,
            include_authors json,
            exclude_authors json,
            created_after character varying,
            created_before character varying,
            active_after character varying,
            active_before character varying,
            include_tags json,
            exclude_tags json,
            include_keywords character varying NOT NULL,
            exclude_keywords character varying NOT NULL,
            exclude_keyword_exemption_markers json,
            preview_image_mode character varying NOT NULL,
            results_per_page integer NOT NULL,
            ui_page_size integer NOT NULL,
            sort_method character varying NOT NULL,
            custom_base_sort character varying NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE public.user_update_preference (
            id bigint NOT NULL,
            user_id bigint NOT NULL,
            thread_id bigint NOT NULL,
            auto_sync boolean NOT NULL,
            no_remind boolean NOT NULL
        )
    """)

    # ── 主键 ─────────────────────────────────────────
    op.execute(
        "ALTER TABLE ONLY public.author ADD CONSTRAINT author_pkey PRIMARY KEY (id)"
    )
    op.execute(
        "ALTER TABLE ONLY public.banner_application ADD CONSTRAINT banner_application_pkey PRIMARY KEY (id)"
    )
    op.execute(
        "ALTER TABLE ONLY public.banner_carousel ADD CONSTRAINT banner_carousel_pkey PRIMARY KEY (id)"
    )
    op.execute(
        "ALTER TABLE ONLY public.banner_waitlist ADD CONSTRAINT banner_waitlist_pkey PRIMARY KEY (id)"
    )
    op.execute(
        "ALTER TABLE ONLY public.booklist ADD CONSTRAINT booklist_pkey PRIMARY KEY (id)"
    )
    op.execute(
        "ALTER TABLE ONLY public.booklist_item ADD CONSTRAINT booklist_item_pkey PRIMARY KEY (id)"
    )
    op.execute(
        "ALTER TABLE ONLY public.bot_config ADD CONSTRAINT bot_config_pkey PRIMARY KEY (id)"
    )
    op.execute(
        "ALTER TABLE ONLY public.mutex_tag_group ADD CONSTRAINT mutex_tag_group_pkey PRIMARY KEY (id)"
    )
    op.execute(
        "ALTER TABLE ONLY public.mutex_tag_rule ADD CONSTRAINT mutex_tag_rule_pkey PRIMARY KEY (id)"
    )
    op.execute("ALTER TABLE ONLY public.tag ADD CONSTRAINT tag_pkey PRIMARY KEY (id)")
    op.execute(
        "ALTER TABLE ONLY public.tag_vote ADD CONSTRAINT tag_vote_pkey PRIMARY KEY (id)"
    )
    op.execute(
        "ALTER TABLE ONLY public.thread ADD CONSTRAINT thread_pkey PRIMARY KEY (id)"
    )
    op.execute(
        "ALTER TABLE ONLY public.thread_follow ADD CONSTRAINT thread_follow_pkey PRIMARY KEY (id)"
    )
    op.execute(
        "ALTER TABLE ONLY public.thread_tag_link ADD CONSTRAINT threadtaglink_pkey PRIMARY KEY (thread_id, tag_id)"
    )
    op.execute(
        "ALTER TABLE ONLY public.user_collection ADD CONSTRAINT user_collection_pkey PRIMARY KEY (id)"
    )
    op.execute(
        "ALTER TABLE ONLY public.user_search_preferences ADD CONSTRAINT usersearchpreferences_pkey PRIMARY KEY (id)"
    )
    op.execute(
        "ALTER TABLE ONLY public.user_update_preference ADD CONSTRAINT user_update_preference_pkey PRIMARY KEY (id)"
    )

    # ── 唯一约束 ─────────────────────────────────────
    op.execute(
        "ALTER TABLE ONLY public.bot_config ADD CONSTRAINT bot_config_type_key UNIQUE (type)"
    )
    op.execute(
        "ALTER TABLE ONLY public.booklist_item ADD CONSTRAINT uq_booklist_thread UNIQUE (booklist_id, thread_id)"
    )
    op.execute(
        "ALTER TABLE ONLY public.tag_vote ADD CONSTRAINT uq_user_tag_thread_vote UNIQUE (user_id, tag_id, thread_id)"
    )
    op.execute(
        "ALTER TABLE ONLY public.user_collection ADD CONSTRAINT uk_user_collection_target UNIQUE (user_id, target_type, target_id)"
    )
    op.execute(
        "ALTER TABLE ONLY public.user_search_preferences ADD CONSTRAINT uk_user_guild_preferences UNIQUE (user_id, guild_id)"
    )
    op.execute(
        "ALTER TABLE ONLY public.user_update_preference ADD CONSTRAINT uk_user_thread_update_pref UNIQUE (user_id, thread_id)"
    )

    # ── 外键 ─────────────────────────────────────────
    op.execute(
        "ALTER TABLE ONLY public.mutex_tag_rule ADD CONSTRAINT mutex_tag_rule_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.mutex_tag_group(id)"
    )
    op.execute(
        "ALTER TABLE ONLY public.tag_vote ADD CONSTRAINT tag_vote_tag_id_fkey FOREIGN KEY (tag_id) REFERENCES public.tag(id)"
    )
    op.execute(
        "ALTER TABLE ONLY public.tag_vote ADD CONSTRAINT tag_vote_thread_id_fkey FOREIGN KEY (thread_id) REFERENCES public.thread(id)"
    )

    # ── 序列所有权 ───────────────────────────────────
    op.execute(
        "ALTER SEQUENCE public.banner_application_id_seq OWNED BY public.banner_application.id"
    )
    op.execute(
        "ALTER SEQUENCE public.banner_carousel_id_seq OWNED BY public.banner_carousel.id"
    )
    op.execute(
        "ALTER SEQUENCE public.banner_waitlist_id_seq OWNED BY public.banner_waitlist.id"
    )
    op.execute("ALTER SEQUENCE public.booklist_id_seq OWNED BY public.booklist.id")
    op.execute(
        "ALTER SEQUENCE public.booklist_item_id_seq OWNED BY public.booklist_item.id"
    )
    op.execute("ALTER SEQUENCE public.bot_config_id_seq OWNED BY public.bot_config.id")
    op.execute(
        "ALTER SEQUENCE public.mutex_tag_group_id_seq OWNED BY public.mutex_tag_group.id"
    )
    op.execute(
        "ALTER SEQUENCE public.mutex_tag_rule_id_seq OWNED BY public.mutex_tag_rule.id"
    )
    op.execute("ALTER SEQUENCE public.tag_id_seq OWNED BY public.tag.id")
    op.execute("ALTER SEQUENCE public.tag_vote_id_seq OWNED BY public.tag_vote.id")
    op.execute("ALTER SEQUENCE public.thread_id_seq OWNED BY public.thread.id")
    op.execute(
        "ALTER SEQUENCE public.thread_follow_id_seq OWNED BY public.thread_follow.id"
    )
    op.execute(
        "ALTER SEQUENCE public.user_collection_id_seq OWNED BY public.user_collection.id"
    )
    op.execute(
        "ALTER SEQUENCE public.usersearchpreferences_id_seq OWNED BY public.user_search_preferences.id"
    )
    op.execute(
        "ALTER SEQUENCE public.user_update_preference_id_seq OWNED BY public.user_update_preference.id"
    )

    # ── 默认值 ───────────────────────────────────────
    op.execute(
        "ALTER TABLE ONLY public.banner_application ALTER COLUMN id SET DEFAULT nextval('public.banner_application_id_seq'::regclass)"
    )
    op.execute(
        "ALTER TABLE ONLY public.banner_carousel ALTER COLUMN id SET DEFAULT nextval('public.banner_carousel_id_seq'::regclass)"
    )
    op.execute(
        "ALTER TABLE ONLY public.banner_waitlist ALTER COLUMN id SET DEFAULT nextval('public.banner_waitlist_id_seq'::regclass)"
    )
    op.execute(
        "ALTER TABLE ONLY public.booklist ALTER COLUMN id SET DEFAULT nextval('public.booklist_id_seq'::regclass)"
    )
    op.execute(
        "ALTER TABLE ONLY public.booklist_item ALTER COLUMN id SET DEFAULT nextval('public.booklist_item_id_seq'::regclass)"
    )
    op.execute(
        "ALTER TABLE ONLY public.bot_config ALTER COLUMN id SET DEFAULT nextval('public.bot_config_id_seq'::regclass)"
    )
    op.execute(
        "ALTER TABLE ONLY public.mutex_tag_group ALTER COLUMN id SET DEFAULT nextval('public.mutex_tag_group_id_seq'::regclass)"
    )
    op.execute(
        "ALTER TABLE ONLY public.mutex_tag_rule ALTER COLUMN id SET DEFAULT nextval('public.mutex_tag_rule_id_seq'::regclass)"
    )
    op.execute(
        "ALTER TABLE ONLY public.tag ALTER COLUMN id SET DEFAULT nextval('public.tag_id_seq'::regclass)"
    )
    op.execute(
        "ALTER TABLE ONLY public.tag_vote ALTER COLUMN id SET DEFAULT nextval('public.tag_vote_id_seq'::regclass)"
    )
    op.execute(
        "ALTER TABLE ONLY public.thread ALTER COLUMN id SET DEFAULT nextval('public.thread_id_seq'::regclass)"
    )
    op.execute(
        "ALTER TABLE ONLY public.thread_follow ALTER COLUMN id SET DEFAULT nextval('public.thread_follow_id_seq'::regclass)"
    )
    op.execute(
        "ALTER TABLE ONLY public.user_collection ALTER COLUMN id SET DEFAULT nextval('public.user_collection_id_seq'::regclass)"
    )
    op.execute(
        "ALTER TABLE ONLY public.user_search_preferences ALTER COLUMN id SET DEFAULT nextval('public.usersearchpreferences_id_seq'::regclass)"
    )
    op.execute(
        "ALTER TABLE ONLY public.user_update_preference ALTER COLUMN id SET DEFAULT nextval('public.user_update_preference_id_seq'::regclass)"
    )

    # ── 索引 ─────────────────────────────────────────
    op.execute(
        "CREATE INDEX ix_banner_application_applicant_id ON public.banner_application USING btree (applicant_id)"
    )
    op.execute(
        "CREATE INDEX ix_banner_application_channel_id ON public.banner_application USING btree (channel_id)"
    )
    op.execute(
        "CREATE INDEX ix_banner_application_status ON public.banner_application USING btree (status)"
    )
    op.execute(
        "CREATE INDEX ix_banner_application_target_scope ON public.banner_application USING btree (target_scope)"
    )
    op.execute(
        "CREATE INDEX ix_banner_application_thread_id ON public.banner_application USING btree (thread_id)"
    )
    op.execute(
        "CREATE INDEX ix_banner_carousel_channel_id ON public.banner_carousel USING btree (channel_id)"
    )
    op.execute(
        "CREATE INDEX ix_banner_carousel_end_time ON public.banner_carousel USING btree (end_time)"
    )
    op.execute(
        'CREATE INDEX ix_banner_carousel_position ON public.banner_carousel USING btree ("position")'
    )
    op.execute(
        "CREATE INDEX ix_banner_carousel_start_time ON public.banner_carousel USING btree (start_time)"
    )
    op.execute(
        "CREATE INDEX ix_banner_carousel_thread_id ON public.banner_carousel USING btree (thread_id)"
    )
    op.execute(
        "CREATE INDEX ix_banner_waitlist_channel_id ON public.banner_waitlist USING btree (channel_id)"
    )
    op.execute(
        'CREATE INDEX ix_banner_waitlist_position ON public.banner_waitlist USING btree ("position")'
    )
    op.execute(
        "CREATE INDEX ix_banner_waitlist_queued_at ON public.banner_waitlist USING btree (queued_at)"
    )
    op.execute(
        "CREATE INDEX ix_banner_waitlist_thread_id ON public.banner_waitlist USING btree (thread_id)"
    )
    op.execute(
        "CREATE INDEX ix_booklist_is_anonymous ON public.booklist USING btree (is_anonymous)"
    )
    op.execute(
        "CREATE INDEX ix_booklist_is_default ON public.booklist USING btree (is_default)"
    )
    op.execute(
        "CREATE INDEX ix_booklist_is_public ON public.booklist USING btree (is_public)"
    )
    op.execute(
        "CREATE INDEX ix_booklist_is_tournament ON public.booklist USING btree (is_tournament)"
    )
    op.execute(
        "CREATE INDEX ix_booklist_item_booklist_id ON public.booklist_item USING btree (booklist_id)"
    )
    op.execute(
        "CREATE INDEX ix_booklist_item_display_order ON public.booklist_item USING btree (display_order)"
    )
    op.execute(
        "CREATE INDEX ix_booklist_item_owner_id ON public.booklist_item USING btree (owner_id)"
    )
    op.execute(
        "CREATE INDEX ix_booklist_item_thread_id ON public.booklist_item USING btree (thread_id)"
    )
    op.execute(
        "CREATE INDEX ix_booklist_owner_id ON public.booklist USING btree (owner_id)"
    )
    op.execute("CREATE INDEX ix_booklist_title ON public.booklist USING btree (title)")
    op.execute(
        "CREATE UNIQUE INDEX ix_booklist_tournament_channel_id ON public.booklist USING btree (tournament_channel_id)"
    )
    op.execute(
        "CREATE INDEX ix_mutex_tag_group_override_tag_name ON public.mutex_tag_group USING btree (override_tag_name)"
    )
    op.execute(
        "CREATE INDEX ix_mutex_tag_rule_tag_name ON public.mutex_tag_rule USING btree (tag_name)"
    )
    op.execute("CREATE INDEX ix_tag_name ON public.tag USING btree (name)")
    op.execute(
        "CREATE INDEX ix_tag_vote_tag_id ON public.tag_vote USING btree (tag_id)"
    )
    op.execute(
        "CREATE INDEX ix_tag_vote_thread_id ON public.tag_vote USING btree (thread_id)"
    )
    op.execute(
        "CREATE INDEX ix_tag_vote_user_id ON public.tag_vote USING btree (user_id)"
    )
    op.execute(
        "CREATE INDEX ix_thread_author_id ON public.thread USING btree (author_id)"
    )
    op.execute(
        "CREATE INDEX ix_thread_channel_id ON public.thread USING btree (channel_id)"
    )
    op.execute(
        "CREATE INDEX ix_thread_created_at ON public.thread USING btree (created_at)"
    )
    op.execute(
        "CREATE INDEX ix_thread_display_count ON public.thread USING btree (display_count)"
    )
    op.execute(
        "CREATE INDEX ix_thread_follow_thread_id ON public.thread_follow USING btree (thread_id)"
    )
    op.execute(
        "CREATE INDEX ix_thread_follow_user_id ON public.thread_follow USING btree (user_id)"
    )
    op.execute(
        "CREATE INDEX ix_thread_guild_id ON public.thread USING btree (guild_id)"
    )
    op.execute(
        "CREATE INDEX ix_thread_last_active_at ON public.thread USING btree (last_active_at)"
    )
    op.execute(
        "CREATE INDEX ix_thread_latest_update_at ON public.thread USING btree (latest_update_at)"
    )
    op.execute(
        "CREATE INDEX ix_thread_not_found_count ON public.thread USING btree (not_found_count)"
    )
    op.execute(
        "CREATE INDEX ix_thread_reaction_count ON public.thread USING btree (reaction_count)"
    )
    op.execute(
        "CREATE INDEX ix_thread_reply_count ON public.thread USING btree (reply_count)"
    )
    op.execute(
        "CREATE INDEX ix_thread_search_vector ON public.thread USING gin (search_vector)"
    )
    op.execute(
        "CREATE INDEX ix_thread_show_flag ON public.thread USING btree (show_flag)"
    )
    op.execute(
        "CREATE UNIQUE INDEX ix_thread_thread_id ON public.thread USING btree (thread_id)"
    )
    op.execute(
        "CREATE INDEX ix_user_collection_target_id ON public.user_collection USING btree (target_id)"
    )
    op.execute(
        "CREATE INDEX ix_user_collection_target_type ON public.user_collection USING btree (target_type)"
    )
    op.execute(
        "CREATE INDEX ix_user_collection_user_id ON public.user_collection USING btree (user_id)"
    )
    op.execute(
        "CREATE INDEX ix_user_update_preference_thread_id ON public.user_update_preference USING btree (thread_id)"
    )
    op.execute(
        "CREATE INDEX ix_user_update_preference_user_id ON public.user_update_preference USING btree (user_id)"
    )
    op.execute(
        "CREATE INDEX ix_usersearchpreferences_guild_id ON public.user_search_preferences USING btree (guild_id)"
    )
    op.execute(
        "CREATE INDEX ix_usersearchpreferences_user_id ON public.user_search_preferences USING btree (user_id)"
    )


def downgrade() -> None:
    # 删除所有表和序列（逆序）
    op.execute("DROP TABLE IF EXISTS public.user_update_preference CASCADE")
    op.execute("DROP TABLE IF EXISTS public.user_search_preferences CASCADE")
    op.execute("DROP TABLE IF EXISTS public.user_collection CASCADE")
    op.execute("DROP TABLE IF EXISTS public.thread_tag_link CASCADE")
    op.execute("DROP TABLE IF EXISTS public.thread_follow CASCADE")
    op.execute("DROP TABLE IF EXISTS public.thread CASCADE")
    op.execute("DROP TABLE IF EXISTS public.tag_vote CASCADE")
    op.execute("DROP TABLE IF EXISTS public.tag CASCADE")
    op.execute("DROP TABLE IF EXISTS public.mutex_tag_rule CASCADE")
    op.execute("DROP TABLE IF EXISTS public.mutex_tag_group CASCADE")
    op.execute("DROP TABLE IF EXISTS public.bot_config CASCADE")
    op.execute("DROP TABLE IF EXISTS public.booklist_item CASCADE")
    op.execute("DROP TABLE IF EXISTS public.booklist CASCADE")
    op.execute("DROP TABLE IF EXISTS public.banner_waitlist CASCADE")
    op.execute("DROP TABLE IF EXISTS public.banner_carousel CASCADE")
    op.execute("DROP TABLE IF EXISTS public.banner_application CASCADE")
    op.execute("DROP TABLE IF EXISTS public.author CASCADE")
