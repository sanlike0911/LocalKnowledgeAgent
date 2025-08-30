"""
進捗表示ユーティリティ (CLAUDE.md準拠)
3秒以上の処理に対する進捗表示機能を提供
"""

import time
from typing import Callable, Optional, Any, Dict, List
from threading import Event, Thread
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from contextlib import contextmanager


@dataclass
class ProgressInfo:
    """進捗情報クラス"""
    current: int
    total: int
    message: str
    start_time: datetime
    estimated_remaining: Optional[float] = None
    
    @property
    def progress_rate(self) -> float:
        """進捗率を取得 (0.0-1.0)"""
        if self.total <= 0:
            return 0.0
        return min(self.current / self.total, 1.0)
    
    @property
    def percentage(self) -> float:
        """進捗率をパーセンテージで取得 (0-100)"""
        return self.progress_rate * 100
    
    @property
    def elapsed_time(self) -> float:
        """経過時間（秒）"""
        return (datetime.now() - self.start_time).total_seconds()
    
    def estimate_remaining_time(self) -> Optional[float]:
        """残り時間を推定（秒）"""
        if self.current <= 0 or self.progress_rate >= 1.0:
            return None
        
        elapsed = self.elapsed_time
        if elapsed <= 0:
            return None
        
        remaining_rate = 1.0 - self.progress_rate
        estimated_total_time = elapsed / self.progress_rate
        return estimated_total_time * remaining_rate
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "current": self.current,
            "total": self.total,
            "message": self.message,
            "progress_rate": self.progress_rate,
            "percentage": round(self.percentage, 1),
            "elapsed_time": round(self.elapsed_time, 1),
            "estimated_remaining": self.estimate_remaining_time(),
            "start_time": self.start_time.isoformat()
        }


class ProgressTracker:
    """
    進捗追跡クラス
    
    長時間処理の進捗を追跡し、コールバック関数を通じて進捗を通知
    """
    
    def __init__(
        self,
        total: int,
        callback: Optional[Callable[[ProgressInfo], None]] = None,
        min_update_interval: float = 0.1,
        description: str = "処理中"
    ):
        """
        進捗追跡を初期化
        
        Args:
            total: 総処理数
            callback: 進捗更新コールバック
            min_update_interval: 最小更新間隔（秒）
            description: 処理説明
        """
        self.total = total
        self.current = 0
        self.callback = callback
        self.min_update_interval = min_update_interval
        self.description = description
        self.start_time = datetime.now()
        self.last_update_time = 0.0
        self.cancelled = Event()
        self.logger = logging.getLogger(__name__)
        
        # 初期進捗を通知
        self._notify_progress("開始")
    
    def update(self, increment: int = 1, message: Optional[str] = None) -> None:
        """
        進捗を更新
        
        Args:
            increment: 増分
            message: 進捗メッセージ
        """
        if self.cancelled.is_set():
            return
        
        self.current = min(self.current + increment, self.total)
        current_time = time.time()
        
        # 最小更新間隔をチェック
        if current_time - self.last_update_time < self.min_update_interval:
            return
        
        self.last_update_time = current_time
        display_message = message or f"{self.description} ({self.current}/{self.total})"
        
        self._notify_progress(display_message)
    
    def set_current(self, current: int, message: Optional[str] = None) -> None:
        """
        現在位置を設定
        
        Args:
            current: 現在位置
            message: 進捗メッセージ
        """
        if self.cancelled.is_set():
            return
        
        self.current = min(max(current, 0), self.total)
        display_message = message or f"{self.description} ({self.current}/{self.total})"
        
        self._notify_progress(display_message)
    
    def finish(self, message: Optional[str] = None) -> None:
        """
        進捗を完了
        
        Args:
            message: 完了メッセージ
        """
        self.current = self.total
        display_message = message or f"{self.description} 完了"
        
        self._notify_progress(display_message)
        
        self.logger.info(f"進捗完了: {self.description}", extra={
            "total_items": self.total,
            "elapsed_time": self.get_progress_info().elapsed_time
        })
    
    def cancel(self) -> None:
        """進捗をキャンセル"""
        self.cancelled.set()
        self.logger.info(f"進捗キャンセル: {self.description}")
    
    def is_cancelled(self) -> bool:
        """キャンセル状態を確認"""
        return self.cancelled.is_set()
    
    def get_progress_info(self) -> ProgressInfo:
        """進捗情報を取得"""
        return ProgressInfo(
            current=self.current,
            total=self.total,
            message=self.description,
            start_time=self.start_time
        )
    
    def _notify_progress(self, message: str) -> None:
        """進捗をコールバックで通知"""
        progress_info = ProgressInfo(
            current=self.current,
            total=self.total,
            message=message,
            start_time=self.start_time
        )
        
        if self.callback:
            try:
                self.callback(progress_info)
            except Exception as e:
                self.logger.warning(f"進捗コールバックエラー: {e}")


class TimerProgressTracker:
    """
    タイマーベース進捗追跡クラス
    
    時間ベースで進捗を管理（処理数が不明な場合に使用）
    """
    
    def __init__(
        self,
        estimated_duration: float,
        callback: Optional[Callable[[ProgressInfo], None]] = None,
        update_interval: float = 1.0,
        description: str = "処理中"
    ):
        """
        タイマー進捗追跡を初期化
        
        Args:
            estimated_duration: 推定実行時間（秒）
            callback: 進捗更新コールバック
            update_interval: 更新間隔（秒）
            description: 処理説明
        """
        self.estimated_duration = estimated_duration
        self.callback = callback
        self.update_interval = update_interval
        self.description = description
        self.start_time = datetime.now()
        self.cancelled = Event()
        self.logger = logging.getLogger(__name__)
        self._timer_thread: Optional[Thread] = None
    
    def start(self) -> None:
        """タイマー進捗を開始"""
        if self._timer_thread and self._timer_thread.is_alive():
            return
        
        self._timer_thread = Thread(target=self._timer_loop, daemon=True)
        self._timer_thread.start()
        
        self.logger.info(f"タイマー進捗開始: {self.description}")
    
    def stop(self, message: Optional[str] = None) -> None:
        """タイマー進捗を停止"""
        self.cancelled.set()
        
        if self._timer_thread:
            self._timer_thread.join(timeout=1.0)
        
        # 完了進捗を通知
        if self.callback:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            progress_info = ProgressInfo(
                current=100,
                total=100,
                message=message or f"{self.description} 完了",
                start_time=self.start_time
            )
            self.callback(progress_info)
        
        self.logger.info(f"タイマー進捗停止: {self.description}")
    
    def _timer_loop(self) -> None:
        """タイマーループ"""
        while not self.cancelled.is_set():
            elapsed = (datetime.now() - self.start_time).total_seconds()
            progress_rate = min(elapsed / self.estimated_duration, 0.95)  # 最大95%まで
            
            if self.callback:
                progress_info = ProgressInfo(
                    current=int(progress_rate * 100),
                    total=100,
                    message=self.description,
                    start_time=self.start_time
                )
                self.callback(progress_info)
            
            if self.cancelled.wait(self.update_interval):
                break


@contextmanager
def progress_context(
    total: int,
    callback: Optional[Callable[[ProgressInfo], None]] = None,
    description: str = "処理中",
    auto_finish: bool = True
):
    """
    進捗追跡コンテキストマネージャー
    
    Args:
        total: 総処理数
        callback: 進捗コールバック
        description: 処理説明
        auto_finish: 自動完了フラグ
        
    Yields:
        ProgressTracker: 進捗追跡オブジェクト
    """
    tracker = ProgressTracker(total, callback, description=description)
    try:
        yield tracker
    finally:
        if auto_finish and not tracker.is_cancelled():
            tracker.finish()


@contextmanager
def timer_progress_context(
    estimated_duration: float,
    callback: Optional[Callable[[ProgressInfo], None]] = None,
    description: str = "処理中"
):
    """
    タイマー進捗追跡コンテキストマネージャー
    
    Args:
        estimated_duration: 推定実行時間（秒）
        callback: 進捗コールバック
        description: 処理説明
        
    Yields:
        TimerProgressTracker: タイマー進捗追跡オブジェクト
    """
    tracker = TimerProgressTracker(estimated_duration, callback, description=description)
    tracker.start()
    try:
        yield tracker
    finally:
        tracker.stop()


def should_show_progress(estimated_duration: float, threshold: float = 3.0) -> bool:
    """
    進捗表示が必要かどうかを判定 (CLAUDE.md準拠: 3秒以上)
    
    Args:
        estimated_duration: 推定実行時間（秒）
        threshold: 進捗表示閾値（秒）
        
    Returns:
        bool: 進捗表示が必要な場合True
    """
    return estimated_duration >= threshold


class ProgressAggregator:
    """
    複数の進捗を集約するクラス
    """
    
    def __init__(
        self,
        callback: Optional[Callable[[ProgressInfo], None]] = None,
        description: str = "全体進捗"
    ):
        """
        進捗集約を初期化
        
        Args:
            callback: 進捗コールバック
            description: 処理説明
        """
        self.callback = callback
        self.description = description
        self.trackers: List[ProgressTracker] = []
        self.weights: List[float] = []
        self.start_time = datetime.now()
    
    def add_tracker(self, tracker: ProgressTracker, weight: float = 1.0) -> None:
        """
        進捗追跡を追加
        
        Args:
            tracker: 進捗追跡オブジェクト
            weight: 重み
        """
        self.trackers.append(tracker)
        self.weights.append(weight)
        
        # 元のコールバックを置き換え
        original_callback = tracker.callback
        tracker.callback = lambda progress: self._on_sub_progress(tracker, progress, original_callback)
    
    def _on_sub_progress(
        self,
        tracker: ProgressTracker,
        progress: ProgressInfo,
        original_callback: Optional[Callable[[ProgressInfo], None]]
    ) -> None:
        """サブ進捗更新時のコールバック"""
        # 元のコールバックを実行
        if original_callback:
            original_callback(progress)
        
        # 全体進捗を計算して通知
        self._notify_aggregate_progress()
    
    def _notify_aggregate_progress(self) -> None:
        """集約進捗を通知"""
        if not self.trackers or not self.callback:
            return
        
        total_weight = sum(self.weights)
        if total_weight <= 0:
            return
        
        # 重み付き平均進捗を計算
        weighted_progress = 0.0
        for tracker, weight in zip(self.trackers, self.weights):
            progress_rate = tracker.current / max(tracker.total, 1)
            weighted_progress += (progress_rate * weight) / total_weight
        
        # 集約進捗情報を作成
        aggregate_current = int(weighted_progress * 100)
        aggregate_info = ProgressInfo(
            current=aggregate_current,
            total=100,
            message=self.description,
            start_time=self.start_time
        )
        
        self.callback(aggregate_info)


# 便利関数
def create_progress_callback(
    update_func: Callable[[float, str], None]
) -> Callable[[ProgressInfo], None]:
    """
    進捗更新関数から進捗コールバックを作成
    
    Args:
        update_func: 進捗更新関数 (progress_rate, message)
        
    Returns:
        進捗コールバック関数
    """
    def callback(progress_info: ProgressInfo) -> None:
        update_func(progress_info.progress_rate, progress_info.message)
    
    return callback


def estimate_processing_time(item_count: int, items_per_second: float) -> float:
    """
    処理時間を推定
    
    Args:
        item_count: 処理アイテム数
        items_per_second: 1秒あたりの処理数
        
    Returns:
        推定処理時間（秒）
    """
    if items_per_second <= 0:
        return float('inf')
    
    return item_count / items_per_second