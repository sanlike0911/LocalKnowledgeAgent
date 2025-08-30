"""
エラー追跡システム実装 (CLAUDE.md準拠)
包括的なエラー監視・分析・アラート機能を提供
"""

import logging
import traceback
import hashlib
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set
from pathlib import Path
from collections import defaultdict, Counter
import json

from src.utils.structured_logger import get_logger


@dataclass
class ErrorInfo:
    """エラー情報データクラス"""
    error_id: str
    error_type: str
    error_message: str
    stack_trace: str
    module: str
    function: str
    line_number: int
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    user_impact: str = "unknown"  # low, medium, high, critical
    resolution_status: str = "open"  # open, investigating, resolved, ignored
    occurrence_count: int = 1
    first_seen: datetime = None
    last_seen: datetime = None
    
    def __post_init__(self):
        if self.first_seen is None:
            self.first_seen = self.timestamp
        if self.last_seen is None:
            self.last_seen = self.timestamp


@dataclass 
class ErrorMetrics:
    """エラーメトリクス"""
    total_errors: int = 0
    unique_errors: int = 0
    critical_errors: int = 0
    error_rate: float = 0.0
    most_frequent_errors: List[Dict[str, Any]] = field(default_factory=list)
    error_trends: Dict[str, List[int]] = field(default_factory=dict)
    uptime_percentage: float = 100.0


class ErrorTracker:
    """
    エラー追跡システム
    
    CLAUDE.md準拠のエラー監視・分析・レポート機能を提供
    """
    
    def __init__(
        self,
        storage_path: str = "./logs/error_tracking",
        max_errors_in_memory: int = 1000,
        alert_threshold: int = 5,
        cleanup_days: int = 30
    ):
        """
        エラートラッカーを初期化
        
        Args:
            storage_path: エラーデータ保存パス
            max_errors_in_memory: メモリ内保持エラー数上限
            alert_threshold: アラート閾値
            cleanup_days: クリーンアップ日数
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.max_errors_in_memory = max_errors_in_memory
        self.alert_threshold = alert_threshold
        self.cleanup_days = cleanup_days
        
        self.logger = get_logger(__name__)
        
        # エラー情報を格納
        self.errors: Dict[str, ErrorInfo] = {}
        self.error_counts: Counter = Counter()
        self.error_timeline: List[Dict[str, Any]] = []
        
        # アラートコールバック
        self.alert_callbacks: List[Callable[[ErrorInfo], None]] = []
        
        # パフォーマンス追跡
        self.start_time = datetime.now()
        self.total_requests = 0
        self.failed_requests = 0
        
        # 既存エラーデータの読み込み
        self._load_existing_errors()
        
        self.logger.info("エラー追跡システム初期化完了", extra={
            "storage_path": str(self.storage_path),
            "max_errors_in_memory": max_errors_in_memory,
            "alert_threshold": alert_threshold
        })
    
    def track_error(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        user_impact: str = "medium"
    ) -> str:
        """
        エラーを追跡
        
        Args:
            exception: 例外オブジェクト
            context: エラーコンテキスト
            user_impact: ユーザー影響度
            
        Returns:
            str: エラーID
        """
        # エラー情報を抽出
        tb = traceback.extract_tb(exception.__traceback__)
        if tb:
            last_frame = tb[-1]
            module = last_frame.filename
            function = last_frame.name
            line_number = last_frame.lineno
        else:
            module = "unknown"
            function = "unknown" 
            line_number = 0
        
        # エラーIDを生成（重複検出のため）
        error_signature = f"{type(exception).__name__}:{str(exception)}:{module}:{function}:{line_number}"
        error_id = hashlib.md5(error_signature.encode()).hexdigest()[:12]
        
        # エラー情報を作成
        if error_id in self.errors:
            # 既存エラーの発生回数を更新
            existing_error = self.errors[error_id]
            existing_error.occurrence_count += 1
            existing_error.last_seen = datetime.now()
        else:
            # 新規エラーを記録
            error_info = ErrorInfo(
                error_id=error_id,
                error_type=type(exception).__name__,
                error_message=str(exception),
                stack_trace=traceback.format_exception(type(exception), exception, exception.__traceback__),
                module=module,
                function=function,
                line_number=line_number,
                timestamp=datetime.now(),
                context=context or {},
                user_impact=user_impact
            )
            
            self.errors[error_id] = error_info
        
        # カウンターを更新
        self.error_counts[error_id] += 1
        self.failed_requests += 1
        
        # タイムライン追加
        self.error_timeline.append({
            "timestamp": datetime.now().isoformat(),
            "error_id": error_id,
            "error_type": type(exception).__name__,
            "user_impact": user_impact
        })
        
        # メモリ制限チェック
        self._cleanup_memory()
        
        # アラートチェック
        self._check_alerts(self.errors[error_id])
        
        # ストレージに保存
        self._save_error_data()
        
        # ログ出力
        self.logger.error(
            f"エラー追跡: {type(exception).__name__}",
            extra={
                "error_id": error_id,
                "error_type": type(exception).__name__,
                "error_message": str(exception),
                "user_impact": user_impact,
                "context": context,
                "occurrence_count": self.errors[error_id].occurrence_count
            },
            exc_info=True
        )
        
        return error_id
    
    def track_request(self, success: bool = True):
        """
        リクエスト追跡
        
        Args:
            success: リクエスト成功フラグ
        """
        self.total_requests += 1
        if not success:
            self.failed_requests += 1
    
    def add_alert_callback(self, callback: Callable[[ErrorInfo], None]):
        """
        アラートコールバックを追加
        
        Args:
            callback: アラートコールバック関数
        """
        self.alert_callbacks.append(callback)
    
    def get_error_metrics(self) -> ErrorMetrics:
        """
        エラーメトリクスを取得
        
        Returns:
            ErrorMetrics: エラーメトリクス
        """
        # 最頻出エラーTOP5
        most_frequent = [
            {
                "error_id": error_id,
                "error_type": self.errors[error_id].error_type,
                "error_message": self.errors[error_id].error_message,
                "count": count,
                "user_impact": self.errors[error_id].user_impact
            }
            for error_id, count in self.error_counts.most_common(5)
            if error_id in self.errors
        ]
        
        # クリティカルエラー数
        critical_count = sum(
            1 for error in self.errors.values() 
            if error.user_impact == "critical"
        )
        
        # エラー率計算
        error_rate = (self.failed_requests / max(self.total_requests, 1)) * 100
        
        # 稼働時間計算
        uptime_hours = (datetime.now() - self.start_time).total_seconds() / 3600
        expected_uptime = uptime_hours
        downtime_impact = sum(
            error.occurrence_count for error in self.errors.values()
            if error.user_impact in ["high", "critical"]
        )
        uptime_percentage = max(0, 100 - (downtime_impact / max(expected_uptime, 1)))
        
        return ErrorMetrics(
            total_errors=sum(self.error_counts.values()),
            unique_errors=len(self.errors),
            critical_errors=critical_count,
            error_rate=error_rate,
            most_frequent_errors=most_frequent,
            uptime_percentage=uptime_percentage
        )
    
    def get_error_report(self, days: int = 7) -> Dict[str, Any]:
        """
        エラーレポートを生成
        
        Args:
            days: 対象日数
            
        Returns:
            Dict[str, Any]: エラーレポート
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # 期間内のエラーをフィルタ
        recent_errors = [
            error for error in self.errors.values()
            if error.last_seen >= cutoff_date
        ]
        
        # エラー種別別統計
        error_types = Counter(error.error_type for error in recent_errors)
        
        # 影響度別統計
        impact_stats = Counter(error.user_impact for error in recent_errors)
        
        # 日別エラー数
        daily_counts = defaultdict(int)
        for error in recent_errors:
            date_key = error.last_seen.strftime('%Y-%m-%d')
            daily_counts[date_key] += error.occurrence_count
        
        metrics = self.get_error_metrics()
        
        return {
            "report_period_days": days,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_errors": len(recent_errors),
                "total_occurrences": sum(error.occurrence_count for error in recent_errors),
                "unique_errors": len(recent_errors),
                "critical_errors": impact_stats.get("critical", 0),
                "error_rate": metrics.error_rate,
                "uptime_percentage": metrics.uptime_percentage
            },
            "error_types": dict(error_types.most_common()),
            "impact_distribution": dict(impact_stats),
            "daily_error_counts": dict(daily_counts),
            "most_frequent_errors": metrics.most_frequent_errors,
            "unresolved_errors": [
                {
                    "error_id": error.error_id,
                    "error_type": error.error_type,
                    "error_message": error.error_message[:100],
                    "occurrence_count": error.occurrence_count,
                    "user_impact": error.user_impact,
                    "first_seen": error.first_seen.isoformat(),
                    "last_seen": error.last_seen.isoformat()
                }
                for error in recent_errors
                if error.resolution_status == "open"
            ]
        }
    
    def mark_error_resolved(self, error_id: str, resolution_note: str = ""):
        """
        エラーを解決済みにマーク
        
        Args:
            error_id: エラーID
            resolution_note: 解決メモ
        """
        if error_id in self.errors:
            self.errors[error_id].resolution_status = "resolved"
            self.logger.info(f"エラー解決: {error_id}", extra={
                "error_id": error_id,
                "resolution_note": resolution_note,
                "resolved_at": datetime.now().isoformat()
            })
    
    def _check_alerts(self, error_info: ErrorInfo):
        """アラートチェック"""
        if error_info.occurrence_count >= self.alert_threshold:
            for callback in self.alert_callbacks:
                try:
                    callback(error_info)
                except Exception as e:
                    self.logger.warning(f"アラートコールバック失敗: {e}")
    
    def _cleanup_memory(self):
        """メモリクリーンアップ"""
        if len(self.errors) > self.max_errors_in_memory:
            # 古いエラーを削除（解決済み優先）
            sorted_errors = sorted(
                self.errors.items(),
                key=lambda x: (x[1].resolution_status == "resolved", x[1].last_seen)
            )
            
            # 上限の70%まで削減
            target_size = int(self.max_errors_in_memory * 0.7)
            errors_to_remove = len(self.errors) - target_size
            
            for i in range(errors_to_remove):
                error_id = sorted_errors[i][0]
                del self.errors[error_id]
                if error_id in self.error_counts:
                    del self.error_counts[error_id]
    
    def _load_existing_errors(self):
        """既存エラーデータの読み込み"""
        error_file = self.storage_path / "errors.json"
        if error_file.exists():
            try:
                with open(error_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                for error_data in data.get("errors", []):
                    error_info = ErrorInfo(**error_data)
                    self.errors[error_info.error_id] = error_info
                    self.error_counts[error_info.error_id] = error_info.occurrence_count
                    
                self.logger.info(f"既存エラーデータ読み込み完了: {len(self.errors)}件")
            except Exception as e:
                self.logger.warning(f"既存エラーデータ読み込み失敗: {e}")
    
    def _save_error_data(self):
        """エラーデータの保存"""
        try:
            error_file = self.storage_path / "errors.json"
            
            # 辞書形式に変換
            errors_data = []
            for error in self.errors.values():
                error_dict = asdict(error)
                error_dict['timestamp'] = error.timestamp.isoformat()
                error_dict['first_seen'] = error.first_seen.isoformat()
                error_dict['last_seen'] = error.last_seen.isoformat()
                errors_data.append(error_dict)
            
            data = {
                "last_updated": datetime.now().isoformat(),
                "total_errors": len(self.errors),
                "errors": errors_data
            }
            
            with open(error_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.warning(f"エラーデータ保存失敗: {e}")
    
    def cleanup_old_data(self):
        """古いデータのクリーンアップ"""
        cutoff_date = datetime.now() - timedelta(days=self.cleanup_days)
        
        # 古いエラーを削除
        old_error_ids = [
            error_id for error_id, error in self.errors.items()
            if error.last_seen < cutoff_date and error.resolution_status == "resolved"
        ]
        
        for error_id in old_error_ids:
            del self.errors[error_id]
            if error_id in self.error_counts:
                del self.error_counts[error_id]
        
        if old_error_ids:
            self.logger.info(f"古いエラーデータクリーンアップ: {len(old_error_ids)}件削除")
            self._save_error_data()


# グローバルエラートラッカー
_global_error_tracker: Optional[ErrorTracker] = None


def get_error_tracker() -> ErrorTracker:
    """グローバルエラートラッカーを取得"""
    global _global_error_tracker
    if _global_error_tracker is None:
        _global_error_tracker = ErrorTracker()
    return _global_error_tracker


def track_error(exception: Exception, context: Optional[Dict[str, Any]] = None, user_impact: str = "medium") -> str:
    """エラー追跡の便利関数"""
    return get_error_tracker().track_error(exception, context, user_impact)


def setup_error_alerts():
    """デフォルトエラーアラートの設定"""
    def default_alert_callback(error_info: ErrorInfo):
        logger = get_logger("error_alerts")
        logger.critical(
            f"🚨 繰り返しエラー検出: {error_info.error_type}",
            extra={
                "error_id": error_info.error_id,
                "occurrence_count": error_info.occurrence_count,
                "user_impact": error_info.user_impact,
                "error_message": error_info.error_message,
                "first_seen": error_info.first_seen.isoformat(),
                "last_seen": error_info.last_seen.isoformat(),
                "alert_type": "frequency_threshold"
            }
        )
    
    get_error_tracker().add_alert_callback(default_alert_callback)