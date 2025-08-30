"""
パフォーマンス監視システム実装 (CLAUDE.md準拠)
リアルタイムパフォーマンス追跡・分析・最適化推奨機能を提供
"""

import time
import psutil
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, NamedTuple
from collections import deque, defaultdict
import json
from pathlib import Path
import statistics
from contextlib import contextmanager
import functools

from src.utils.structured_logger import get_logger


class PerformanceMetric(NamedTuple):
    """パフォーマンス指標"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    context: Dict[str, Any]


@dataclass
class SystemMetrics:
    """システム指標"""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    network_io_mb: float
    process_count: int
    timestamp: datetime


@dataclass
class PerformanceStats:
    """パフォーマンス統計"""
    operation_name: str
    total_calls: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    median_time: float = 0.0
    percentile_95: float = 0.0
    percentile_99: float = 0.0
    error_count: int = 0
    success_rate: float = 100.0
    recent_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    def add_measurement(self, duration: float, success: bool = True):
        """測定値を追加"""
        self.total_calls += 1
        self.total_time += duration
        self.recent_times.append(duration)
        
        if success:
            self.min_time = min(self.min_time, duration)
            self.max_time = max(self.max_time, duration)
        else:
            self.error_count += 1
        
        # 統計を更新
        if self.recent_times:
            times_list = list(self.recent_times)
            self.avg_time = statistics.mean(times_list)
            self.median_time = statistics.median(times_list)
            
            if len(times_list) >= 20:  # 十分なサンプル数がある場合
                self.percentile_95 = statistics.quantiles(times_list, n=20)[18]  # 95%
                self.percentile_99 = statistics.quantiles(times_list, n=100)[98] if len(times_list) >= 100 else max(times_list)
        
        self.success_rate = ((self.total_calls - self.error_count) / self.total_calls) * 100


class PerformanceMonitor:
    """
    パフォーマンス監視システム
    
    CLAUDE.md準拠のリアルタイムパフォーマンス追跡・分析機能
    """
    
    def __init__(
        self,
        storage_path: str = "./logs/performance",
        collection_interval: float = 5.0,
        retention_hours: int = 24,
        alert_thresholds: Optional[Dict[str, float]] = None
    ):
        """
        パフォーマンスモニターを初期化
        
        Args:
            storage_path: パフォーマンスデータ保存パス
            collection_interval: システム指標収集間隔（秒）
            retention_hours: データ保持時間
            alert_thresholds: アラート閾値設定
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.collection_interval = collection_interval
        self.retention_hours = retention_hours
        
        # デフォルトアラート閾値
        self.alert_thresholds = alert_thresholds or {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_usage_percent': 90.0,
            'response_time_ms': 1000.0,
            'error_rate_percent': 5.0
        }
        
        self.logger = get_logger(__name__)
        
        # パフォーマンス統計
        self.operation_stats: Dict[str, PerformanceStats] = defaultdict(PerformanceStats)
        
        # システム指標履歴
        self.system_metrics_history: deque = deque(maxlen=int(retention_hours * 3600 / collection_interval))
        
        # メトリクス履歴
        self.metrics_history: deque = deque(maxlen=10000)
        
        # アラートコールバック
        self.alert_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        
        # 監視スレッド
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        
        # アプリケーション開始時刻
        self.start_time = datetime.now()
        
        self.logger.info("パフォーマンス監視システム初期化完了", extra={
            "storage_path": str(self.storage_path),
            "collection_interval": collection_interval,
            "retention_hours": retention_hours,
            "alert_thresholds": self.alert_thresholds
        })
    
    def start_monitoring(self):
        """システム監視を開始"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self._monitor_system, daemon=True)
            self.monitoring_thread.start()
            self.logger.info("システム監視開始")
    
    def stop_monitoring(self):
        """システム監視を停止"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        self.logger.info("システム監視停止")
    
    @contextmanager
    def measure_operation(self, operation_name: str, context: Optional[Dict[str, Any]] = None):
        """
        操作の実行時間を測定
        
        Args:
            operation_name: 操作名
            context: コンテキスト情報
        """
        start_time = time.perf_counter()
        success = True
        
        try:
            yield
        except Exception as e:
            success = False
            # エラーも記録
            from src.utils.error_tracker import track_error
            track_error(e, context={"operation": operation_name})
            raise
        finally:
            duration = time.perf_counter() - start_time
            
            # 統計を更新
            if operation_name not in self.operation_stats:
                self.operation_stats[operation_name] = PerformanceStats(operation_name=operation_name)
            
            self.operation_stats[operation_name].add_measurement(duration, success)
            
            # メトリクス履歴に追加
            metric = PerformanceMetric(
                name=f"{operation_name}_duration",
                value=duration * 1000,  # ミリ秒に変換
                unit="ms",
                timestamp=datetime.now(),
                context=context or {}
            )
            self.metrics_history.append(metric)
            
            # アラートチェック
            self._check_performance_alerts(operation_name, duration * 1000, success)
            
            # ログ出力
            self.logger.info(f"パフォーマンス測定: {operation_name}", extra={
                "operation": operation_name,
                "duration_ms": duration * 1000,
                "success": success,
                "context": context,
                "avg_time_ms": self.operation_stats[operation_name].avg_time * 1000
            })
    
    def measure_function(self, operation_name: Optional[str] = None):
        """
        関数デコレータ：関数の実行時間を自動測定
        
        Args:
            operation_name: 操作名（指定しない場合は関数名を使用）
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                name = operation_name or f"{func.__module__}.{func.__name__}"
                context = {
                    "function": func.__name__,
                    "module": func.__module__,
                    "args_count": len(args),
                    "kwargs_count": len(kwargs)
                }
                
                with self.measure_operation(name, context):
                    return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def record_metric(self, name: str, value: float, unit: str = "", context: Optional[Dict[str, Any]] = None):
        """
        カスタムメトリクスを記録
        
        Args:
            name: メトリクス名
            value: 値
            unit: 単位
            context: コンテキスト情報
        """
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            context=context or {}
        )
        self.metrics_history.append(metric)
        
        self.logger.info(f"カスタムメトリクス: {name}", extra={
            "metric_name": name,
            "value": value,
            "unit": unit,
            "context": context
        })
    
    def get_system_metrics(self) -> SystemMetrics:
        """現在のシステム指標を取得"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # メモリ情報
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            memory_available_mb = memory.available / (1024 * 1024)
            
            # ディスク情報
            disk = psutil.disk_usage('/')
            disk_usage_percent = disk.percent
            disk_free_gb = disk.free / (1024 * 1024 * 1024)
            
            # ネットワークI/O
            network_io = psutil.net_io_counters()
            network_io_mb = (network_io.bytes_sent + network_io.bytes_recv) / (1024 * 1024)
            
            # プロセス数
            process_count = len(psutil.pids())
            
            return SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                memory_available_mb=memory_available_mb,
                disk_usage_percent=disk_usage_percent,
                disk_free_gb=disk_free_gb,
                network_io_mb=network_io_mb,
                process_count=process_count,
                timestamp=datetime.now()
            )
        except Exception as e:
            self.logger.warning(f"システム指標取得エラー: {e}")
            return SystemMetrics(
                cpu_percent=0.0, memory_percent=0.0, memory_used_mb=0.0,
                memory_available_mb=0.0, disk_usage_percent=0.0, disk_free_gb=0.0,
                network_io_mb=0.0, process_count=0, timestamp=datetime.now()
            )
    
    def get_performance_report(self, hours: int = 1) -> Dict[str, Any]:
        """
        パフォーマンスレポートを生成
        
        Args:
            hours: 対象時間（時間）
            
        Returns:
            Dict[str, Any]: パフォーマンスレポート
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # システム指標統計
        recent_system_metrics = [
            m for m in self.system_metrics_history
            if m.timestamp >= cutoff_time
        ]
        
        system_stats = {}
        if recent_system_metrics:
            system_stats = {
                "avg_cpu_percent": statistics.mean([m.cpu_percent for m in recent_system_metrics]),
                "max_cpu_percent": max([m.cpu_percent for m in recent_system_metrics]),
                "avg_memory_percent": statistics.mean([m.memory_percent for m in recent_system_metrics]),
                "max_memory_percent": max([m.memory_percent for m in recent_system_metrics]),
                "avg_disk_usage_percent": statistics.mean([m.disk_usage_percent for m in recent_system_metrics]),
                "min_disk_free_gb": min([m.disk_free_gb for m in recent_system_metrics])
            }
        
        # 操作統計
        operation_summaries = {}
        for name, stats in self.operation_stats.items():
            if stats.total_calls > 0:
                operation_summaries[name] = {
                    "total_calls": stats.total_calls,
                    "success_rate": stats.success_rate,
                    "avg_time_ms": stats.avg_time * 1000,
                    "median_time_ms": stats.median_time * 1000,
                    "percentile_95_ms": stats.percentile_95 * 1000,
                    "min_time_ms": stats.min_time * 1000,
                    "max_time_ms": stats.max_time * 1000,
                    "error_count": stats.error_count
                }
        
        # 最近のメトリクス
        recent_metrics = [
            m for m in self.metrics_history
            if m.timestamp >= cutoff_time
        ]
        
        # トップ課題の特定
        performance_issues = []
        
        for name, stats in self.operation_stats.items():
            if stats.success_rate < 95.0:
                performance_issues.append({
                    "type": "low_success_rate",
                    "operation": name,
                    "success_rate": stats.success_rate,
                    "severity": "high" if stats.success_rate < 90 else "medium"
                })
            
            if stats.avg_time > 1.0:  # 1秒以上
                performance_issues.append({
                    "type": "slow_operation",
                    "operation": name,
                    "avg_time_ms": stats.avg_time * 1000,
                    "severity": "high" if stats.avg_time > 5.0 else "medium"
                })
        
        # システムリソース課題
        current_system = self.get_system_metrics()
        if current_system.cpu_percent > self.alert_thresholds['cpu_percent']:
            performance_issues.append({
                "type": "high_cpu_usage",
                "value": current_system.cpu_percent,
                "threshold": self.alert_thresholds['cpu_percent'],
                "severity": "high" if current_system.cpu_percent > 90 else "medium"
            })
        
        if current_system.memory_percent > self.alert_thresholds['memory_percent']:
            performance_issues.append({
                "type": "high_memory_usage",
                "value": current_system.memory_percent,
                "threshold": self.alert_thresholds['memory_percent'],
                "severity": "high" if current_system.memory_percent > 95 else "medium"
            })
        
        uptime_hours = (datetime.now() - self.start_time).total_seconds() / 3600
        
        return {
            "report_period_hours": hours,
            "generated_at": datetime.now().isoformat(),
            "uptime_hours": uptime_hours,
            "system_metrics": system_stats,
            "operation_statistics": operation_summaries,
            "current_system_status": {
                "cpu_percent": current_system.cpu_percent,
                "memory_percent": current_system.memory_percent,
                "disk_usage_percent": current_system.disk_usage_percent,
                "disk_free_gb": current_system.disk_free_gb
            },
            "performance_issues": performance_issues,
            "metrics_collected": len(recent_metrics),
            "recommendations": self._generate_performance_recommendations(performance_issues)
        }
    
    def add_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """
        アラートコールバックを追加
        
        Args:
            callback: アラートコールバック関数
        """
        self.alert_callbacks.append(callback)
    
    def _monitor_system(self):
        """システム監視ループ"""
        while self.monitoring_active:
            try:
                metrics = self.get_system_metrics()
                self.system_metrics_history.append(metrics)
                
                # システムアラートチェック
                self._check_system_alerts(metrics)
                
                # データ保存
                self._save_metrics_data()
                
            except Exception as e:
                self.logger.warning(f"システム監視エラー: {e}")
            
            time.sleep(self.collection_interval)
    
    def _check_performance_alerts(self, operation_name: str, duration_ms: float, success: bool):
        """パフォーマンスアラートチェック"""
        alerts = []
        
        if duration_ms > self.alert_thresholds['response_time_ms']:
            alerts.append({
                "type": "slow_operation",
                "operation": operation_name,
                "duration_ms": duration_ms,
                "threshold_ms": self.alert_thresholds['response_time_ms']
            })
        
        if not success:
            stats = self.operation_stats[operation_name]
            error_rate = (stats.error_count / stats.total_calls) * 100
            if error_rate > self.alert_thresholds['error_rate_percent']:
                alerts.append({
                    "type": "high_error_rate",
                    "operation": operation_name,
                    "error_rate_percent": error_rate,
                    "threshold_percent": self.alert_thresholds['error_rate_percent']
                })
        
        for alert in alerts:
            self._trigger_alert("performance", alert)
    
    def _check_system_alerts(self, metrics: SystemMetrics):
        """システムアラートチェック"""
        alerts = []
        
        if metrics.cpu_percent > self.alert_thresholds['cpu_percent']:
            alerts.append({
                "type": "high_cpu",
                "value": metrics.cpu_percent,
                "threshold": self.alert_thresholds['cpu_percent']
            })
        
        if metrics.memory_percent > self.alert_thresholds['memory_percent']:
            alerts.append({
                "type": "high_memory",
                "value": metrics.memory_percent,
                "threshold": self.alert_thresholds['memory_percent']
            })
        
        if metrics.disk_usage_percent > self.alert_thresholds['disk_usage_percent']:
            alerts.append({
                "type": "low_disk_space",
                "value": metrics.disk_usage_percent,
                "threshold": self.alert_thresholds['disk_usage_percent']
            })
        
        for alert in alerts:
            self._trigger_alert("system", alert)
    
    def _trigger_alert(self, category: str, alert_data: Dict[str, Any]):
        """アラートを発生させる"""
        for callback in self.alert_callbacks:
            try:
                callback(category, alert_data)
            except Exception as e:
                self.logger.warning(f"アラートコールバック失敗: {e}")
        
        # ログ出力
        self.logger.warning(f"🚨 {category.upper()}アラート: {alert_data['type']}", extra={
            "alert_category": category,
            "alert_data": alert_data
        })
    
    def _generate_performance_recommendations(self, issues: List[Dict[str, Any]]) -> List[str]:
        """パフォーマンス改善推奨事項を生成"""
        recommendations = []
        
        for issue in issues:
            if issue["type"] == "high_cpu_usage":
                recommendations.append("CPU使用率が高いため、処理の最適化またはリソース増強を検討してください")
            elif issue["type"] == "high_memory_usage":
                recommendations.append("メモリ使用率が高いため、メモリリーク確認またはメモリ最適化を検討してください")
            elif issue["type"] == "slow_operation":
                recommendations.append(f"操作'{issue['operation']}'が遅いため、アルゴリズム最適化を検討してください")
            elif issue["type"] == "low_success_rate":
                recommendations.append(f"操作'{issue['operation']}'の成功率が低いため、エラーハンドリング改善を検討してください")
        
        if not recommendations:
            recommendations.append("現在、重大なパフォーマンス問題は検出されていません")
        
        return recommendations
    
    def _save_metrics_data(self):
        """メトリクスデータの保存"""
        try:
            metrics_file = self.storage_path / f"metrics_{datetime.now().strftime('%Y%m%d')}.json"
            
            # 今日のメトリクスを収集
            today = datetime.now().date()
            today_metrics = [
                {
                    "name": m.name,
                    "value": m.value,
                    "unit": m.unit,
                    "timestamp": m.timestamp.isoformat(),
                    "context": m.context
                }
                for m in self.metrics_history
                if m.timestamp.date() == today
            ]
            
            if today_metrics:
                with open(metrics_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "date": today.isoformat(),
                        "metrics": today_metrics,
                        "last_updated": datetime.now().isoformat()
                    }, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            self.logger.warning(f"メトリクスデータ保存失敗: {e}")


# グローバルパフォーマンスモニター
_global_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """グローバルパフォーマンスモニターを取得"""
    global _global_performance_monitor
    if _global_performance_monitor is None:
        _global_performance_monitor = PerformanceMonitor()
    return _global_performance_monitor


def measure_operation(operation_name: str, context: Optional[Dict[str, Any]] = None):
    """操作測定の便利関数"""
    return get_performance_monitor().measure_operation(operation_name, context)


def measure_function(operation_name: Optional[str] = None):
    """関数測定デコレータの便利関数"""
    return get_performance_monitor().measure_function(operation_name)


def setup_performance_alerts():
    """デフォルトパフォーマンスアラートの設定"""
    def default_alert_callback(category: str, alert_data: Dict[str, Any]):
        logger = get_logger("performance_alerts")
        severity = "CRITICAL" if alert_data.get("value", 0) > 95 else "WARNING"
        
        logger.warning(
            f"🚨 {severity} {category.upper()}パフォーマンスアラート: {alert_data['type']}",
            extra={
                "alert_category": category,
                "alert_type": alert_data['type'],
                "alert_data": alert_data,
                "severity": severity
            }
        )
    
    get_performance_monitor().add_alert_callback(default_alert_callback)