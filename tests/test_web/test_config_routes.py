from __future__ import annotations

from pathlib import Path

from bili_monitor.config.loader import load_config, save_config
from bili_monitor.config.models import AppConfig, MonitorConfig, NotificationConfig
from bili_monitor.web.app import create_app


def test_save_masked_config_keeps_existing_secrets(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    original_cookie = "SESSDATA=abcdefghijklmnopqrstuvwxyz1234567890; bili_jct=token-value"
    original_webhook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=abcdefghijklmnopqrstuvwxyz"
    original_bot_token = "123456789:abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"
    original_smtp_password = "mail-auth-code-secret"

    save_config(
        AppConfig(
            monitor=MonitorConfig(cookie=original_cookie),
            notification=[
                NotificationConfig(type="wechat", webhook_url=original_webhook),
                NotificationConfig(type="telegram", bot_token=original_bot_token, chat_id="-100123456"),
                NotificationConfig(
                    type="email",
                    smtp_server="smtp.qq.com",
                    smtp_user="user@example.com",
                    smtp_password=original_smtp_password,
                    sender="user@example.com",
                    receivers=["to@example.com"],
                ),
            ],
        ),
        config_path,
    )

    app = create_app(str(config_path))
    client = app.test_client()

    response = client.get("/api/config")
    assert response.status_code == 200
    full_config = response.get_json()
    assert full_config["monitor"]["cookie"] == original_cookie
    assert full_config["notification"][0]["webhook_url"] == original_webhook
    assert full_config["notification"][1]["bot_token"] == original_bot_token
    assert full_config["notification"][2]["smtp_password"] == original_smtp_password

    full_config["monitor"]["check_interval"] = 600
    response = client.post("/api/config", json=full_config)
    assert response.status_code == 200

    saved = load_config(config_path)
    assert saved.monitor.check_interval == 600
    assert saved.monitor.cookie == original_cookie
    assert saved.notification[0].webhook_url == original_webhook
    assert saved.notification[1].bot_token == original_bot_token
    assert saved.notification[1].chat_id == "-100123456"
    assert saved.notification[2].smtp_password == original_smtp_password
