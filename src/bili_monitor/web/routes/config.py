"""配置相关路由"""

from __future__ import annotations

import logging
from typing import Any

from flask import Blueprint, current_app, jsonify, request

from ...config.loader import load_config, save_config
from ...config.models import AppConfig, DatabaseConfig, LoggerConfig, MonitorConfig, NotificationConfig, UpstreamConfig

logger = logging.getLogger("bili-monitor.web")

config_bp = Blueprint("config", __name__)


def _is_masked(sent: str, original: str) -> bool:
    """检查 sent 是否为 original 的掩码版本（即用户未修改该字段）"""
    if not sent or not original:
        return False
    return sent == _mask_cookie(original)


def _resolve_secret(sent: Any, original: str, unchanged_marker: str | None = None) -> str:
    if sent is None:
        return original

    sent_text = str(sent)
    if unchanged_marker is not None and sent_text == unchanged_marker:
        return original
    if _is_masked(sent_text, original):
        return original
    return sent_text


def _mask_cookie(cookie: str) -> str:
    """掩码 Cookie"""
    if not cookie or len(cookie) < 20:
        return cookie[:5] + "..." if cookie else ""
    return cookie[:10] + "..." + cookie[-5:]


def _find_existing_notification(config: AppConfig, notif_type: str) -> NotificationConfig:
    return next((n for n in config.notification if n.type == notif_type), NotificationConfig(type=notif_type))


@config_bp.route("/api/config", methods=["GET"])
def get_config() -> Any:
    """获取配置"""
    try:
        config_path = current_app.config["CONFIG_PATH"]
        config = load_config(config_path)

        # 构建响应
        notification_list = []
        for n in config.notification:
            notification_list.append({
                "type": n.type,
                "webhook_url": n.webhook_url,
                "secret": n.secret,
                "serverchan_key": n.serverchan_key,
                "pushplus_token": n.pushplus_token,
                "smtp_server": n.smtp_server,
                "smtp_port": n.smtp_port,
                "smtp_user": n.smtp_user,
                "smtp_password": n.smtp_password,
                "sender": n.sender,
                "receivers": n.receivers,
                "bot_token": n.bot_token,
                "chat_id": n.chat_id,
            })

        upstreams = []
        for u in config.upstreams:
            upstreams.append({
                "uid": u.uid,
                "name": u.name,
                "face": u.face,
                "fans": u.fans,
            })

        return jsonify({
            "monitor": {
                "check_interval": config.monitor.check_interval,
                "retry_times": config.monitor.retry_times,
                "retry_delay": config.monitor.retry_delay,
                "cookie": config.monitor.cookie,
                "request_min": config.monitor.request_min,
                "request_max": config.monitor.request_max,
                "upstream_min": config.monitor.upstream_min,
                "upstream_max": config.monitor.upstream_max,
                "error_min": config.monitor.error_min,
                "error_max": config.monitor.error_max,
            },
            "upstreams": upstreams,
            "logger": {
                "level": config.logger.level,
                "file": config.logger.file,
                "max_bytes": config.logger.max_bytes,
                "backup_count": config.logger.backup_count,
            },
            "database": {
                "path": config.database.path,
            },
            "notification": notification_list,
        })
    except FileNotFoundError:
        return jsonify({"error": "配置文件不存在"}), 404
    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        return jsonify({"error": str(e)}), 500


@config_bp.route("/api/config", methods=["POST"])
def update_config() -> Any:
    """更新配置"""
    try:
        config_path = current_app.config["CONFIG_PATH"]
        raw_body = request.get_json()

        # 加载现有配置
        try:
            current_config = load_config(config_path)
        except Exception:
            current_config = AppConfig()

        # 更新监控配置
        monitor_data = raw_body.get("monitor", {})
        existing_cookie = current_config.monitor.cookie

        # 处理 Cookie
        new_cookie = _resolve_secret(monitor_data.get("cookie"), existing_cookie)

        # 更新 UP 主列表
        upstreams_data = raw_body.get("upstreams", [])

        # 更新日志配置
        logger_data = raw_body.get("logger", {})

        # 更新数据库配置
        database_data = raw_body.get("database", {})

        # 更新通知配置
        notification_data = raw_body.get("notification", [])
        notification_list = []
        for n in notification_data:
            notif_type = str(n.get("type", ""))
            existing_notif = _find_existing_notification(current_config, notif_type)

            receivers = n.get("receivers", existing_notif.receivers)
            if isinstance(receivers, list):
                resolved_receivers = [str(r) for r in receivers]
            else:
                resolved_receivers = []

            n_dict = {
                "type": notif_type,
                "webhook_url": _resolve_secret(n.get("webhook_url"), existing_notif.webhook_url),
                "secret": str(n.get("secret", existing_notif.secret)),
                "serverchan_key": _resolve_secret(n.get("serverchan_key"), existing_notif.serverchan_key),
                "pushplus_token": _resolve_secret(n.get("pushplus_token"), existing_notif.pushplus_token),
                "smtp_server": str(n.get("smtp_server", existing_notif.smtp_server)),
                "smtp_port": int(n.get("smtp_port", existing_notif.smtp_port)),
                "smtp_user": str(n.get("smtp_user", existing_notif.smtp_user)),
                "smtp_password": _resolve_secret(
                    n.get("smtp_password"),
                    existing_notif.smtp_password,
                    unchanged_marker="******",
                ),
                "sender": str(n.get("sender", existing_notif.sender)),
                "receivers": resolved_receivers,
                "bot_token": _resolve_secret(n.get("bot_token"), existing_notif.bot_token),
                "chat_id": str(n.get("chat_id", existing_notif.chat_id)),
            }
            notification_list.append(n_dict)

        # 构建 UP 主列表，并缓存远程头像
        from ...monitor.image import ImageDownloader
        avatar_downloader = ImageDownloader(base_dir="images", logger=logger)

        upstreams = []
        for u in upstreams_data:
            face = str(u.get("face") or "")
            uid = str(u.get("uid", ""))
            # 如果 face 是远程 URL，下载到本地缓存
            if face and face.startswith("http"):
                local_face = avatar_downloader.download_avatar(face, uid)
                if local_face:
                    face = local_face
            upstreams.append(UpstreamConfig(
                uid=uid,
                name=str(u.get("name", "")),
                face=face,
                fans=int(u.get("fans", 0)),
            ))

        new_config = AppConfig(
            monitor=MonitorConfig(
                check_interval=int(monitor_data.get("check_interval", 300)),
                retry_times=int(monitor_data.get("retry_times", 3)),
                retry_delay=int(monitor_data.get("retry_delay", 5)),
                cookie=new_cookie,
                request_min=float(monitor_data.get("request_min", 1.5)),
                request_max=float(monitor_data.get("request_max", 3.0)),
                upstream_min=float(monitor_data.get("upstream_min", 2.0)),
                upstream_max=float(monitor_data.get("upstream_max", 5.0)),
                error_min=float(monitor_data.get("error_min", 3.0)),
                error_max=float(monitor_data.get("error_max", 6.0)),
            ),
            upstreams=upstreams,
            logger=LoggerConfig(
                level=str(logger_data.get("level", "INFO")),
                file=str(logger_data.get("file", "logs/bili-monitor.log")),
                max_bytes=int(logger_data.get("max_bytes", 10 * 1024 * 1024)),
                backup_count=int(logger_data.get("backup_count", 5)),
            ),
            database=DatabaseConfig(
                path=str(database_data.get("path", "data/bili_monitor.db")),
            ),
            web=current_config.web,
            notification=[
                NotificationConfig(**n) for n in notification_list
            ],
        )

        # 保存配置
        save_config(new_config, config_path)
        current_app.config["APP_CONFIG"] = new_config

        # 热更新监控配置
        monitor = current_app.config.get("MONITOR_INSTANCE")
        if monitor and monitor._running:
            monitor._config = new_config
            # 同步更新抖动间隔
            m = new_config.monitor
            monitor.INTERVAL_CONFIG["upstream_check"] = (m.upstream_min, m.upstream_max)
            monitor.INTERVAL_CONFIG["error_retry"] = (m.error_min, m.error_max)
            # 同步更新 HTTP 客户端的 Cookie 和限流
            if monitor._client:
                if new_config.monitor.cookie:
                    monitor._client._session.headers["Cookie"] = new_config.monitor.cookie
                monitor._client.RATE_LIMIT_CONFIG["min_interval"] = m.request_min
                monitor._client.RATE_LIMIT_CONFIG["max_interval"] = m.request_max
            # 同步更新 Cookie 服务
            if monitor._cookie_service:
                monitor._cookie_service.update_cookie(new_config.monitor.cookie)
            logger.info("监控配置已热更新")

        return jsonify({"success": True, "message": "配置已保存"})

    except Exception as e:
        logger.error(f"保存配置失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
