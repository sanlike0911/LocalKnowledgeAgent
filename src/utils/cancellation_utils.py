"""
キャンセル制御ユーティリティ (CLAUDE.md準拠)
長時間処理のキャンセル制御機能を提供
"""

from threading import Event, Lock
from typing import Callable, Optional, Any, Dict, Set
from datetime import datetime, timedelta
import logging
from contextlib import contextmanager
from dataclasses import dataclass
import weakref
import time


@dataclass
class CancellationToken:
    """
    キャンセルトークンクラス
    
    処理のキャンセル状態を管理
    """
    token_id: str
    created_at: datetime
    cancelled_at: Optional[datetime] = None
    reason: Optional[str] = None
    
    def __post_init__(self):
        self._cancelled = Event()
        self._callbacks: Set[Callable] = set()
        self._lock = Lock()
    
    def cancel(self, reason: Optional[str] = None) -> None:
        """
        キャンセルを実行
        
        Args:
            reason: キャンセル理由
        """
        with self._lock:
            if self._cancelled.is_set():
                return
            
            self.cancelled_at = datetime.now()
            self.reason = reason or "ユーザーによるキャンセル"
            self._cancelled.set()
            
            # コールバックを実行
            for callback in self._callbacks.copy():
                try:
                    callback(self)
                except Exception as e:
                    logger = logging.getLogger(__name__)
                    logger.warning(f"キャンセルコールバックエラー: {e}")
    
    def is_cancelled(self) -> bool:
        """キャンセル状態を確認"""
        return self._cancelled.is_set()
    
    def check_cancelled(self) -> None:
        """
        キャンセル状態をチェックし、キャンセルされていれば例外を発生
        
        Raises:
            CancellationError: キャンセルされている場合
        """
        if self.is_cancelled():
            raise CancellationError(
                f"処理がキャンセルされました: {self.reason}",
                token=self
            )
    
    def add_callback(self, callback: Callable[['CancellationToken'], None]) -> None:
        """
        キャンセル時のコールバックを追加
        
        Args:
            callback: コールバック関数
        """
        with self._lock:
            self._callbacks.add(callback)
    
    def remove_callback(self, callback: Callable[['CancellationToken'], None]) -> None:
        """
        キャンセル時のコールバックを削除
        
        Args:
            callback: コールバック関数
        """
        with self._lock:
            self._callbacks.discard(callback)
    
    def wait_for_cancellation(self, timeout: Optional[float] = None) -> bool:
        """
        キャンセルを待機
        
        Args:
            timeout: タイムアウト時間（秒）
            
        Returns:
            bool: キャンセルされた場合True
        """
        return self._cancelled.wait(timeout)


class CancellationError(Exception):
    """キャンセル関連のエラー"""
    
    def __init__(self, message: str, token: Optional[CancellationToken] = None):
        super().__init__(message)
        self.token = token
        self.cancelled_at = datetime.now()


class CancellationManager:
    """
    キャンセル管理クラス
    
    アプリケーション全体のキャンセルトークンを管理
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if not getattr(self, '_initialized', False):
            self._tokens: Dict[str, CancellationToken] = {}
            self._token_lock = Lock()
            self._logger = logging.getLogger(__name__)
            self._cleanup_interval = 300  # 5分
            self._last_cleanup = time.time()
            self._initialized = True
    
    def create_token(self, token_id: Optional[str] = None) -> CancellationToken:
        """
        新しいキャンセルトークンを作成
        
        Args:
            token_id: トークンID（指定しない場合は自動生成）
            
        Returns:
            CancellationToken: 作成されたトークン
        """
        if token_id is None:
            token_id = f"token_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        token = CancellationToken(
            token_id=token_id,
            created_at=datetime.now()
        )
        
        with self._token_lock:
            self._tokens[token_id] = token
        
        self._logger.debug(f"キャンセルトークンを作成: {token_id}")
        self._cleanup_if_needed()
        
        return token
    
    def get_token(self, token_id: str) -> Optional[CancellationToken]:
        """
        トークンIDでキャンセルトークンを取得
        
        Args:
            token_id: トークンID
            
        Returns:
            Optional[CancellationToken]: トークン（存在しない場合None）
        """
        with self._token_lock:
            return self._tokens.get(token_id)
    
    def cancel_token(self, token_id: str, reason: Optional[str] = None) -> bool:
        """
        指定されたトークンをキャンセル
        
        Args:
            token_id: トークンID
            reason: キャンセル理由
            
        Returns:
            bool: キャンセルに成功した場合True
        """
        token = self.get_token(token_id)
        if token:
            token.cancel(reason)
            self._logger.info(f"トークンをキャンセル: {token_id}, 理由: {reason}")
            return True
        return False
    
    def cancel_all_tokens(self, reason: Optional[str] = None) -> int:
        """
        すべてのトークンをキャンセル
        
        Args:
            reason: キャンセル理由
            
        Returns:
            int: キャンセルされたトークン数
        """
        cancelled_count = 0
        
        with self._token_lock:
            tokens = list(self._tokens.values())
        
        for token in tokens:
            if not token.is_cancelled():
                token.cancel(reason or "全体キャンセル")
                cancelled_count += 1
        
        self._logger.info(f"全トークンをキャンセル: {cancelled_count}件")
        return cancelled_count
    
    def cleanup_expired_tokens(self, max_age: timedelta = timedelta(hours=1)) -> int:
        """
        期限切れトークンをクリーンアップ
        
        Args:
            max_age: トークンの最大保持時間
            
        Returns:
            int: クリーンアップされたトークン数
        """
        cleanup_count = 0
        current_time = datetime.now()
        
        with self._token_lock:
            expired_tokens = []
            for token_id, token in self._tokens.items():
                if current_time - token.created_at > max_age:
                    expired_tokens.append(token_id)
            
            for token_id in expired_tokens:
                del self._tokens[token_id]
                cleanup_count += 1
        
        if cleanup_count > 0:
            self._logger.debug(f"期限切れトークンをクリーンアップ: {cleanup_count}件")
        
        return cleanup_count
    
    def _cleanup_if_needed(self) -> None:
        """必要に応じてクリーンアップを実行"""
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            self.cleanup_expired_tokens()
            self._last_cleanup = current_time
    
    def get_active_token_count(self) -> int:
        """アクティブなトークン数を取得"""
        with self._token_lock:
            return len([t for t in self._tokens.values() if not t.is_cancelled()])
    
    def get_token_statistics(self) -> Dict[str, Any]:
        """トークン統計情報を取得"""
        with self._token_lock:
            total_count = len(self._tokens)
            active_count = len([t for t in self._tokens.values() if not t.is_cancelled()])
            cancelled_count = total_count - active_count
        
        return {
            "total_tokens": total_count,
            "active_tokens": active_count,
            "cancelled_tokens": cancelled_count,
            "cleanup_interval": self._cleanup_interval
        }


class CancellableOperation:
    """
    キャンセル可能な操作クラス
    
    長時間処理をキャンセル可能にするためのベースクラス
    """
    
    def __init__(
        self,
        operation_name: str,
        cancellation_token: Optional[CancellationToken] = None
    ):
        """
        キャンセル可能な操作を初期化
        
        Args:
            operation_name: 操作名
            cancellation_token: キャンセルトークン
        """
        self.operation_name = operation_name
        self.token = cancellation_token or CancellationManager().create_token()
        self.start_time = datetime.now()
        self.logger = logging.getLogger(__name__)
        
        # 弱参照でself-referenceを避ける
        weak_self = weakref.ref(self)
        self.token.add_callback(lambda t: self._on_cancelled(weak_self, t))
    
    @staticmethod
    def _on_cancelled(weak_self, token: CancellationToken) -> None:
        """キャンセル時のコールバック"""
        self = weak_self()
        if self is not None:
            self._handle_cancellation(token)
    
    def _handle_cancellation(self, token: CancellationToken) -> None:
        """
        キャンセル処理（サブクラスでオーバーライド）
        
        Args:
            token: キャンセルトークン
        """
        self.logger.info(f"操作がキャンセルされました: {self.operation_name}")
    
    def check_cancellation(self) -> None:
        """
        キャンセル状態をチェック
        
        Raises:
            CancellationError: キャンセルされている場合
        """
        self.token.check_cancelled()
    
    def is_cancelled(self) -> bool:
        """キャンセル状態を確認"""
        return self.token.is_cancelled()
    
    def cancel(self, reason: Optional[str] = None) -> None:
        """操作をキャンセル"""
        self.token.cancel(reason)


@contextmanager
def cancellable_context(
    operation_name: str,
    cancellation_token: Optional[CancellationToken] = None,
    check_interval: float = 1.0
):
    """
    キャンセル可能コンテキストマネージャー
    
    Args:
        operation_name: 操作名
        cancellation_token: キャンセルトークン
        check_interval: キャンセルチェック間隔（秒）
        
    Yields:
        CancellableOperation: キャンセル可能操作オブジェクト
    """
    operation = CancellableOperation(operation_name, cancellation_token)
    
    try:
        yield operation
    except CancellationError:
        logging.getLogger(__name__).info(f"操作がキャンセルされました: {operation_name}")
        raise
    finally:
        # トークンのクリーンアップは不要（自動的に管理される）
        pass


def periodic_cancellation_check(
    operation: CancellableOperation,
    check_func: Callable[[], Any],
    check_interval: float = 0.1
) -> Any:
    """
    定期的にキャンセルをチェックしながら関数を実行
    
    Args:
        operation: キャンセル可能操作
        check_func: 実行する関数
        check_interval: チェック間隔（秒）
        
    Returns:
        関数の戻り値
        
    Raises:
        CancellationError: キャンセルされた場合
    """
    start_time = time.time()
    last_check = start_time
    
    while True:
        current_time = time.time()
        
        # 定期的なキャンセルチェック
        if current_time - last_check >= check_interval:
            operation.check_cancellation()
            last_check = current_time
        
        try:
            result = check_func()
            return result
        except StopIteration:
            # ジェネレーター等の正常終了
            break
        except CancellationError:
            raise
        except Exception:
            # その他の例外は最後にキャンセルチェックしてから再発生
            operation.check_cancellation()
            raise
        
        # 短時間待機
        time.sleep(0.01)


# グローバルインスタンス
cancellation_manager = CancellationManager()


# 便利関数
def create_cancellation_token(token_id: Optional[str] = None) -> CancellationToken:
    """キャンセルトークン作成の便利関数"""
    return cancellation_manager.create_token(token_id)


def cancel_operation(token_id: str, reason: Optional[str] = None) -> bool:
    """操作キャンセルの便利関数"""
    return cancellation_manager.cancel_token(token_id, reason)


def cancel_all_operations(reason: Optional[str] = None) -> int:
    """全操作キャンセルの便利関数"""
    return cancellation_manager.cancel_all_tokens(reason)