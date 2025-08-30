"""
環境変数バリデーション機能モジュール
CLAUDE.md 準拠の設定値安全読み込み機能を提供
"""

import logging
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv


class EnvironmentError(Exception):
    """環境変数関連のエラー"""

    pass


class EnvironmentValidator:
    """環境変数バリデーションクラス"""

    def __init__(self, env_file: str = ".env"):
        """
        環境変数バリデーターを初期化

        Args:
            env_file: 環境変数ファイルのパス
        """
        self.env_file = env_file
        self._load_environment()

    def _load_environment(self) -> None:
        """環境変数ファイルを読み込み"""
        if os.path.exists(self.env_file):
            load_dotenv(self.env_file)
            logging.info(f"環境変数ファイル {self.env_file} を読み込みました")
        else:
            logging.warning(f"環境変数ファイル {self.env_file} が見つかりません")

    def get_required_env(self, key: str, default: Optional[str] = None) -> str:
        """
        必須環境変数を取得

        Args:
            key: 環境変数名
            default: デフォルト値

        Returns:
            環境変数の値

        Raises:
            EnvironmentError: 必須環境変数が設定されていない場合
        """
        value = os.getenv(key, default)
        if value is None:
            raise EnvironmentError(f"必須環境変数 {key} が設定されていません")
        return value

    def get_optional_env(self, key: str, default: str = "") -> str:
        """
        オプション環境変数を取得

        Args:
            key: 環境変数名
            default: デフォルト値

        Returns:
            環境変数の値またはデフォルト値
        """
        return os.getenv(key, default)

    def get_bool_env(self, key: str, default: bool = False) -> bool:
        """
        boolean型環境変数を取得

        Args:
            key: 環境変数名
            default: デフォルト値

        Returns:
            boolean値
        """
        value = os.getenv(key, str(default)).lower()
        return value in ("true", "1", "yes", "on")

    def get_int_env(self, key: str, default: int = 0) -> int:
        """
        整数型環境変数を取得

        Args:
            key: 環境変数名
            default: デフォルト値

        Returns:
            整数値

        Raises:
            EnvironmentError: 値が整数に変換できない場合
        """
        value = os.getenv(key, str(default))
        try:
            return int(value)
        except ValueError:
            raise EnvironmentError(f"環境変数 {key} の値 '{value}' は整数ではありません")

    def validate_configuration(self) -> Dict[str, Any]:
        """
        アプリケーション設定を検証して取得

        Returns:
            検証済み設定辞書
        """
        config = {
            # Ollama設定
            "ollama_host": self.get_optional_env(
                "OLLAMA_HOST", "http://localhost:11434"
            ),
            "ollama_model": self.get_optional_env("OLLAMA_MODEL", "llama2"),
            # ChromaDB設定
            "chroma_db_path": self.get_optional_env(
                "CHROMA_DB_PATH", "./data/chroma_db"
            ),
            "chroma_collection_name": self.get_optional_env(
                "CHROMA_COLLECTION_NAME", "knowledge_base"
            ),
            # ドキュメント処理設定
            "max_file_size_mb": self.get_int_env("MAX_FILE_SIZE_MB", 50),
            "supported_extensions": self.get_optional_env(
                "SUPPORTED_EXTENSIONS", ".pdf,.txt,.docx"
            ).split(","),
            # アプリケーション設定
            "app_debug": self.get_bool_env("APP_DEBUG", False),
            "log_level": self.get_optional_env("LOG_LEVEL", "INFO"),
            "max_chat_history": self.get_int_env("MAX_CHAT_HISTORY", 50),
            # Streamlit設定
            "streamlit_server_port": self.get_int_env("STREAMLIT_SERVER_PORT", 8501),
            "streamlit_server_address": self.get_optional_env(
                "STREAMLIT_SERVER_ADDRESS", "localhost"
            ),
            # セキュリティ設定
            "upload_folder": self.get_optional_env("UPLOAD_FOLDER", "./uploads"),
            "temp_folder": self.get_optional_env("TEMP_FOLDER", "./temp"),
        }

        # パス検証
        self._validate_paths(config)

        return config

    def _validate_paths(self, config: Dict[str, Any]) -> None:
        """
        パス設定を検証

        Args:
            config: 設定辞書

        Raises:
            EnvironmentError: パス設定が不正な場合
        """
        path_keys = ["chroma_db_path", "upload_folder", "temp_folder"]

        for key in path_keys:
            path = config[key]
            # 相対パスの場合は絶対パスに変換
            if not os.path.isabs(path):
                config[key] = os.path.abspath(path)

            # ディレクトリが存在しない場合は作成
            os.makedirs(config[key], exist_ok=True)
            logging.info(f"ディレクトリ設定確認: {key} = {config[key]}")


def get_app_config() -> Dict[str, Any]:
    """
    アプリケーション設定を取得する便利関数

    Returns:
        検証済み設定辞書
    """
    validator = EnvironmentValidator()
    return validator.validate_configuration()
