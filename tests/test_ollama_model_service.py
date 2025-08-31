"""
ISSUE-022: LLM モデル動的選択機能のテスト

テスト内容:
- Ollama API からのモデル一覧取得
- エラーハンドリング（接続失敗、タイムアウト）  
- フォールバック機能（デフォルトモデル返却）
"""

import pytest
import requests
from requests.exceptions import ConnectionError, Timeout, HTTPError
from unittest.mock import Mock, patch
from src.logic.ollama_model_service import OllamaModelService, OllamaConnectionError


class TestOllamaModelService:
    """OllamaModelService テストクラス"""
    
    def setup_method(self):
        """各テストメソッド実行前のセットアップ"""
        self.service = OllamaModelService("http://localhost:11434")
        
    def test_init_default_host(self):
        """デフォルトホストでの初期化テスト"""
        service = OllamaModelService()
        assert service.host == "http://localhost:11434"
        assert service.timeout == 5
        
    def test_init_custom_host(self):
        """カスタムホストでの初期化テスト"""
        custom_host = "http://custom-host:8080"
        service = OllamaModelService(custom_host, timeout=10)
        assert service.host == custom_host
        assert service.timeout == 10

    @patch('src.logic.ollama_model_service.requests.get')
    def test_get_available_models_success(self, mock_get):
        """モデル一覧取得成功テスト"""
        # モックレスポンス設定
        mock_response = Mock()
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3:8b"},
                {"name": "mistral:latest"},
                {"name": "codellama:13b"}
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # テスト実行
        models = self.service.get_available_models()
        
        # アサーション
        assert models == ["llama3:8b", "mistral:latest", "codellama:13b"]
        mock_get.assert_called_once_with(
            "http://localhost:11434/api/tags",
            timeout=5
        )

    @patch('src.logic.ollama_model_service.requests.get')
    def test_get_available_models_connection_error(self, mock_get):
        """接続エラー時のテスト"""
        mock_get.side_effect = ConnectionError("Connection failed")
        
        with pytest.raises(OllamaConnectionError) as exc_info:
            self.service.get_available_models()
            
        assert "Ollamaサーバーへの接続に失敗しました" in str(exc_info.value)

    @patch('src.logic.ollama_model_service.requests.get')
    def test_get_available_models_timeout(self, mock_get):
        """タイムアウト時のテスト"""
        mock_get.side_effect = Timeout("Request timeout")
        
        with pytest.raises(OllamaConnectionError) as exc_info:
            self.service.get_available_models()
            
        assert "Ollamaサーバーへの接続がタイムアウトしました" in str(exc_info.value)

    @patch('src.logic.ollama_model_service.requests.get')
    def test_get_available_models_http_error(self, mock_get):
        """HTTPエラー時のテスト"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = HTTPError("404 Not Found")
        mock_response.json.return_value = {"models": []}
        mock_get.return_value = mock_response
        
        with pytest.raises(OllamaConnectionError) as exc_info:
            self.service.get_available_models()
            
        assert "Ollama APIでエラーが発生しました" in str(exc_info.value)

    @patch('src.logic.ollama_model_service.requests.get')
    def test_get_available_models_with_fallback_success(self, mock_get):
        """フォールバック付きモデル取得成功テスト"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "models": [{"name": "llama3:8b"}]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        fallback_models = ["mistral:latest", "codellama:13b"]
        models = self.service.get_available_models_with_fallback(fallback_models)
        
        assert models == ["llama3:8b"]

    @patch('src.logic.ollama_model_service.requests.get')
    def test_get_available_models_with_fallback_error(self, mock_get):
        """フォールバック付きモデル取得エラー時のテスト"""
        mock_get.side_effect = ConnectionError("Connection failed")
        
        fallback_models = ["mistral:latest", "codellama:13b"]
        models = self.service.get_available_models_with_fallback(fallback_models)
        
        assert models == fallback_models

    @patch('src.logic.ollama_model_service.requests.get')
    def test_get_available_models_empty_response(self, mock_get):
        """空のレスポンス時のテスト"""
        mock_response = Mock()
        mock_response.json.return_value = {"models": []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        models = self.service.get_available_models()
        assert models == []

    @patch('src.logic.ollama_model_service.requests.get')
    def test_get_available_models_invalid_json(self, mock_get):
        """不正なJSON時のテスト"""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with pytest.raises(OllamaConnectionError) as exc_info:
            self.service.get_available_models()
            
        assert "Ollama APIからの応答が不正です" in str(exc_info.value)

    @patch.object(OllamaModelService, 'get_available_models')
    def test_is_model_available_success(self, mock_get_models):
        """モデル利用可能性チェック成功テスト"""
        mock_get_models.return_value = ["llama3:8b", "mistral:latest"]
        
        assert self.service.is_model_available("llama3:8b") is True
        assert self.service.is_model_available("codellama:13b") is False

    @patch.object(OllamaModelService, 'get_available_models')
    def test_is_model_available_with_error(self, mock_get_models):
        """モデル利用可能性チェック（エラー時）テスト"""
        mock_get_models.side_effect = OllamaConnectionError("Connection failed")
        
        assert self.service.is_model_available("llama3:8b") is False