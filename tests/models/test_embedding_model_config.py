"""
埋め込みモデル設定機能のテスト
"""

import pytest
import tempfile
import json
from pathlib import Path
from src.models.config import Config, ConfigValidationError


class TestEmbeddingModelConfig:
    """埋め込みモデル設定テスト"""
    
    def setup_method(self):
        """テスト前準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.json"
    
    def test_default_embedding_model(self):
        """デフォルト埋め込みモデルのテスト"""
        config = Config()
        assert config.embedding_model == "nomic-embed-text"
    
    def test_custom_embedding_model(self):
        """カスタム埋め込みモデル設定テスト"""
        config = Config(embedding_model="mxbai-embed-large")
        assert config.embedding_model == "mxbai-embed-large"
    
    def test_embedding_model_validation(self):
        """埋め込みモデル検証テスト"""
        # 空文字列は無効
        with pytest.raises(ConfigValidationError, match="embedding_modelは必須です"):
            Config(embedding_model="")
        
        # None は無効
        with pytest.raises(ConfigValidationError, match="embedding_modelは必須です"):
            Config(embedding_model=None)
        
        # スペースのみは無効
        with pytest.raises(ConfigValidationError, match="embedding_modelは必須です"):
            Config(embedding_model="   ")
    
    def test_config_to_dict_includes_embedding_model(self):
        """to_dictメソッドに埋め込みモデルが含まれることを確認"""
        config = Config(embedding_model="all-minilm")
        config_dict = config.to_dict()
        
        assert "embedding_model" in config_dict
        assert config_dict["embedding_model"] == "all-minilm"
    
    def test_config_from_dict_with_embedding_model(self):
        """from_dictメソッドで埋め込みモデルが正しく読み込まれることを確認"""
        test_data = {
            "ollama_host": "http://localhost:11434",
            "ollama_model": "llama3:8b",
            "embedding_model": "snowflake-arctic-embed"
        }
        
        config = Config.from_dict(test_data)
        assert config.embedding_model == "snowflake-arctic-embed"
    
    def test_config_from_dict_default_embedding_model(self):
        """埋め込みモデル未指定時のデフォルト値テスト"""
        test_data = {
            "ollama_host": "http://localhost:11434", 
            "ollama_model": "llama3:8b"
        }
        
        config = Config.from_dict(test_data)
        assert config.embedding_model == "nomic-embed-text"
    
    def test_config_save_and_load_with_embedding_model(self):
        """埋め込みモデル設定の保存・読み込みテスト"""
        original_config = Config(
            ollama_model="llama3:8b",
            embedding_model="mxbai-embed-large"
        )
        
        # 保存
        original_config.save_to_file(str(self.config_path))
        
        # 読み込み
        loaded_config = Config.load_from_file(str(self.config_path))
        
        assert loaded_config.embedding_model == "mxbai-embed-large"
        assert loaded_config.ollama_model == "llama3:8b"
    
    def test_config_file_format_with_embedding_model(self):
        """設定ファイルのフォーマットに埋め込みモデルが含まれることを確認"""
        config = Config(embedding_model="all-minilm")
        config.save_to_file(str(self.config_path))
        
        # ファイル内容を直接確認
        with open(self.config_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert "embedding_model" in saved_data
        assert saved_data["embedding_model"] == "all-minilm"


class TestEmbeddingModelSupported:
    """サポートされている埋め込みモデルのテスト"""
    
    def test_supported_embedding_models(self):
        """サポートされている埋め込みモデルのテスト"""
        supported_models = [
            "nomic-embed-text",
            "mxbai-embed-large",
            "all-minilm", 
            "snowflake-arctic-embed"
        ]
        
        for model in supported_models:
            config = Config(embedding_model=model)
            assert config.embedding_model == model
    
    def test_embedding_model_string_representation(self):
        """埋め込みモデル設定の文字列表現テスト"""
        config = Config(
            ollama_model="llama3:8b",
            embedding_model="mxbai-embed-large"
        )
        
        config_str = str(config)
        # 基本情報が含まれていることを確認
        assert "llama3:8b" in config_str
        
        config_repr = repr(config)
        # 詳細情報が含まれていることを確認  
        assert "ollama_model='llama3:8b'" in config_repr