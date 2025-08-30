"""
構造化ログ実装 (JSON形式) - CLAUDE.md準拠
アプリケーション全体で使用する構造化ログ機能を提供
"""

import json
import logging
import logging.handlers
from datetime import datetime
from typing import Dict, Any, Optional, Union
from pathlib import Path
import sys
import os


class StructuredFormatter(logging.Formatter):
    """
    構造化ログ用のカスタムフォーマッター
    JSON形式でログを出力
    """
    
    def __init__(self, include_extra: bool = True):
        """
        構造化フォーマッターを初期化
        
        Args:
            include_extra: 追加情報を含めるかどうか
        """
        super().__init__()
        self.include_extra = include_extra
        self.hostname = os.uname().nodename if hasattr(os, 'uname') else 'unknown'
        
    def format(self, record: logging.LogRecord) -> str:
        """
        ログレコードをJSON形式にフォーマット
        
        Args:
            record: ログレコード
            
        Returns:
            str: JSON形式のログ文字列
        """
        # 基本ログ情報
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "hostname": self.hostname,
            "process_id": record.process,
            "thread_id": record.thread
        }
        
        # 例外情報がある場合
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info) if record.exc_info else None
            }
        
        # 追加情報を含める場合
        if self.include_extra:
            # レコードから標準属性以外を抽出
            standard_attrs = {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
                'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName',
                'created', 'msecs', 'relativeCreated', 'thread', 'threadName',
                'processName', 'process', 'message'
            }
            
            extra_data = {}
            for key, value in record.__dict__.items():
                if key not in standard_attrs and not key.startswith('_'):
                    try:
                        # JSON serializable かチェック
                        json.dumps(value)
                        extra_data[key] = value
                    except (TypeError, ValueError):
                        extra_data[key] = str(value)
            
            if extra_data:
                log_entry["extra"] = extra_data
        
        return json.dumps(log_entry, ensure_ascii=False)


class StructuredLogger:
    """
    構造化ログ管理クラス
    
    アプリケーション全体で使用する構造化ログを管理
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not StructuredLogger._initialized:
            self.log_directory = Path("./logs")
            self.log_file = self.log_directory / "app.log"
            self.error_log_file = self.log_directory / "error.log"
            self.max_bytes = 10 * 1024 * 1024  # 10MB
            self.backup_count = 5
            self.setup_logging()
            StructuredLogger._initialized = True
    
    def setup_logging(self) -> None:
        """ログ設定を初期化"""
        # ログディレクトリを作成
        self.log_directory.mkdir(parents=True, exist_ok=True)
        
        # ルートロガーの設定
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # 既存のハンドラーをクリア
        root_logger.handlers.clear()
        
        # コンソールハンドラー
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = StructuredFormatter(include_extra=False)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # ファイルハンドラー（全ログ）
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = StructuredFormatter(include_extra=True)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # エラーログハンドラー
        error_handler = logging.handlers.RotatingFileHandler(
            self.error_log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_handler)
        
        # 初期化完了ログ
        logging.info("構造化ログシステムが初期化されました", extra={
            "log_directory": str(self.log_directory),
            "log_file": str(self.log_file),
            "error_log_file": str(self.error_log_file)
        })
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        指定された名前のロガーを取得
        
        Args:
            name: ロガー名
            
        Returns:
            logging.Logger: 構造化ログ対応ロガー
        """
        return logging.getLogger(name)
    
    def log_performance(
        self,
        operation: str,
        duration: float,
        details: Optional[Dict[str, Any]] = None,
        logger_name: str = "performance"
    ) -> None:
        """
        パフォーマンス情報をログ出力
        
        Args:
            operation: 操作名
            duration: 実行時間（秒）
            details: 詳細情報
            logger_name: ロガー名
        """
        logger = self.get_logger(logger_name)
        
        perf_data = {
            "operation": operation,
            "duration_seconds": round(duration, 3),
            "performance_category": "timing"
        }
        
        if details:
            perf_data.update(details)
        
        logger.info(f"パフォーマンス測定: {operation} ({duration:.3f}s)", extra=perf_data)
    
    def log_user_action(
        self,
        action: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        logger_name: str = "user_action"
    ) -> None:
        """
        ユーザーアクションをログ出力
        
        Args:
            action: アクション名
            user_id: ユーザーID
            details: 詳細情報
            logger_name: ロガー名
        """
        logger = self.get_logger(logger_name)
        
        action_data = {
            "action": action,
            "user_id": user_id or "anonymous",
            "action_category": "user_interaction"
        }
        
        if details:
            action_data.update(details)
        
        logger.info(f"ユーザーアクション: {action}", extra=action_data)
    
    def log_system_event(
        self,
        event: str,
        event_type: str = "system",
        details: Optional[Dict[str, Any]] = None,
        logger_name: str = "system"
    ) -> None:
        """
        システムイベントをログ出力
        
        Args:
            event: イベント名
            event_type: イベントタイプ
            details: 詳細情報
            logger_name: ロガー名
        """
        logger = self.get_logger(logger_name)
        
        event_data = {
            "event": event,
            "event_type": event_type,
            "system_category": "event"
        }
        
        if details:
            event_data.update(details)
        
        logger.info(f"システムイベント: {event}", extra=event_data)
    
    def log_error_with_context(
        self,
        error: Exception,
        context: Dict[str, Any],
        logger_name: str = "error"
    ) -> None:
        """
        コンテキスト情報付きでエラーをログ出力
        
        Args:
            error: 例外オブジェクト
            context: コンテキスト情報
            logger_name: ロガー名
        """
        logger = self.get_logger(logger_name)
        
        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "error_category": "application_error"
        }
        
        logger.error(f"エラーが発生しました: {error}", extra=error_data, exc_info=True)
    
    def configure_level(self, level: Union[str, int]) -> None:
        """
        ログレベルを設定
        
        Args:
            level: ログレベル
        """
        if isinstance(level, str):
            level = getattr(logging, level.upper())
        
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        logging.info(f"ログレベルを {logging.getLevelName(level)} に設定しました", extra={
            "log_level": logging.getLevelName(level),
            "configuration_change": True
        })
    
    def add_file_handler(self, file_path: str, level: int = logging.INFO) -> None:
        """
        追加のファイルハンドラーを追加
        
        Args:
            file_path: ログファイルパス
            level: ログレベル
        """
        file_handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        formatter = StructuredFormatter(include_extra=True)
        file_handler.setFormatter(formatter)
        
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        
        logging.info(f"追加ファイルハンドラーを設定しました: {file_path}", extra={
            "file_path": file_path,
            "log_level": logging.getLevelName(level),
            "handler_addition": True
        })
    
    def get_log_stats(self) -> Dict[str, Any]:
        """
        ログ統計情報を取得
        
        Returns:
            Dict[str, Any]: ログ統計情報
        """
        stats = {
            "log_directory": str(self.log_directory),
            "handlers": [],
            "log_files": []
        }
        
        # ハンドラー情報
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            handler_info = {
                "type": type(handler).__name__,
                "level": logging.getLevelName(handler.level)
            }
            
            if hasattr(handler, 'baseFilename'):
                handler_info["file"] = handler.baseFilename
                
            stats["handlers"].append(handler_info)
        
        # ログファイル情報
        for log_file in self.log_directory.glob("*.log*"):
            if log_file.is_file():
                stats["log_files"].append({
                    "file": str(log_file),
                    "size": log_file.stat().st_size,
                    "modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
                })
        
        return stats


# グローバルインスタンス
structured_logger = StructuredLogger()


# 便利関数
def get_logger(name: str) -> logging.Logger:
    """構造化ロガーを取得する便利関数"""
    return structured_logger.get_logger(name)


def log_performance(operation: str, duration: float, **kwargs) -> None:
    """パフォーマンスログの便利関数"""
    structured_logger.log_performance(operation, duration, **kwargs)


def log_user_action(action: str, **kwargs) -> None:
    """ユーザーアクションログの便利関数"""
    structured_logger.log_user_action(action, **kwargs)


def log_system_event(event: str, **kwargs) -> None:
    """システムイベントログの便利関数"""
    structured_logger.log_system_event(event, **kwargs)


def log_error_with_context(error: Exception, context: Dict[str, Any], **kwargs) -> None:
    """コンテキスト付きエラーログの便利関数"""
    structured_logger.log_error_with_context(error, context, **kwargs)