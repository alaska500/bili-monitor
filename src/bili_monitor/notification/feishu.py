"""飞书通知器模块"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time
from typing import Any

from ..api.endpoints import DynamicInfo
from .base import NotificationBase, NotificationResult


class FeishuNotifier(NotificationBase):
    """飞书通知器"""

    def __init__(
        self,
        webhook_url: str,
        secret: str = "",
        logger: logging.Logger | None = None,
    ) -> None:
        super().__init__(logger)
        self._webhook_url = webhook_url
        self._secret = secret

    def _build_payload(self, content: dict[str, Any]) -> dict[str, Any]:
        """构建飞书请求体，如有 secret 则加入签名"""
        data: dict[str, Any] = {
            "msg_type": "interactive",
            "card": content,
        }
        if self._secret:
            timestamp = str(round(time.time()))
            string_to_sign = f"{timestamp}\n{self._secret}"
            hmac_code = hmac.new(
                self._secret.encode("utf-8"),
                string_to_sign.encode("utf-8"),
                digestmod=hashlib.sha256,
            ).digest()
            sign = base64.b64encode(hmac_code).decode("utf-8")
            data["timestamp"] = timestamp
            data["sign"] = sign
        return data

    def _format_post_content(self, dynamic: DynamicInfo) -> dict[str, Any]:
        """把动态整理成飞书互动卡片"""
        elements: list[dict[str, Any]] = []
        upstream_name = dynamic.upstream_name or "未知UP主"
        dynamic_type = dynamic.dynamic_type or "未知"
        dynamic_url = self._build_dynamic_url(dynamic)

        elements.append(self._text_block(f"👤 UP主：{upstream_name}"))
        elements.append(self._text_block(f"📝 类型：{dynamic_type}"))

        if dynamic.content:
            preview = self._truncate_text(dynamic.content, limit=500)
            elements.append(self._content_block(preview))

        if dynamic.video:
            elements.append(self._text_block(f"🎬 视频：{dynamic.video.title or '未命名'}"))
            if dynamic.video.bvid:
                elements.append(self._text_block(f"📎 BVID：{dynamic.video.bvid}"))

        if dynamic.images:
            elements.append(self._text_block(f"🖼️ 图片：{len(dynamic.images)} 张"))

        elements.append(self._stats_block(dynamic))
        elements.append(self._text_block(f"🕐 {self._format_time(dynamic.publish_time)}"))
        elements.append({"tag": "hr"})
        elements.append(self._action_block(dynamic_url))

        return {
            "config": {
                "wide_screen_mode": True,
                "enable_forward": True,
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"B站动态更新 · {upstream_name}",
                },
                "template": "blue",
            },
            "elements": elements,
        }

    def _format_test_post_content(self) -> dict[str, Any]:
        """构建测试消息内容"""
        return {
            "config": {
                "wide_screen_mode": True,
                "enable_forward": True,
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "飞书通知测试",
                },
                "template": "blue",
            },
            "elements": [
                self._text_block("B站动态监控飞书 Webhook 已连通。"),
                self._text_block("如果这条消息展示正常，说明格式和签名都可用。"),
            ],
        }

    def _text_block(self, text: str) -> dict[str, Any]:
        """生成普通文本块"""
        return {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": self._escape_markdown(text),
            },
        }

    def _content_block(self, text: str) -> dict[str, Any]:
        """生成内容段落块"""
        return {
            "tag": "div",
            "text": {
                "tag": "plain_text",
                "content": text,
            },
        }

    def _stats_block(self, dynamic: DynamicInfo) -> dict[str, Any]:
        """生成统计信息块"""
        return {
            "tag": "div",
            "fields": [
                {
                    "is_short": True,
                    "text": {
                        "tag": "lark_md",
                        "content": f"👍 {dynamic.stat.like:,}",
                    },
                },
                {
                    "is_short": True,
                    "text": {
                        "tag": "lark_md",
                        "content": f"💬 {dynamic.stat.comment:,}",
                    },
                },
                {
                    "is_short": True,
                    "text": {
                        "tag": "lark_md",
                        "content": f"🔄 {dynamic.stat.repost:,}",
                    },
                },
            ],
        }

    def _action_block(self, url: str) -> dict[str, Any]:
        """生成底部按钮块"""
        return {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": "查看动态",
                    },
                    "type": "default",
                    "url": url,
                }
            ],
        }

    def _format_time(self, publish_time) -> str:
        """格式化发布时间"""
        return publish_time.strftime("%Y-%m-%d %H:%M:%S") if publish_time else "未知"

    def _truncate_text(self, text: str, limit: int = 240) -> str:
        """截断长文本，保留阅读体验"""
        normalized = text.strip().replace("\r\n", "\n")
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3].rstrip() + "..."

    def _escape_markdown(self, text: str) -> str:
        """转义飞书 markdown 特殊字符"""
        escaped = text
        for char in ("\\", "`", "*", "_", "{", "}", "[", "]", "(", ")", "#", "+", "!", "|", ">"):
            escaped = escaped.replace(char, f"\\{char}")
        return escaped

    def _build_dynamic_url(self, dynamic: DynamicInfo) -> str:
        """构建动态跳转链接"""
        return f"https://t.bilibili.com/{dynamic.dynamic_id}" if dynamic.dynamic_id else "https://www.bilibili.com"

    def send(self, dynamic: DynamicInfo) -> NotificationResult:
        """发送通知"""
        content = self._format_post_content(dynamic)
        data = self._build_payload(content)
        return self._request(
            "POST", self._webhook_url, "code", 0, "飞书", "飞书", json_data=data
        )

    def test(self) -> NotificationResult:
        """测试通知器"""
        data = self._build_payload(self._format_test_post_content())
        return self._test_request_result(
            "POST", self._webhook_url, "code", 0, "飞书", payload=data
        )
