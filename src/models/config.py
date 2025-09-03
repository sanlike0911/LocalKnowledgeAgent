"""
Configモデル実装 (TDD Green フェーズ)
設計書準拠の設定管理モデルクラス
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


class ConfigError(Exception):
    """設定関連のエラー"""

    pass


class ConfigValidationError(ConfigError):
    """設定データ検証エラー"""

    pass


@dataclass
class Config:
    """
    アプリケーション設定モデルクラス

    Attributes:
        ollama_host: Ollamaサーバーホスト
        ollama_model: 使用するOllamaモデル名
        embedding_model: 埋め込み（ベクトル変換）用モデル名
        chroma_db_path: ChromaDBのデータベースパス
        chroma_collection_name: ChromaDBコレクション名
        max_chat_history: 最大チャット履歴数
        max_file_size_mb: 最大ファイルサイズ (MB)
        supported_extensions: サポート拡張子リスト
        selected_folders: 選択されたフォルダパスリスト
        index_status: インデックス状態
        app_debug: デバッグモード
        log_level: ログレベル
        upload_folder: アップロードフォルダパス
        temp_folder: 一時フォルダパス
        force_japanese_response: 日本語固定回答制御フラグ
    """

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3:8b"
    embedding_model: str = "nomic-embed-text"
    chroma_db_path: str = "./data/chroma_db"
    chroma_collection_name: str = "knowledge_base"
    max_chat_history: int = 50
    max_file_size_mb: int = 50
    supported_extensions: List[str] = field(
        default_factory=lambda: [".pdf", ".txt", ".md"]
    )
    selected_folders: List[str] = field(default_factory=list)
    index_status: str = "not_created"  # 'not_created', 'creating', 'created', 'error'
    app_debug: bool = False
    log_level: str = "INFO"
    upload_folder: str = "./uploads"
    temp_folder: str = "./temp"
    force_japanese_response: bool = True  # 日本語固定回答制御
    supported_embedding_models: List[str] = field(
        default_factory=lambda: ["nomic-embed-text", "mxbai-embed-large", "all-minilm", "snowflake-arctic-embed"]
    )

    def __post_init__(self) -> None:
        """データクラス初期化後の検証処理"""
        self._validate()

    def _validate(self) -> None:
        """設定データの検証"""
        if not self.ollama_host or not self.ollama_host.strip():
            raise ConfigValidationError("ollama_hostは必須です")

        if not self.ollama_model or not self.ollama_model.strip():
            raise ConfigValidationError("ollama_modelは必須です")

        if not self.embedding_model or not self.embedding_model.strip():
            raise ConfigValidationError("embedding_modelは必須です")

        if self.max_chat_history <= 0:
            raise ConfigValidationError("max_chat_historyは1以上である必要があります")

        if self.max_file_size_mb <= 0:
            raise ConfigValidationError("max_file_size_mbは1以上である必要があります")

        if not self.chroma_collection_name or not self.chroma_collection_name.strip():
            raise ConfigValidationError("chroma_collection_nameは必須です")

        # インデックス状態の検証
        valid_statuses = {"not_created", "creating", "created", "error"}
        if self.index_status not in valid_statuses:
            raise ConfigValidationError(
                f"無効なindex_status: {self.index_status}. "
                f"有効な値: {', '.join(valid_statuses)}"
            )

        # ログレベルの検証
        valid_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid_log_levels:
            raise ConfigValidationError(
                f"無効なlog_level: {self.log_level}. "
                f"有効な値: {', '.join(valid_log_levels)}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """
        設定オブジェクトを辞書形式に変換

        Returns:
            Dict[str, Any]: 設定データの辞書
        """
        return {
            "ollama_host": self.ollama_host,
            "ollama_model": self.ollama_model,
            "embedding_model": self.embedding_model,
            "chroma_db_path": self.chroma_db_path,
            "chroma_collection_name": self.chroma_collection_name,
            "max_chat_history": self.max_chat_history,
            "max_file_size_mb": self.max_file_size_mb,
            "supported_extensions": self.supported_extensions.copy(),
            "selected_folders": self.selected_folders.copy(),
            "index_status": self.index_status,
            "app_debug": self.app_debug,
            "log_level": self.log_level,
            "upload_folder": self.upload_folder,
            "temp_folder": self.temp_folder,
            "force_japanese_response": self.force_japanese_response,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """
        辞書から設定オブジェクトを作成

        Args:
            data: 設定データの辞書

        Returns:
            Config: 設定インスタンス
        """
        return cls(
            ollama_host=data.get("ollama_host", "http://localhost:11434"),
            ollama_model=data.get("ollama_model", "llama3:8b"),
            embedding_model=data.get("embedding_model", "nomic-embed-text"),
            chroma_db_path=data.get("chroma_db_path", "./data/chroma_db"),
            chroma_collection_name=data.get("chroma_collection_name", "knowledge_base"),
            max_chat_history=data.get("max_chat_history", 50),
            max_file_size_mb=data.get("max_file_size_mb", 50),
            supported_extensions=data.get(
                "supported_extensions", [".pdf", ".txt", ".md"]
            ),
            selected_folders=data.get("selected_folders", []),
            index_status=data.get("index_status", "not_created"),
            app_debug=data.get("app_debug", False),
            log_level=data.get("log_level", "INFO"),
            upload_folder=data.get("upload_folder", "./uploads"),
            temp_folder=data.get("temp_folder", "./temp"),
            force_japanese_response=data.get("force_japanese_response", True),
        )

    def save_to_file(self, file_path: str) -> None:
        """
        設定をファイルに保存

        Args:
            file_path: 保存先ファイルパス

        Raises:
            ConfigError: 保存に失敗した場合
        """
        try:
            # ディレクトリが存在しない場合は作成
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

            logging.info(f"設定を保存しました: {file_path}")

        except (OSError, TypeError) as e:
            raise ConfigError(f"設定ファイルの保存に失敗しました: {e}")

    @classmethod
    def load_from_file(cls, file_path: str) -> "Config":
        """
        ファイルから設定を読み込み

        Args:
            file_path: 設定ファイルパス

        Returns:
            Config: 読み込まれた設定インスタンス

        Raises:
            ConfigError: 読み込みに失敗した場合
        """
        if not Path(file_path).exists():
            raise ConfigError(f"設定ファイルが見つかりません: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            config = cls.from_dict(data)
            logging.info(f"設定を読み込みました: {file_path}")
            return config

        except (OSError, json.JSONDecodeError) as e:
            raise ConfigError(f"設定ファイルの読み込みに失敗しました: {e}")

    def add_selected_folder(self, folder_path: str) -> None:
        """
        選択フォルダを追加

        Args:
            folder_path: フォルダパス
        """
        if folder_path not in self.selected_folders:
            self.selected_folders.append(folder_path)
            logging.info(f"フォルダを追加しました: {folder_path}")

    def remove_selected_folder(self, folder_path: str) -> None:
        """
        選択フォルダを削除

        Args:
            folder_path: フォルダパス
        """
        if folder_path in self.selected_folders:
            self.selected_folders.remove(folder_path)
            logging.info(f"フォルダを削除しました: {folder_path}")

    def clear_selected_folders(self) -> None:
        """選択フォルダをすべてクリア"""
        self.selected_folders.clear()
        logging.info("選択フォルダをすべてクリアしました")

    def is_extension_supported(self, extension: str) -> bool:
        """
        拡張子がサポートされているかを判定

        Args:
            extension: 拡張子 (.pdf or pdf)

        Returns:
            bool: サポートされている場合True
        """
        # ドット無しの場合はドットを追加
        if not extension.startswith("."):
            extension = f".{extension}"

        return extension.lower() in [ext.lower() for ext in self.supported_extensions]

    def get_max_file_size_bytes(self) -> int:
        """
        最大ファイルサイズをバイト単位で取得

        Returns:
            int: 最大ファイルサイズ (バイト)
        """
        return self.max_file_size_mb * 1024 * 1024

    def update_index_status(self, status: str) -> None:
        """
        インデックス状態を更新

        Args:
            status: 新しいインデックス状態

        Raises:
            ConfigValidationError: 無効な状態の場合
        """
        valid_statuses = {"not_created", "creating", "created", "error"}
        if status not in valid_statuses:
            raise ConfigValidationError(
                f"無効なindex_status: {status}. " f"有効な値: {', '.join(valid_statuses)}"
            )

        self.index_status = status
        logging.info(f"インデックス状態を更新しました: {status}")

    def get_absolute_paths(self) -> Dict[str, str]:
        """
        相対パスを絶対パスに変換して取得

        Returns:
            Dict[str, str]: 絶対パスの辞書
        """
        return {
            "chroma_db_path": str(Path(self.chroma_db_path).resolve()),
            "upload_folder": str(Path(self.upload_folder).resolve()),
            "temp_folder": str(Path(self.temp_folder).resolve()),
        }

    def validate_paths(self) -> List[str]:
        """
        パス設定を検証し、問題があるパスをリストで返す

        Returns:
            List[str]: 問題があるパスのリスト
        """
        problems = []

        # 選択フォルダの存在チェック
        for folder in self.selected_folders:
            if not Path(folder).exists():
                problems.append(f"選択フォルダが存在しません: {folder}")
            elif not Path(folder).is_dir():
                problems.append(f"選択パスがディレクトリではありません: {folder}")

        return problems

    def __str__(self) -> str:
        """設定の文字列表現"""
        return (
            f"Config(ollama_model={self.ollama_model}, "
            f"folders={len(self.selected_folders)}, "
            f"status={self.index_status})"
        )

    def __repr__(self) -> str:
        """設定の詳細文字列表現"""
        return (
            f"Config(ollama_host='{self.ollama_host}', "
            f"ollama_model='{self.ollama_model}', "
            f"chroma_collection_name='{self.chroma_collection_name}', "
            f"max_chat_history={self.max_chat_history}, "
            f"selected_folders={self.selected_folders}, "
            f"index_status='{self.index_status}')"
        )
