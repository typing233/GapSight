import uuid
import asyncio
import httpx
from typing import List, Dict, Optional, Any, Callable
from datetime import datetime
from collections import defaultdict
import logging

from backend.models.schemas import (
    ThresholdConfig, NotificationConfig, Alert,
    NotificationChannel, DataSnapshot
)

logger = logging.getLogger(__name__)


class MonitoringService:
    def __init__(self):
        self.thresholds: Dict[str, ThresholdConfig] = {}
        self.notifications: Dict[str, NotificationConfig] = {}
        self.alerts: Dict[str, Alert] = {}
        self.alert_callbacks: List[Callable] = []

    def create_threshold(self, threshold: ThresholdConfig) -> ThresholdConfig:
        if threshold.id is None:
            threshold.id = str(uuid.uuid4())
        if threshold.created_at is None:
            threshold.created_at = datetime.now()
        self.thresholds[threshold.id] = threshold
        logger.info(f"创建阈值配置: {threshold.name} (ID: {threshold.id})")
        return threshold

    def get_threshold(self, threshold_id: str) -> Optional[ThresholdConfig]:
        return self.thresholds.get(threshold_id)

    def list_thresholds(self) -> List[ThresholdConfig]:
        return list(self.thresholds.values())

    def update_threshold(self, threshold_id: str, threshold: ThresholdConfig) -> Optional[ThresholdConfig]:
        if threshold_id in self.thresholds:
            threshold.id = threshold_id
            threshold.created_at = self.thresholds[threshold_id].created_at
            self.thresholds[threshold_id] = threshold
            logger.info(f"更新阈值配置: {threshold.name} (ID: {threshold_id})")
            return threshold
        return None

    def delete_threshold(self, threshold_id: str) -> bool:
        if threshold_id in self.thresholds:
            del self.thresholds[threshold_id]
            logger.info(f"删除阈值配置 (ID: {threshold_id})")
            return True
        return False

    def create_notification(self, notification: NotificationConfig) -> NotificationConfig:
        if notification.id is None:
            notification.id = str(uuid.uuid4())
        if notification.created_at is None:
            notification.created_at = datetime.now()
        self.notifications[notification.id] = notification
        logger.info(f"创建通知配置: {notification.name} (ID: {notification.id})")
        return notification

    def get_notification(self, notification_id: str) -> Optional[NotificationConfig]:
        return self.notifications.get(notification_id)

    def list_notifications(self) -> List[NotificationConfig]:
        return list(self.notifications.values())

    def update_notification(self, notification_id: str, notification: NotificationConfig) -> Optional[NotificationConfig]:
        if notification_id in self.notifications:
            notification.id = notification_id
            notification.created_at = self.notifications[notification_id].created_at
            self.notifications[notification_id] = notification
            logger.info(f"更新通知配置: {notification.name} (ID: {notification_id})")
            return notification
        return None

    def delete_notification(self, notification_id: str) -> bool:
        if notification_id in self.notifications:
            del self.notifications[notification_id]
            logger.info(f"删除通知配置 (ID: {notification_id})")
            return True
        return False

    def get_snapshot_metric(self, snapshot: DataSnapshot, dimension: str) -> float:
        metric_map = {
            'node_count': len(snapshot.nodes),
            'edge_count': len(snapshot.edges),
            'gap_count': len(snapshot.gap_pairs),
            'total_papers': snapshot.total_papers,
            'total_entities': snapshot.total_entities,
        }
        return float(metric_map.get(dimension, 0))

    def evaluate_threshold(self, threshold: ThresholdConfig, snapshot: DataSnapshot) -> Optional[Alert]:
        if not threshold.is_active:
            return None

        actual_value = self.get_snapshot_metric(snapshot, threshold.dimension)
        threshold_value = threshold.value

        is_violation = False
        if threshold.operator == '>':
            is_violation = actual_value > threshold_value
        elif threshold.operator == '>=':
            is_violation = actual_value >= threshold_value
        elif threshold.operator == '<':
            is_violation = actual_value < threshold_value
        elif threshold.operator == '<=':
            is_violation = actual_value <= threshold_value
        elif threshold.operator == '==':
            is_violation = actual_value == threshold_value
        elif threshold.operator == '!=':
            is_violation = actual_value != threshold_value

        if is_violation:
            deviation = abs(actual_value - threshold_value)
            if threshold_value > 0:
                deviation_percent = (deviation / threshold_value) * 100
            else:
                deviation_percent = 100 if actual_value != 0 else 0

            message = (
                f"阈值预警: '{threshold.name}' 触发\n"
                f"维度: {threshold.dimension}\n"
                f"快照: {snapshot.name}\n"
                f"阈值条件: {threshold.operator} {threshold_value}\n"
                f"实际值: {actual_value}\n"
                f"偏离度: {deviation_percent:.2f}%"
            )

            alert = Alert(
                id=str(uuid.uuid4()),
                threshold_id=threshold.id,
                threshold_name=threshold.name,
                snapshot_id=snapshot.id,
                snapshot_name=snapshot.name,
                triggered_at=datetime.now(),
                dimension=threshold.dimension,
                expected_value=threshold_value,
                actual_value=actual_value,
                deviation=deviation_percent,
                message=message,
                is_read=False,
                channels=[]
            )

            return alert

        return None

    def check_snapshot(self, snapshot: DataSnapshot) -> List[Alert]:
        triggered_alerts = []

        for threshold_id, threshold in self.thresholds.items():
            if threshold.is_active:
                alert = self.evaluate_threshold(threshold, snapshot)
                if alert:
                    self.alerts[alert.id] = alert
                    triggered_alerts.append(alert)
                    logger.warning(f"触发预警: {alert.message}")

                    for callback in self.alert_callbacks:
                        try:
                            callback(alert)
                        except Exception as e:
                            logger.error(f"预警回调执行失败: {str(e)}")

        return triggered_alerts

    def get_alerts(self, include_read: bool = False, limit: int = 100) -> List[Alert]:
        alerts = list(self.alerts.values())
        if not include_read:
            alerts = [a for a in alerts if not a.is_read]
        alerts.sort(key=lambda x: x.triggered_at, reverse=True)
        return alerts[:limit]

    def mark_alert_read(self, alert_id: str) -> bool:
        if alert_id in self.alerts:
            self.alerts[alert_id].is_read = True
            return True
        return False

    def mark_all_alerts_read(self) -> int:
        count = 0
        for alert_id in self.alerts:
            if not self.alerts[alert_id].is_read:
                self.alerts[alert_id].is_read = True
                count += 1
        return count

    async def send_webhook_notification(self, webhook_url: str, alert: Alert) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    'alert_id': alert.id,
                    'threshold_name': alert.threshold_name,
                    'snapshot_name': alert.snapshot_name,
                    'triggered_at': alert.triggered_at.isoformat(),
                    'dimension': alert.dimension,
                    'expected_value': alert.expected_value,
                    'actual_value': alert.actual_value,
                    'deviation': alert.deviation,
                    'message': alert.message
                }
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=10.0
                )
                if response.status_code in [200, 201, 202, 204]:
                    logger.info(f"Webhook 通知发送成功: {webhook_url}")
                    return True
                else:
                    logger.warning(f"Webhook 通知返回非预期状态码: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Webhook 通知发送失败: {str(e)}")
            return False

    async def send_notifications(self, alert: Alert, notification_configs: List[NotificationConfig] = None) -> Dict[str, bool]:
        results = {}

        if notification_configs is None:
            notification_configs = [n for n in self.notifications.values() if n.is_active]

        for config in notification_configs:
            if not config.is_active:
                continue

            for channel in config.channels:
                if channel == NotificationChannel.SYSTEM_POPUP:
                    results[f"popup_{config.id}"] = True
                    logger.info(f"系统弹窗通知已标记: {alert.message[:50]}...")

                elif channel == NotificationChannel.WEBHOOK and config.webhook_url:
                    success = await self.send_webhook_notification(config.webhook_url, alert)
                    results[f"webhook_{config.id}"] = success

                elif channel == NotificationChannel.EMAIL:
                    logger.warning(f"邮件通知功能尚未实现 (收件人: {config.email_recipients})")
                    results[f"email_{config.id}"] = False

        return results

    def get_monitoring_summary(self) -> Dict[str, Any]:
        active_thresholds = [t for t in self.thresholds.values() if t.is_active]
        active_notifications = [n for n in self.notifications.values() if n.is_active]
        unread_alerts = [a for a in self.alerts.values() if not a.is_read]
        recent_alerts = self.get_alerts(include_read=True, limit=10)

        return {
            'total_thresholds': len(self.thresholds),
            'active_thresholds': len(active_thresholds),
            'total_notifications': len(self.notifications),
            'active_notifications': len(active_notifications),
            'total_alerts': len(self.alerts),
            'unread_alerts': len(unread_alerts),
            'recent_alerts': [
                {
                    'id': a.id,
                    'threshold_name': a.threshold_name,
                    'snapshot_name': a.snapshot_name,
                    'triggered_at': a.triggered_at.isoformat(),
                    'message': a.message,
                    'is_read': a.is_read
                }
                for a in recent_alerts
            ],
            'threshold_summary': {
                'dimensions': self._get_threshold_dimension_summary(),
                'operators': self._get_threshold_operator_summary()
            }
        }

    def _get_threshold_dimension_summary(self) -> Dict[str, int]:
        summary = defaultdict(int)
        for threshold in self.thresholds.values():
            if threshold.is_active:
                summary[threshold.dimension] += 1
        return dict(summary)

    def _get_threshold_operator_summary(self) -> Dict[str, int]:
        summary = defaultdict(int)
        for threshold in self.thresholds.values():
            if threshold.is_active:
                summary[threshold.operator] += 1
        return dict(summary)

    def register_alert_callback(self, callback: Callable):
        self.alert_callbacks.append(callback)

    def unregister_alert_callback(self, callback: Callable):
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)


monitoring_service = MonitoringService()
