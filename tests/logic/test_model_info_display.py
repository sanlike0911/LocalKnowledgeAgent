"""
Phase 6.2 モデル情報表示機能のテスト

TDD Red フェーズ: モデル詳細情報表示機能のテストケースを作成
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from src.logic.ollama_model_service import OllamaModelService, OllamaConnectionError


class TestModelInfoDisplay:
    """モデル情報表示機能のテスト"""

    @pytest.fixture
    def model_service(self):
        """OllamaModelServiceのインスタンスを返すフィクスチャ"""
        return OllamaModelService()

    def test_get_model_info_success(self, model_service):
        """正常系: モデル詳細情報を取得"""
        # Arrange
        mock_response_data = {
            "models": [
                {
                    "name": "llama3:8b",
                    "size": 4661224192,  # バイト単位のサイズ
                    "modified_at": "2024-08-30T10:00:00Z",
                    "digest": "sha256:123456789"
                },
                {
                    "name": "codellama:13b",
                    "size": 7365967616,  # 約7GB
                    "modified_at": "2024-08-29T15:30:00Z",
                    "digest": "sha256:abcdef123"
                }
            ]
        }
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            # Act
            model_info = model_service.get_model_info("llama3:8b")

            # Assert
            assert model_info is not None
            assert model_info["name"] == "llama3:8b"
            assert model_info["size"] == 4661224192
            assert model_info["modified_at"] == "2024-08-30T10:00:00Z"
            assert "digest" in model_info

    def test_get_model_info_not_found(self, model_service):
        """異常系: 存在しないモデルの情報を取得"""
        mock_response_data = {
            "models": [
                {
                    "name": "llama3:8b",
                    "size": 4661224192,
                    "modified_at": "2024-08-30T10:00:00Z"
                }
            ]
        }
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            # Act
            model_info = model_service.get_model_info("nonexistent:model")

            # Assert
            assert model_info is None

    def test_format_model_size_bytes_to_human_readable(self, model_service):
        """正常系: バイト数を人間が読みやすい形式に変換"""
        # Act & Assert
        assert model_service.format_model_size(1024) == "1.0 KB"
        assert model_service.format_model_size(1048576) == "1.0 MB"
        assert model_service.format_model_size(4661224192) == "4.3 GB"
        assert model_service.format_model_size(7365967616) == "6.9 GB"
        assert model_service.format_model_size(1099511627776) == "1.0 TB"

    def test_format_model_size_edge_cases(self, model_service):
        """境界値テスト: サイズ変換のエッジケース"""
        # Act & Assert
        assert model_service.format_model_size(0) == "0 B"
        assert model_service.format_model_size(512) == "512 B"
        assert model_service.format_model_size(1023) == "1023 B"

    def test_format_datetime_to_japanese(self, model_service):
        """正常系: ISO日時を日本語フォーマットに変換"""
        # Act & Assert
        result = model_service.format_datetime("2024-08-30T10:00:00Z")
        assert result == "2024年08月30日 10:00"

    def test_format_datetime_invalid_format(self, model_service):
        """異常系: 不正な日時フォーマットの処理"""
        # Act & Assert
        result = model_service.format_datetime("invalid-date")
        assert result == "不明"

    def test_format_datetime_none(self, model_service):
        """異常系: None値の日時処理"""
        # Act & Assert
        result = model_service.format_datetime(None)
        assert result == "不明"

    def test_is_large_model_warning_true(self, model_service):
        """正常系: 大容量モデルの警告判定 - True"""
        large_size = 8 * 1024 * 1024 * 1024  # 8GB
        
        # Act & Assert
        assert model_service.is_large_model(large_size) is True

    def test_is_large_model_warning_false(self, model_service):
        """正常系: 大容量モデルの警告判定 - False"""
        small_size = 2 * 1024 * 1024 * 1024  # 2GB
        
        # Act & Assert
        assert model_service.is_large_model(small_size) is False

    def test_estimate_memory_usage(self, model_service):
        """正常系: メモリ使用量の推定"""
        model_size = 4 * 1024 * 1024 * 1024  # 4GB
        
        # Act
        estimated_memory = model_service.estimate_memory_usage(model_size)
        
        # Assert (一般的にモデルサイズの1.2-1.5倍のメモリが必要)
        assert estimated_memory >= model_size * 1.2
        assert estimated_memory <= model_size * 1.5

    def test_get_model_info_connection_error(self, model_service):
        """異常系: API接続エラーの処理"""
        with patch('requests.get', side_effect=Exception("Connection refused")):
            # Act
            model_info = model_service.get_model_info("llama3:8b")

            # Assert
            assert model_info is None

    def test_get_all_models_info_success(self, model_service):
        """正常系: 全モデルの詳細情報を取得"""
        mock_response_data = {
            "models": [
                {
                    "name": "llama3:8b",
                    "size": 4661224192,
                    "modified_at": "2024-08-30T10:00:00Z"
                },
                {
                    "name": "codellama:13b", 
                    "size": 7365967616,
                    "modified_at": "2024-08-29T15:30:00Z"
                }
            ]
        }
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            # Act
            all_models_info = model_service.get_all_models_info()

            # Assert
            assert len(all_models_info) == 2
            assert all_models_info[0]["name"] == "llama3:8b"
            assert all_models_info[1]["name"] == "codellama:13b"
            assert all(isinstance(model["size"], int) for model in all_models_info)