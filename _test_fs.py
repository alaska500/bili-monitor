import sys
sys.path.insert(0, r'D:\Codex Desk\bili-monitor\src')
from bili_monitor.notification import create_notifier, FeishuNotifier
n = create_notifier('feishu', webhook_url='https://test.hk/xxx')
print('OK:', type(n).__name__)
