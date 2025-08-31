"""
統合ログ・モニタリングシステム (CLAUDE.md準拠)
構造化ログ・エラー追跡・パフォーマンス監視の統合管理
"""

import atexit
import signal
import sys
import threading
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
from datetime import datetime

from src.utils.structured_logger import get_logger, setup_logging
from src.utils.error_tracker import get_error_tracker, setup_error_alerts, track_error
from src.utils.performance_monitor import get_performance_monitor, setup_performance_alerts, measure_operation, measure_function


class MonitoringIntegration:
    """
    統合監視システム
    
    全ての監視コンポーネントを統合管理
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        統合監視システムを初期化
        
        Args:
            config: 監視設定
        """
        self.config = config or self._get_default_config()
        self.logger = get_logger(__name__)
        
        # 各コンポーネントの初期化
        self._initialize_components()
        
        # シグナルハンドラーの設定
        self._setup_signal_handlers()
        
        # 終了時処理の設定
        atexit.register(self.shutdown)
        
        self.logger.info("統合監視システム初期化完了", extra={
            "config": self.config,
            "components": ["structured_logging", "error_tracking", "performance_monitoring"]
        })
    
    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定を取得"""
        return {
            "logging": {
                "level": "INFO",
                "log_directory": "./logs",
                "max_file_size_mb": 100,
                "backup_count": 5
            },
            "error_tracking": {
                "storage_path": "./logs/error_tracking",
                "max_errors_in_memory": 1000,
                "alert_threshold": 5,
                "cleanup_days": 30
            },
            "performance_monitoring": {
                "storage_path": "./logs/performance",
                "collection_interval": 5.0,
                "retention_hours": 24,
                "alert_thresholds": {
                    "cpu_percent": 80.0,
                    "memory_percent": 85.0,
                    "disk_usage_percent": 90.0,
                    "response_time_ms": 1000.0,
                    "error_rate_percent": 5.0
                }
            },
            "alerts": {
                "enabled": True,
                "email_notifications": False,
                "slack_notifications": False
            }
        }
    
    def _initialize_components(self):
        """各コンポーネントを初期化"""
        # 構造化ログ設定
        setup_logging()
        
        # エラー追跡設定
        setup_error_alerts()
        
        # パフォーマンス監視設定
        setup_performance_alerts()
        
        # パフォーマンス監視開始
        performance_monitor = get_performance_monitor()
        performance_monitor.start_monitoring()
        
        # 統合アラート設定
        self._setup_integrated_alerts()
    
    def _setup_signal_handlers(self):
        """シグナルハンドラーを設定"""
        if threading.current_thread() is threading.main_thread():
            def signal_handler(signum, frame):
                self.logger.info(f"シグナル受信: {signum}")
                self.shutdown()
                sys.exit(0)
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        else:
            self.logger.warning("シグナルハンドラーはメインスレッドでのみ設定可能です。")
    
    def _setup_integrated_alerts(self):
        """統合アラートを設定"""
        if not self.config["alerts"]["enabled"]:
            return
        
        def integrated_alert_handler(category: str, alert_data: Dict[str, Any]):
            """統合アラートハンドラー"""
            alert_info = {
                "category": category,
                "alert_type": alert_data.get("type", "unknown"),
                "timestamp": datetime.now().isoformat(),
                "severity": self._determine_severity(alert_data),
                "data": alert_data
            }
            
            # 重要度に応じて処理
            if alert_info["severity"] in ["high", "critical"]:
                self._handle_critical_alert(alert_info)
            else:
                self._handle_standard_alert(alert_info)
        
        # エラートラッカーにコールバック追加
        error_tracker = get_error_tracker()
        error_tracker.add_alert_callback(
            lambda error_info: integrated_alert_handler("error", {
                "type": "repeated_error",
                "error_id": error_info.error_id,
                "error_type": error_info.error_type,
                "occurrence_count": error_info.occurrence_count,
                "user_impact": error_info.user_impact
            })
        )
        
        # パフォーマンスモニターにコールバック追加
        performance_monitor = get_performance_monitor()
        performance_monitor.add_alert_callback(integrated_alert_handler)
    
    def _determine_severity(self, alert_data: Dict[str, Any]) -> str:
        """アラートの重要度を判定"""
        alert_type = alert_data.get("type", "")
        
        # クリティカルな条件
        if alert_type in ["high_memory", "low_disk_space"] and alert_data.get("value", 0) > 95:
            return "critical"
        
        if alert_type == "repeated_error" and alert_data.get("user_impact") == "critical":
            return "critical"
        
        # 高重要度の条件
        if alert_type in ["high_cpu", "high_memory", "low_disk_space"]:
            return "high"
        
        if alert_type == "repeated_error" and alert_data.get("occurrence_count", 0) > 10:
            return "high"
        
        if alert_type == "slow_operation" and alert_data.get("duration_ms", 0) > 5000:
            return "high"
        
        return "medium"
    
    def _handle_critical_alert(self, alert_info: Dict[str, Any]):
        """クリティカルアラートの処理"""
        self.logger.critical(
            f"🚨 CRITICAL ALERT: {alert_info['alert_type']}",
            extra=alert_info
        )
        
        # クリティカルアラートファイルに記録
        self._save_critical_alert(alert_info)
        
        # 外部通知（設定されている場合）
        if self.config["alerts"].get("email_notifications"):
            self._send_email_notification(alert_info)
        
        if self.config["alerts"].get("slack_notifications"):
            self._send_slack_notification(alert_info)
    
    def _handle_standard_alert(self, alert_info: Dict[str, Any]):
        """標準アラートの処理"""
        self.logger.warning(
            f"⚠️ Alert: {alert_info['alert_type']}",
            extra=alert_info
        )
    
    def _save_critical_alert(self, alert_info: Dict[str, Any]):
        """クリティカルアラートをファイルに保存"""
        try:
            alerts_dir = Path("./logs/critical_alerts")
            alerts_dir.mkdir(parents=True, exist_ok=True)
            
            alert_file = alerts_dir / f"critical_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(alert_file, 'w', encoding='utf-8') as f:
                json.dump(alert_info, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            self.logger.error(f"クリティカルアラート保存失敗: {e}")
    
    def _send_email_notification(self, alert_info: Dict[str, Any]):
        """メール通知送信（実装例）"""
        # 実際の実装では適切なメール送信ライブラリを使用
        self.logger.info("メール通知送信（未実装）", extra={"alert_info": alert_info})
    
    def _send_slack_notification(self, alert_info: Dict[str, Any]):
        """Slack通知送信（実装例）"""
        # 実際の実装では適切なSlack APIを使用
        self.logger.info("Slack通知送信（未実装）", extra={"alert_info": alert_info})
    
    def get_system_health_report(self) -> Dict[str, Any]:
        """システム健康状態レポートを生成"""
        error_tracker = get_error_tracker()
        performance_monitor = get_performance_monitor()
        
        # エラー情報取得
        error_metrics = error_tracker.get_error_metrics()
        error_report = error_tracker.get_error_report(days=1)
        
        # パフォーマンス情報取得
        performance_report = performance_monitor.get_performance_report(hours=1)
        system_metrics = performance_monitor.get_system_metrics()
        
        # 全体的な健康度を計算
        health_score = self._calculate_health_score(error_metrics, system_metrics)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "health_score": health_score,
            "status": self._get_status_from_score(health_score),
            "summary": {
                "total_errors": error_metrics.total_errors,
                "unique_errors": error_metrics.unique_errors,
                "critical_errors": error_metrics.critical_errors,
                "error_rate": error_metrics.error_rate,
                "uptime_percentage": error_metrics.uptime_percentage,
                "cpu_usage": system_metrics.cpu_percent,
                "memory_usage": system_metrics.memory_percent,
                "disk_usage": system_metrics.disk_usage_percent
            },
            "error_details": {
                "most_frequent_errors": error_metrics.most_frequent_errors[:3],
                "unresolved_errors": len(error_report.get("unresolved_errors", []))
            },
            "performance_details": {
                "performance_issues": len(performance_report.get("performance_issues", [])),
                "slow_operations": [
                    op for op in performance_report.get("operation_statistics", {}).items()
                    if op[1]["avg_time_ms"] > 1000
                ][:3]
            },
            "recommendations": self._generate_health_recommendations(error_metrics, performance_report)
        }
    
    def _calculate_health_score(self, error_metrics: Any, system_metrics: Any) -> float:
        """健康度スコア計算（0-100）"""
        score = 100.0
        
        # エラー率による減点
        score -= min(error_metrics.error_rate * 2, 20)
        
        # クリティカルエラーによる減点
        score -= min(error_metrics.critical_errors * 5, 25)
        
        # システムリソースによる減点
        score -= min(max(0, system_metrics.cpu_percent - 70) * 0.5, 15)
        score -= min(max(0, system_metrics.memory_percent - 80) * 0.5, 15)
        score -= min(max(0, system_metrics.disk_usage_percent - 85) * 0.3, 15)
        
        return max(0.0, score)
    
    def _get_status_from_score(self, score: float) -> str:
        """スコアから状態を判定"""
        if score >= 90:
            return "excellent"
        elif score >= 80:
            return "good"
        elif score >= 70:
            return "fair"
        elif score >= 60:
            return "poor"
        else:
            return "critical"
    
    def _generate_health_recommendations(self, error_metrics: Any, performance_report: Dict[str, Any]) -> List[str]:
        """健康状態改善推奨事項を生成"""
        recommendations = []
        
        if error_metrics.error_rate > 5:
            recommendations.append("エラー率が高いため、根本原因の調査と修正を推奨します")
        
        if error_metrics.critical_errors > 0:
            recommendations.append("クリティカルエラーがあるため、緊急対応が必要です")
        
        performance_issues = performance_report.get("performance_issues", [])
        if performance_issues:
            high_severity_issues = [i for i in performance_issues if i.get("severity") == "high"]
            if high_severity_issues:
                recommendations.append("高重要度のパフォーマンス問題があるため、最適化を検討してください")
        
        if not recommendations:
            recommendations.append("システムは良好な状態です。定期的な監視を継続してください")
        
        return recommendations
    
    def shutdown(self):
        """監視システムを正常終了"""
        self.logger.info("統合監視システム終了処理開始")
        
        try:
            # パフォーマンス監視停止
            performance_monitor = get_performance_monitor()
            performance_monitor.stop_monitoring()
            
            # 最終レポート生成
            final_report = self.get_system_health_report()
            self.logger.info("最終システム健康状態レポート", extra=final_report)
            
            # データ保存
            self._save_final_data()
            
        except Exception as e:
            self.logger.error(f"終了処理エラー: {e}")
        
        self.logger.info("統合監視システム終了処理完了")
    
    def _save_final_data(self):
        """最終データの保存"""
        try:
            final_data_dir = Path("./logs/final_reports")
            final_data_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 最終健康状態レポート
            health_report = self.get_system_health_report()
            with open(final_data_dir / f"health_report_{timestamp}.json", 'w', encoding='utf-8') as f:
                json.dump(health_report, f, indent=2, ensure_ascii=False)
            
            # エラーレポート
            error_tracker = get_error_tracker()
            error_report = error_tracker.get_error_report(days=7)
            with open(final_data_dir / f"error_report_{timestamp}.json", 'w', encoding='utf-8') as f:
                json.dump(error_report, f, indent=2, ensure_ascii=False)
            
            # パフォーマンスレポート
            performance_monitor = get_performance_monitor()
            performance_report = performance_monitor.get_performance_report(hours=24)
            with open(final_data_dir / f"performance_report_{timestamp}.json", 'w', encoding='utf-8') as f:
                json.dump(performance_report, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            self.logger.error(f"最終データ保存失敗: {e}")


# グローバル統合監視システム
_global_monitoring_integration: Optional[MonitoringIntegration] = None


def initialize_monitoring(config: Optional[Dict[str, Any]] = None) -> MonitoringIntegration:
    """統合監視システムを初期化"""
    global _global_monitoring_integration
    if _global_monitoring_integration is None:
        _global_monitoring_integration = MonitoringIntegration(config)
    return _global_monitoring_integration


def get_monitoring_integration() -> Optional[MonitoringIntegration]:
    """統合監視システムインスタンスを取得"""
    return _global_monitoring_integration


# 便利関数
def log_performance(operation_name: str, context: Optional[Dict[str, Any]] = None):
    """パフォーマンス測定の便利関数"""
    return measure_operation(operation_name, context)


def log_error(exception: Exception, context: Optional[Dict[str, Any]] = None, user_impact: str = "medium"):
    """エラー追跡の便利関数"""
    return track_error(exception, context, user_impact)


def get_system_status() -> Dict[str, Any]:
    """システム状態取得の便利関数"""
    monitoring = get_monitoring_integration()
    if monitoring:
        return monitoring.get_system_health_report()
    else:
        return {"status": "monitoring_not_initialized"}