"""
Configモデルのテストケース (TDD Red フェーズ)
CLAUDE.md準拠のTDD実装手順に従う
"""

import json
import tempfile
from pathlib import Path


import pytest


class TestConfigModel:
    """Configモデルのテストクラス"""

    def test_config_creation_with_default_values(self) -> None:
        """デフォルト値でConfigインスタンスが作成できることをテスト"""
        from src.models.config import Config

        config = Config()

        assert config.ollama_host == "http://localhost:11434"
        assert config.ollama_model == "llama2"
        assert config.chroma_db_path == "./data/chroma_db"
        assert config.chroma_collection_name == "knowledge_base"
        assert config.max_chat_history == 50
        assert config.max_file_size_mb == 50
        assert isinstance(config.supported_extensions, list)
        assert ".pdf" in config.supported_extensions
        assert ".txt" in config.supported_extensions
        assert ".docx" in config.supported_extensions

    def test_config_creation_with_custom_values(self) -> None:
        """カスタム値でConfigインスタンスが作成できることをテスト"""
        from src.models.config import Config

        config = Config(
            ollama_host="http://custom-host:11434",
            ollama_model="custom-model",
            chroma_db_path="/custom/path/db",
            chroma_collection_name="custom_collection",
            max_chat_history=100,
            max_file_size_mb=100,
            supported_extensions=[".pdf", ".txt"],
            selected_folders=["/path/to/docs"],
        )

        assert config.ollama_host == "http://custom-host:11434"
        assert config.ollama_model == "custom-model"
        assert config.chroma_db_path == "/custom/path/db"
        assert config.chroma_collection_name == "custom_collection"
        assert config.max_chat_history == 100
        assert config.max_file_size_mb == 100
        assert config.supported_extensions == [".pdf", ".txt"]
        assert config.selected_folders == ["/path/to/docs"]

    def test_config_validation_invalid_max_chat_history(self) -> None:
        """無効なmax_chat_historyでエラーが発生することをテスト"""
        from src.models.config import Config, ConfigValidationError

        with pytest.raises(
            ConfigValidationError, match="max_chat_historyは1以上である必要があります"
        ):
            Config(max_chat_history=0)

        with pytest.raises(
            ConfigValidationError, match="max_chat_historyは1以上である必要があります"
        ):
            Config(max_chat_history=-10)

    def test_config_validation_invalid_max_file_size(self) -> None:
        """無効なmax_file_size_mbでエラーが発生することをテスト"""
        from src.models.config import Config, ConfigValidationError

        with pytest.raises(
            ConfigValidationError, match="max_file_size_mbは1以上である必要があります"
        ):
            Config(max_file_size_mb=0)

        with pytest.raises(
            ConfigValidationError, match="max_file_size_mbは1以上である必要があります"
        ):
            Config(max_file_size_mb=-5)

    def test_config_validation_empty_ollama_host(self) -> None:
        """空のollama_hostでエラーが発生することをテスト"""
        from src.models.config import Config, ConfigValidationError

        with pytest.raises(ConfigValidationError, match="ollama_hostは必須です"):
            Config(ollama_host="")

        with pytest.raises(ConfigValidationError, match="ollama_hostは必須です"):
            Config(ollama_host="   ")

    def test_config_validation_empty_ollama_model(self) -> None:
        """空のollama_modelでエラーが発生することをテスト"""
        from src.models.config import Config, ConfigValidationError

        with pytest.raises(ConfigValidationError, match="ollama_modelは必須です"):
            Config(ollama_model="")

    def test_config_to_dict(self) -> None:
        """Configオブジェクトが辞書形式に変換できることをテスト"""
        from src.models.config import Config

        config = Config(
            ollama_host="http://localhost:11434",
            ollama_model="llama2",
            selected_folders=["/path/to/docs"],
        )

        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert config_dict["ollama_host"] == "http://localhost:11434"
        assert config_dict["ollama_model"] == "llama2"
        assert config_dict["selected_folders"] == ["/path/to/docs"]
        assert "chroma_db_path" in config_dict
        assert "max_chat_history" in config_dict

    def test_config_from_dict(self) -> None:
        """辞書からConfigオブジェクトが作成できることをテスト"""
        from src.models.config import Config

        config_data = {
            "ollama_host": "http://custom:11434",
            "ollama_model": "custom-model",
            "chroma_db_path": "/custom/path",
            "chroma_collection_name": "custom_collection",
            "max_chat_history": 75,
            "max_file_size_mb": 25,
            "supported_extensions": [".pdf", ".txt"],
            "selected_folders": ["/docs"],
            "index_status": "created",
        }

        config = Config.from_dict(config_data)

        assert config.ollama_host == "http://custom:11434"
        assert config.ollama_model == "custom-model"
        assert config.chroma_db_path == "/custom/path"
        assert config.max_chat_history == 75
        assert config.selected_folders == ["/docs"]
        assert config.index_status == "created"

    def test_config_save_to_file(self) -> None:
        """設定をファイルに保存できることをテスト"""
        from src.models.config import Config

        config = Config(
            ollama_host="http://test:11434", selected_folders=["/test/path"]
        )

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_file = f.name

        try:
            config.save_to_file(temp_file)

            # ファイルが作成されたことを確認
            assert Path(temp_file).exists()

            # ファイル内容を確認
            with open(temp_file, "r", encoding="utf-8") as f:
                saved_data = json.load(f)

            assert saved_data["ollama_host"] == "http://test:11434"
            assert saved_data["selected_folders"] == ["/test/path"]

        finally:
            # クリーンアップ
            Path(temp_file).unlink(missing_ok=True)

    def test_config_load_from_file(self) -> None:
        """ファイルから設定を読み込めることをテスト"""
        from src.models.config import Config

        config_data = {
            "ollama_host": "http://loaded:11434",
            "ollama_model": "loaded-model",
            "selected_folders": ["/loaded/path"],
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            config = Config.load_from_file(temp_file)

            assert config.ollama_host == "http://loaded:11434"
            assert config.ollama_model == "loaded-model"
            assert config.selected_folders == ["/loaded/path"]

        finally:
            # クリーンアップ
            Path(temp_file).unlink(missing_ok=True)

    def test_config_load_from_nonexistent_file(self) -> None:
        """存在しないファイルから読み込み時にエラーが発生することをテスト"""
        from src.models.config import Config, ConfigError

        with pytest.raises(ConfigError, match="設定ファイルが見つかりません"):
            Config.load_from_file("/nonexistent/path/config.json")

    def test_config_add_selected_folder(self) -> None:
        """選択フォルダの追加が正しく動作することをテスト"""
        from src.models.config import Config

        config = Config()

        config.add_selected_folder("/new/folder")

        assert "/new/folder" in config.selected_folders

    def test_config_add_duplicate_folder(self) -> None:
        """重複フォルダの追加時に重複しないことをテスト"""
        from src.models.config import Config

        config = Config(selected_folders=["/existing/folder"])

        config.add_selected_folder("/existing/folder")

        # 重複しないことを確認
        folder_count = config.selected_folders.count("/existing/folder")
        assert folder_count == 1

    def test_config_remove_selected_folder(self) -> None:
        """選択フォルダの削除が正しく動作することをテスト"""
        from src.models.config import Config

        config = Config(selected_folders=["/folder1", "/folder2"])

        config.remove_selected_folder("/folder1")

        assert "/folder1" not in config.selected_folders
        assert "/folder2" in config.selected_folders

    def test_config_clear_selected_folders(self) -> None:
        """選択フォルダの全削除が正しく動作することをテスト"""
        from src.models.config import Config

        config = Config(selected_folders=["/folder1", "/folder2"])

        config.clear_selected_folders()

        assert len(config.selected_folders) == 0

    def test_config_is_extension_supported(self) -> None:
        """拡張子サポート判定が正しく動作することをテスト"""
        from src.models.config import Config

        config = Config(supported_extensions=[".pdf", ".txt"])

        assert config.is_extension_supported(".pdf") is True
        assert config.is_extension_supported("pdf") is True
        assert config.is_extension_supported(".PDF") is True
        assert config.is_extension_supported(".docx") is False
        assert config.is_extension_supported("exe") is False

    def test_config_get_max_file_size_bytes(self) -> None:
        """最大ファイルサイズのバイト変換が正しく動作することをテスト"""
        from src.models.config import Config

        config = Config(max_file_size_mb=10)

        expected_bytes = 10 * 1024 * 1024  # 10MB in bytes
        assert config.get_max_file_size_bytes() == expected_bytes
