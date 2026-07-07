"""通知模块"""

from __future__ import annotations

import logging
from typing import Any

from .base import NotificationBase, NotificationResult
from .dingtalk import DingTalkNotifier
from .email import EmailNotifier
from .feishu import FeishuNotifier
from .pushplus import PushPlusNotifier
from .serverchan import ServerChanNotifier
from .telegram import TelegramNotifier
from .wechat import WeChatNotifier


def create_notifier(
    notifier_type: str,
    logger: logging.Logger | None = None,
    **kwargs: Any,
) -> NotificationBase:
    """创建通知器工厂函数
    
    Args:
        notifier_type: 通知类型 (wechat, serverchan, pushplus, dingtalk, email, telegram, feishu)
        logger: 日志记录器
        **kwargs: 通知器配置
        
    Returns:
        通知器实例
    """
    notifier_type = notifier_type.lower()

    # 过滤掉空字符串值，避免其他参数类型的字段干扰
    kwargs = {k: v for k, v in kwargs.items() if v != '' and v is not None}

    # 每种通知器只传递其接受的参数，避免 TypeError
    if notifier_type == "wechat":
        return WeChatNotifier(
            webhook_url=kwargs.get("webhook_url", ""),
            logger=logger,
        )
    elif notifier_type == "serverchan":
        return ServerChanNotifier(
            serverchan_key=kwargs.get("serverchan_key", ""),
            logger=logger,
        )
    elif notifier_type == "pushplus":
        return PushPlusNotifier(
            pushplus_token=kwargs.get("pushplus_token", ""),
            logger=logger,
        )
    elif notifier_type == "dingtalk":
        return DingTalkNotifier(
            webhook_url=kwargs.get("webhook_url", ""),
            secret=kwargs.get("secret", ""),
            logger=logger,
        )
    elif notifier_type == "email":
        return EmailNotifier(
            smtp_server=kwargs.get("smtp_server", ""),
            smtp_port=int(kwargs.get("smtp_port", 465)),
            smtp_user=kwargs.get("smtp_user", ""),
            smtp_password=kwargs.get("smtp_password", ""),
            sender=kwargs.get("sender", ""),
            receivers=kwargs.get("receivers", []),
            use_ssl=bool(kwargs.get("use_ssl", True)),
            logger=logger,
        )
    elif notifier_type == "telegram":
        return TelegramNotifier(
            bot_token=kwargs.get("bot_token", ""),
            chat_id=kwargs.get("chat_id", ""),
            parse_mode=kwargs.get("parse_mode", "Markdown"),
            logger=logger,
        )
    elif notifier_type == "feishu":
        return FeishuNotifier(
            webhook_url=kwargs.get("webhook_url", ""),
            secret=kwargs.get("secret", ""),
            logger=logger,
        )
    else:
        raise ValueError(f"不支持的通知类型: {notifier_type}")


__all__ = [
    "DingTalkNotifier",
    "EmailNotifier",
    "FeishuNotifier",
    "NotificationBase",
    "NotificationResult",
    "PushPlusNotifier",
    "ServerChanNotifier",
    "TelegramNotifier",
    "WeChatNotifier",
    "create_notifier",
]
