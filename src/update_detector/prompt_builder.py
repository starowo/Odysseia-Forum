from typing import Optional

SYSTEM_PROMPT = """\
你是一个Discord论坛帖子更新检测助手。你的任务是判断一条消息是否为帖子作者发布的"作品版本更新/发布更新"。

帖子标题和首楼内容仅用于帮助你理解作品背景。你必须只判断待检测消息是否为一次作品版本更新/发布更新，不得因为标题或首楼内容中出现了更新、版本、发布等词语就回答 "YES"。

判断标准：
- 消息内容明确提及了新版本、更新、修复、改进、发布等关键词
- 消息包含版本号（如 v1.2、1.0.0 等）
- 消息描述了changelog、更新日志、新增功能、修复内容等
- 消息附带了更新相关的文件（如 .json 配置文件）

不算更新的情况：
- 普通的聊天讨论或回复
- 提问或求助
- 纯粹的感想或评论
- 虽然文字量大但并非版本发布相关

请只回答 "YES" 或 "NO"，不要解释。
"""


def build_update_detection_prompt(
    *,
    thread_title: str,
    first_message_content: str,
    message_content: str,
    attachment_filenames: Optional[list[str]] = None,
) -> tuple[str, str]:
    """构造更新检测共用的系统提示词和用户提示词。"""
    user_content = (
        f"帖子标题：\n{thread_title}"
        f"\n\n帖子首楼内容：\n{first_message_content}"
        f"\n\n待检测消息：\n{message_content}"
    )
    if attachment_filenames:
        user_content += f"\n\n附件文件名：{', '.join(attachment_filenames)}"
    return SYSTEM_PROMPT, user_content
