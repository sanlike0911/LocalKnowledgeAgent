"""
Phase 6.2 LLMモデル選択の設定保存・読み込み機能のテスト

TDD Red フェーズ: 設定保存・復元機能拡張のテストケースを作成
"""

import pytest
import tempfile
import json
from pathlib import Path
from src.logic.config_manager import ConfigManager
from src.models.config import Config
from src.exceptions.base_exceptions import ConfigError


class TestModelConfigSave:
    """LLMモデル選択設定の保存・読み込み機能のテスト"""

    @pytest.fixture
    def temp_config_file(self):
        """一時設定ファイルを返すフィクスチャ"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        yield temp_path
        # クリーンアップ
        Path(temp_path).unlink(missing_ok=True)

    @pytest.fixture
    def config_manager(self, temp_config_file):
        """ConfigManagerのインスタンスを返すフィクスチャ"""
        return ConfigManager(temp_config_file)

    def test_save_llm_model_config_success(self, config_manager, temp_config_file):
        """正常系: LLMモデル設定の保存"""
        # Arrange
        test_config = Config(
            selected_folders=["/test/folder"],
            chroma_db_path="./test_db", 
            ollama_model="llama3:8b",
            embedding_model="nomic-embed-text",
            ollama_host="http://localhost:11434",
            max_chat_history=100,
            index_status="created"
        )

        # Act
        config_manager.save_config(test_config)

        # Assert
        # ファイルが作成されていることを確認
        config_file = Path(temp_config_file)
        assert config_file.exists()
        
        # 内容を確認
        with open(temp_config_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert saved_data["ollama_model"] == "llama3:8b"
        assert saved_data["embedding_model"] == "nomic-embed-text"

    def test_load_llm_model_config_success(self, config_manager, temp_config_file):
        """正常系: LLMモデル設定の読み込み"""
        # Arrange - 設定ファイルを事前に作成
        config_data = {
            "selected_folders": ["/test/folder"],
            "chroma_db_path": "./test_db",
            "chroma_collection_name": "test_collection",
            "max_file_size_mb": 50,
            "ollama_model": "mistral:latest",
            "embedding_model": "mxbai-embed-large",
            "ollama_host": "http://localhost:11434",
            "max_chat_history": 100,
            "index_status": "created",
            "force_japanese_response": True
        }
        
        with open(temp_config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)

        # Act
        loaded_config = config_manager.load_config()

        # Assert
        assert loaded_config.ollama_model == "mistral:latest"
        assert loaded_config.embedding_model == "mxbai-embed-large"

    def test_update_llm_model_only(self, config_manager, temp_config_file):
        """正常系: LLMモデルのみ更新"""
        # Arrange - 初期設定
        initial_config = Config(
            selected_folders=["/test/folder"],
            chroma_db_path="./test_db",
            ollama_model="llama3:8b",
            embedding_model="nomic-embed-text"
        )
        config_manager.save_config(initial_config)

        # Act - LLMモデルのみ変更
        updated_config = Config(
            selected_folders=["/test/folder"],
            chroma_db_path="./test_db", 
            ollama_model="codellama:13b",  # 変更
            embedding_model="nomic-embed-text"  # 維持
        )
        config_manager.save_config(updated_config)

        # Assert
        loaded_config = config_manager.load_config()
        assert loaded_config.ollama_model == "codellama:13b"
        assert loaded_config.embedding_model == "nomic-embed-text"
        assert loaded_config.selected_folders == ["/test/folder"]

    def test_save_config_with_validation(self, config_manager):
        """正常系: 設定保存時のバリデーション"""
        # Arrange
        valid_config = Config(
            selected_folders=["/valid/folder"],
            chroma_db_path="./valid_db",
            ollama_model="llama3:8b",
            embedding_model="nomic-embed-text"
        )

        # Act & Assert - 例外が発生しないことを確認
        config_manager.save_config(valid_config)
        loaded_config = config_manager.load_config()
        assert loaded_config.ollama_model == "llama3:8b"

    def test_load_config_with_missing_model_fields_raises_error(self, config_manager, temp_config_file):
        """境界値テスト: 必須モデルフィールドが不足している場合はエラーが発生する"""
        # Arrange - ollama_modelフィールドが不足した設定
        incomplete_config_data = {
            "selected_folders": ["/test/folder"],
            "chroma_db_path": "./test_db",
            "chroma_collection_name": "test_collection",
            "max_file_size_mb": 50,
            # ollama_model と embedding_model が不足
            "ollama_host": "http://localhost:11434",
            "max_chat_history": 100,
            "index_status": "not_created"
        }
        
        with open(temp_config_file, 'w', encoding='utf-8') as f:
            json.dump(incomplete_config_data, f, ensure_ascii=False, indent=2)

        # Act & Assert - ConfigErrorが発生することを確認
        with pytest.raises(ConfigError) as exc_info:
            config_manager.load_config()
        
        assert "ollama_model" in str(exc_info.value)
        assert exc_info.value.error_code == "CFG-007"

    def test_save_config_preserves_other_fields(self, config_manager, temp_config_file):
        """正常系: モデル設定更新時に他のフィールドが保持される"""
        # Arrange - 複数フィールドを持つ設定
        original_config = Config(
            selected_folders=["/folder1", "/folder2"],
            chroma_db_path="./custom_db",
            ollama_model="llama3:8b",
            embedding_model="nomic-embed-text",
            max_chat_history=200,
            index_status="created"
        )
        config_manager.save_config(original_config)

        # Act - モデルのみ変更
        updated_config = Config(
            selected_folders=["/folder1", "/folder2"],  # 保持
            chroma_db_path="./custom_db",  # 保持
            ollama_model="gemma:7b",  # 変更
            embedding_model="mxbai-embed-large",  # 変更
            max_chat_history=200,  # 保持
            index_status="created"  # 保持
        )
        config_manager.save_config(updated_config)

        # Assert - 全フィールドが適切に保存・読み込みされることを確認
        loaded_config = config_manager.load_config()
        assert loaded_config.ollama_model == "gemma:7b"
        assert loaded_config.embedding_model == "mxbai-embed-large"
        assert loaded_config.selected_folders == ["/folder1", "/folder2"]
        assert loaded_config.chroma_db_path == "./custom_db"
        assert loaded_config.max_chat_history == 200
        assert loaded_config.index_status == "created"

    def test_config_file_creation_on_first_save(self, temp_config_file):
        """正常系: 初回保存時の設定ファイル作成"""
        # Arrange - 存在しないファイルパス
        non_existent_file = temp_config_file + "_new"
        config_manager = ConfigManager(non_existent_file)
        
        # Act
        test_config = Config(
            selected_folders=["/new/folder"],
            ollama_model="llama3:8b",
            embedding_model="nomic-embed-text"
        )
        config_manager.save_config(test_config)

        # Assert
        config_file = Path(non_existent_file)
        assert config_file.exists()
        
        loaded_config = config_manager.load_config()
        assert loaded_config.ollama_model == "llama3:8b"
        
        # クリーンアップ
        config_file.unlink(missing_ok=True)