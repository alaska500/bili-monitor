"""飞书通知器测试"""

from __future__ import annotations

from datetime import datetime

from bili_monitor.api.endpoints import DynamicInfo, ImageInfo, StatInfo, VideoInfo
from bili_monitor.notification import create_notifier
from bili_monitor.notification.feishu import FeishuNotifier


def _make_dynamic() -> DynamicInfo:
    return DynamicInfo(
        dynamic_id="123456789",
        uid="10001",
        upstream_name="测试UP主",
        dynamic_type="图文",
        content="第一行内容。\n第二行内容。\n第三行内容。\n" + ("长文本" * 80),
        publish_time=datetime(2026, 7, 1, 12, 30, 0),
        images=[ImageInfo(url="https://example.com/1.jpg")],
        video=VideoInfo(bvid="BV1xx411c7mD", title="测试视频标题"),
        stat=StatInfo(like=1234, repost=56, comment=78),
    )


def test_create_feishu_notifier() -> None:
    """确认工厂函数可以创建飞书通知器"""
    notifier = create_notifier("feishu", webhook_url="https://example.com")
    assert isinstance(notifier, FeishuNotifier)


def test_feishu_payload_uses_post_format() -> None:
    """确认飞书使用卡片格式"""
    notifier = FeishuNotifier(webhook_url="https://example.com")
    dynamic = _make_dynamic()

    content = notifier._format_post_content(dynamic)
    payload = notifier._build_payload(content)

    assert payload["msg_type"] == "interactive"
    assert payload["card"]["header"]["title"]["content"] == "B站动态更新 · 测试UP主"

    elements = payload["card"]["elements"]
    text_blocks = [item for item in elements if item.get("tag") == "div" and "text" in item]
    contents = [item["text"]["content"] for item in text_blocks]

    assert any(text.startswith("👤 UP主：测试UP主") for text in contents)
    assert any(text.startswith("📝 类型：图文") for text in contents)
    assert any(text == dynamic.content for text in contents)
    assert any(text.startswith("🎬 视频：测试视频标题") for text in contents)
    assert any(text.startswith("📎 BVID：BV1xx411c7mD") for text in contents)
    assert any(text.startswith("🕐 2026-07-01 12:30:00") for text in contents)

    stats_block = next(item for item in elements if item.get("tag") == "div" and "fields" in item)
    stats_texts = [field["text"]["content"] for field in stats_block["fields"]]
    assert "👍 1,234" in stats_texts
    assert "💬 78" in stats_texts
    assert "🔄 56" in stats_texts

    action_block = next(item for item in elements if item.get("tag") == "action")
    assert action_block["actions"][0]["text"]["content"] == "查看动态"
    assert action_block["actions"][0]["url"] == "https://t.bilibili.com/123456789"


def test_feishu_signature_is_attached() -> None:
    """确认启用加签时会附带签名字段"""
    notifier = FeishuNotifier(webhook_url="https://example.com", secret="secret-token")
    payload = notifier._build_payload(notifier._format_test_post_content())

    assert payload["msg_type"] == "interactive"
    assert payload["timestamp"] != ""
    assert payload["sign"] != ""
