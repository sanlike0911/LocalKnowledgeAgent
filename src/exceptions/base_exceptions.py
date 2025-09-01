"""
基底例外クラス実装 (CLAUDE.md準拠)
日本語エラーメッセージとエラーコード体系を提供
"""

from typing import Dict, Any, Optional, Callable
from datetime import datetime
import logging


class LocalKnowledgeAgentError(Exception):
    """
    LocalKnowledgeAgentの基底例外クラス
    
    Attributes:
        error_code: エラーコード
        message: 日本語エラーメッセージ
        details: 詳細情報
        timestamp: エラー発生時刻
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        基底例外を初期化
        
        Args:
            message: 日本語エラーメッセージ
            error_code: エラーコード
            details: 詳細情報
            cause: 原因となった例外
        """
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.cause = cause
        self.timestamp = datetime.now()
        
        # ログ出力
        self._log_error()
    
    def _log_error(self) -> None:
        """エラーをログに出力"""
        logger = logging.getLogger(self.__class__.__module__)
        logger.error(
            f"[{self.error_code}] {self.message}",
            extra={
                "error_code": self.error_code,
                "error_class": self.__class__.__name__,
                "details": self.details,
                "timestamp": self.timestamp.isoformat()
            }
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        例外を辞書形式に変換
        
        Returns:
            Dict[str, Any]: 例外情報の辞書
        """
        return {
            "error_code": self.error_code,
            "error_class": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "cause": str(self.cause) if self.cause else None
        }
    
    def __str__(self) -> str:
        """文字列表現"""
        return f"[{self.error_code}] {self.message}"
    
    def __repr__(self) -> str:
        """詳細文字列表現"""
        return (
            f"{self.__class__.__name__}("
            f"error_code='{self.error_code}', "
            f"message='{self.message}', "
            f"timestamp='{self.timestamp.isoformat()}')"
        )


class IndexingError(LocalKnowledgeAgentError):
    """
    インデックス処理関連のエラー
    
    インデックスの作成、更新、削除、検索に関するエラー
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "IDX_ERROR",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message, error_code, details, cause)


class QAError(LocalKnowledgeAgentError):
    """
    質問応答処理関連のエラー
    
    質問の処理、回答の生成、LLM連携に関するエラー
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "QA_ERROR", 
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message, error_code, details, cause)


class ConfigError(LocalKnowledgeAgentError):
    """
    設定関連のエラー
    
    設定の読み込み、保存、検証に関するエラー
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "CFG_ERROR",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message, error_code, details, cause)


# 具体的なエラータイプ

class IndexingConnectionError(IndexingError):
    """インデックスデータベース接続エラー"""
    
    def __init__(self, message: str = "インデックスデータベースに接続できません", **kwargs: Any) -> None:
        super().__init__(message, error_code="IDX_CONNECTION", **kwargs)


class IndexingValidationError(IndexingError):
    """インデックス検証エラー"""
    
    def __init__(self, message: str = "インデックスデータの検証に失敗しました", **kwargs: Any) -> None:
        super().__init__(message, error_code="IDX_VALIDATION", **kwargs)


class DocumentNotFoundError(IndexingError):
    """文書が見つからないエラー"""
    
    def __init__(self, document_id: str, **kwargs: Any) -> None:
        message = f"文書が見つかりません (ID: {document_id})"
        details = {"document_id": document_id}
        super().__init__(message, error_code="IDX_DOC_NOT_FOUND", details=details, **kwargs)


class QAModelError(QAError):
    """QAモデル関連エラー"""
    
    def __init__(self, message: str = "質問応答モデルでエラーが発生しました", **kwargs: Any) -> None:
        super().__init__(message, error_code="QA_MODEL", **kwargs)


class QATimeoutError(QAError):
    """QA処理タイムアウトエラー"""
    
    def __init__(self, timeout_seconds: int, **kwargs: Any) -> None:
        message = f"質問応答処理がタイムアウトしました ({timeout_seconds}秒)"
        details = {"timeout_seconds": timeout_seconds}
        super().__init__(message, error_code="QA_TIMEOUT", details=details, **kwargs)


class QAValidationError(QAError):
    """QA入力検証エラー"""
    
    def __init__(self, message: str = "質問の入力内容が無効です", **kwargs: Any) -> None:
        super().__init__(message, error_code="QA_VALIDATION", **kwargs)


class ConfigValidationError(ConfigError):
    """設定検証エラー"""
    
    def __init__(self, message: str = "設定データの検証に失敗しました", **kwargs: Any) -> None:
        super().__init__(message, error_code="CFG_VALIDATION", **kwargs)


class ConfigFileError(ConfigError):
    """設定ファイル関連エラー"""
    
    def __init__(self, file_path: str, operation: str = "読み込み", **kwargs: Any) -> None:
        message = f"設定ファイルの{operation}に失敗しました: {file_path}"
        details = {"file_path": file_path, "operation": operation}
        super().__init__(message, error_code="CFG_FILE", details=details, **kwargs)


class ConfigMigrationError(ConfigError):
    """設定マイグレーションエラー"""
    
    def __init__(self, from_version: str, to_version: str, **kwargs: Any) -> None:
        message = f"設定のマイグレーションに失敗しました (v{from_version} → v{to_version})"
        details = {"from_version": from_version, "to_version": to_version}
        super().__init__(message, error_code="CFG_MIGRATION", details=details, **kwargs)


# エラーコード定数
class ErrorCodes:
    """エラーコード定数クラス"""
    
    # 基底エラー
    UNKNOWN = "UNKNOWN"
    
    # インデックス関連
    IDX_ERROR = "IDX_ERROR"
    IDX_CONNECTION = "IDX_CONNECTION"
    IDX_VALIDATION = "IDX_VALIDATION"
    IDX_DOC_NOT_FOUND = "IDX_DOC_NOT_FOUND"
    IDX_SEARCH_FAILED = "IDX_SEARCH_FAILED"
    IDX_CREATE_FAILED = "IDX_CREATE_FAILED"
    IDX_UPDATE_FAILED = "IDX_UPDATE_FAILED"
    IDX_DELETE_FAILED = "IDX_DELETE_FAILED"
    
    # QA関連
    QA_ERROR = "QA_ERROR"
    QA_MODEL = "QA_MODEL"
    QA_TIMEOUT = "QA_TIMEOUT"
    QA_VALIDATION = "QA_VALIDATION"
    QA_GENERATION_FAILED = "QA_GENERATION_FAILED"
    QA_CONTEXT_ERROR = "QA_CONTEXT_ERROR"
    
    # 設定関連
    CFG_ERROR = "CFG_ERROR"
    CFG_VALIDATION = "CFG_VALIDATION"
    CFG_FILE = "CFG_FILE"
    CFG_MIGRATION = "CFG_MIGRATION"
    CFG_BACKUP_FAILED = "CFG_BACKUP_FAILED"
    CFG_RESTORE_FAILED = "CFG_RESTORE_FAILED"


# エラーメッセージテンプレート
class ErrorMessages:
    """日本語エラーメッセージテンプレートクラス"""
    
    # インデックス関連
    IDX_CONNECTION_FAILED = "インデックスデータベースに接続できません。データベースサーバーの状態を確認してください。"
    IDX_DOCUMENT_NOT_FOUND = "指定された文書が見つかりません。文書IDを確認してください。"
    IDX_SEARCH_NO_RESULTS = "検索条件に一致する文書が見つかりませんでした。検索キーワードを変更してお試しください。"
    IDX_CREATE_PERMISSION_DENIED = "インデックスを作成する権限がありません。管理者に問い合わせください。"
    
    # QA関連
    QA_MODEL_UNAVAILABLE = "質問応答モデルが利用できません。しばらく時間をおいてからお試しください。"
    QA_QUESTION_TOO_LONG = "質問が長すぎます。1000文字以内で入力してください。"
    QA_QUESTION_EMPTY = "質問を入力してください。"
    QA_GENERATION_TIMEOUT = "回答の生成に時間がかかりすぎています。質問を簡潔にしてお試しください。"
    
    # 設定関連
    CFG_FILE_NOT_FOUND = "設定ファイルが見つかりません。デフォルト設定を使用します。"
    CFG_INVALID_FORMAT = "設定ファイルの形式が正しくありません。設定を確認してください。"
    CFG_BACKUP_SPACE_INSUFFICIENT = "バックアップを作成するディスク容量が不足しています。"
    CFG_PERMISSION_DENIED = "設定ファイルにアクセスする権限がありません。"


def create_error_handler(error_type: str = "general") -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    エラーハンドラーデコレータを作成
    
    Args:
        error_type: エラータイプ ("indexing", "qa", "config", "general")
        
    Returns:
        デコレータ関数
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except LocalKnowledgeAgentError:
                # 既に独自例外の場合は再発生
                raise
            except Exception as e:
                # その他の例外を独自例外に変換
                if error_type == "indexing":
                    raise IndexingError(
                        f"インデックス処理中にエラーが発生しました: {e}",
                        error_code="IDX_UNEXPECTED",
                        cause=e
                    )
                elif error_type == "qa":
                    raise QAError(
                        f"質問応答処理中にエラーが発生しました: {e}",
                        error_code="QA_UNEXPECTED",
                        cause=e
                    )
                elif error_type == "config":
                    raise ConfigError(
                        f"設定処理中にエラーが発生しました: {e}",
                        error_code="CFG_UNEXPECTED",
                        cause=e
                    )
                else:
                    raise LocalKnowledgeAgentError(
                        f"予期しないエラーが発生しました: {e}",
                        error_code="UNEXPECTED",
                        cause=e
                    )
        return wrapper
    return decorator