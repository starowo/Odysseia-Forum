import glob
import os
import subprocess
import asyncio
import logging
import traceback
import base64
from datetime import datetime, timezone

from discord.ext import commands, tasks
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import aioboto3

logger = logging.getLogger(__name__)

TEMP_BACKUP_PATTERN = "data/backup_temp_*.dump"
TEMP_ENC_PATTERN = "data/backup_temp_*.enc"

# 需要加密备份的配置文件（相对于工作目录的路径）
CONFIG_FILES_TO_BACKUP: list[tuple[str, str]] = [
    ("config.json", "config"),
    (".env", "env"),
]


class BackupCog(commands.Cog):
    """定时将 PostgreSQL 数据库快照及配置文件加密后上传至 S3 兼容对象存储（如 Cloudflare R2）"""

    def __init__(self, bot: commands.Bot, config: dict):
        self.bot = bot
        self.backup_config = config.get("backup", {})

        self._cleanup_stale_temp_files()

        if self.backup_config.get("enabled", False):
            self.backup_task.start()
        else:
            logger.warning("数据库备份功能未启用。")

    @staticmethod
    def _cleanup_stale_temp_files() -> None:
        """清理因非正常退出而残留的临时文件"""
        for pattern in (TEMP_BACKUP_PATTERN, TEMP_ENC_PATTERN):
            for stale in glob.glob(pattern):
                try:
                    os.remove(stale)
                    logger.info(f"已清理残留临时文件: {stale}")
                except OSError:
                    pass

    def cog_unload(self) -> None:
        if self.backup_task.is_running():
            self.backup_task.cancel()

    # ── 加密相关 ─────────────────────────────────────────────

    @staticmethod
    def _get_encryption_key() -> bytes | None:
        """从环境变量读取 AES-256 加密密钥；未设置则返回 None"""
        key_b64 = os.environ.get("BACKUP_ENCRYPTION_KEY", "")
        if not key_b64:
            return None
        try:
            key = base64.b64decode(key_b64)
            if len(key) != 32:
                logger.error(
                    "BACKUP_ENCRYPTION_KEY 解码后长度不为 32 字节，将跳过配置文件加密备份"
                )
                return None
            return key
        except Exception as e:
            logger.error(f"BACKUP_ENCRYPTION_KEY 解码失败: {e}，将跳过配置文件加密备份")
            return None

    @staticmethod
    def _encrypt_file_sync(source_path: str, dest_path: str, key: bytes) -> bool:
        """AES-256-GCM 加密单个文件，nonce（12 字节）前置写入密文文件。

        返回 True 表示成功，False 表示跳过（文件不存在）或失败。
        """
        if not os.path.exists(source_path):
            logger.debug(f"配置文件不存在，跳过加密: {source_path}")
            return False

        try:
            with open(source_path, "rb") as f:
                plaintext = f.read()

            nonce = os.urandom(12)
            aesgcm = AESGCM(key)
            ciphertext = aesgcm.encrypt(nonce, plaintext, None)

            with open(dest_path, "wb") as f:
                f.write(nonce + ciphertext)

            logger.debug(f"配置文件已加密: {source_path} → {dest_path}")
            return True
        except Exception as e:
            logger.error(f"加密配置文件失败 {source_path}: {e}")
            return False

    def _encrypt_config_files_sync(self, key: bytes, timestamp: str) -> list[str]:
        """加密所有配置文件，返回成功生成的 .enc 文件路径列表"""
        enc_paths: list[str] = []
        for source_rel, label in CONFIG_FILES_TO_BACKUP:
            dest_path = f"data/backup_temp_{label}_{timestamp}.enc"
            if self._encrypt_file_sync(source_rel, dest_path, key):
                enc_paths.append(dest_path)
        return enc_paths

    # ── 数据库备份 ───────────────────────────────────────────

    def _create_compressed_backup_sync(self) -> str:
        """在子线程中执行：使用 pg_dump 生成数据库快照并 zstd 压缩"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        dump_path = f"data/backup_temp_{timestamp}.dump"

        try:
            # 从环境变量获取数据库连接信息
            db_url = os.environ.get(
                "DATABASE_URL",
                "postgresql://odysseia:changeme@localhost:5432/odysseia",
            )
            # 将 asyncpg URL 转为标准 pg URL（pg_dump 不需要 async 驱动前缀）
            pg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

            subprocess.run(
                [
                    "pg_dump",
                    "--dbname",
                    pg_url,
                    "--format",
                    "custom",
                    "--compress",
                    "zstd:6",
                    "--file",
                    dump_path,
                    "--no-owner",
                    "--no-acl",
                ],
                check=True,
                capture_output=True,
            )

            return dump_path
        except subprocess.CalledProcessError as e:
            logger.error(f"pg_dump 失败: {e.stderr.decode() if e.stderr else str(e)}")
            raise

    # ── S3 上传 ──────────────────────────────────────────────

    def _build_s3_client_kwargs(self) -> dict:
        """构建 aioboto3 S3 客户端参数"""
        client_kwargs = {
            "service_name": "s3",
            "endpoint_url": self.backup_config["endpoint_url"],
            "aws_access_key_id": self.backup_config["access_key"],
            "aws_secret_access_key": self.backup_config["secret_key"],
        }
        if self.backup_config.get("region_name"):
            client_kwargs["region_name"] = self.backup_config["region_name"]
        return client_kwargs

    async def _upload_to_s3(self, file_path: str, s3_key: str | None = None) -> None:
        """将文件上传至 S3 兼容对象存储"""
        session = aioboto3.Session()
        client_kwargs = self._build_s3_client_kwargs()

        file_name = os.path.basename(file_path)
        bucket = self.backup_config["bucket_name"]
        if s3_key is None:
            s3_key = f"odysseia_backups/{file_name}"

        async with session.client(**client_kwargs) as client:  # type: ignore[reportUnknownMemberType,reportGeneralTypeIssues]
            logger.info(f"正在上传 {file_name} 到存储桶 {bucket} ...")

            await client.upload_file(
                Filename=file_path,
                Bucket=bucket,
                Key=s3_key,
            )

            logger.info(f"上传成功: {file_name}")

    # ── 定时任务 ─────────────────────────────────────────────

    @tasks.loop(hours=3.0)
    async def backup_task(self) -> None:
        """每 3 小时执行一次：数据库快照 + 配置文件加密 → 上传 → 清理本地临时文件"""
        logger.info("开始执行定期备份任务...")
        dump_path = None
        enc_paths: list[str] = []
        try:
            # 数据库快照和压缩是 CPU/IO 密集型操作，放入子线程避免阻塞事件循环
            dump_path = await asyncio.to_thread(self._create_compressed_backup_sync)

            # 从 dump 文件名提取时间戳，用于配置文件加密备份命名
            basename = os.path.basename(dump_path)  # backup_temp_YYYYMMDD_HHMMSS.dump
            timestamp = basename[len("backup_temp_") : -len(".dump")]

            # 加密配置文件（若密钥已配置）
            key = self._get_encryption_key()
            if key:
                enc_paths = await asyncio.to_thread(
                    self._encrypt_config_files_sync, key, timestamp
                )
            else:
                logger.debug("未设置 BACKUP_ENCRYPTION_KEY，跳过配置文件加密备份")

            # 上传数据库 dump
            await self._upload_to_s3(dump_path)

            # 上传加密的配置文件（S3 key 去掉 backup_temp_ 前缀，保持路径整洁）
            for enc_path in enc_paths:
                try:
                    enc_basename = os.path.basename(enc_path)
                    # backup_temp_config_YYYYMMDD_HHMMSS.enc → config_YYYYMMDD_HHMMSS.enc
                    clean_name = enc_basename[len("backup_temp_") :]
                    s3_key = f"odysseia_backups/{clean_name}"
                    await self._upload_to_s3(enc_path, s3_key=s3_key)
                except Exception as e:
                    logger.error(f"上传加密配置文件失败 {enc_path}: {e}")

        except Exception as e:
            logger.error(f"数据库备份失败: {e}\n{traceback.format_exc()}")
        finally:
            # 无论上传成功与否，都清理本地临时文件，避免占用 VPS 磁盘
            if dump_path and os.path.exists(dump_path):
                os.remove(dump_path)
            for enc_path in enc_paths:
                if os.path.exists(enc_path):
                    os.remove(enc_path)

    @backup_task.before_loop
    async def before_backup_task(self) -> None:
        """等待机器人就绪后再开始首次备份"""
        await self.bot.wait_until_ready()
