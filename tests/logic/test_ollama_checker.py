"""
Ollama モデルチェッカーのテストケース

起動時モデルチェック機能のテストを実装
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import requests
from dataclasses import dataclass

from src.logic.ollama_checker import (
    OllamaModelChecker,
    ModelCheckResult,
    ModelInfo
)


class TestOllamaModelChecker(unittest.TestCase):
    """OllamaModelCheckerのテストクラス"""
    
    def setUp(self):
        """テストセットアップ"""
        self.checker = OllamaModelChecker()
    
    @patch('src.logic.ollama_checker.requests.get')
    def test_check_ollama_connection_success(self, mock_get):
        """Ollama接続チェック成功テスト"""
        # モックレスポンス設定
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # テスト実行
        result = self.checker._check_ollama_connection()
        
        # 検証
        self.assertTrue(result)
        mock_get.assert_called_once_with(
            "http://localhost:11434/api/tags", 
            timeout=5.0
        )
    
    @patch('src.logic.ollama_checker.requests.get')
    def test_check_ollama_connection_failure(self, mock_get):
        """Ollama接続チェック失敗テスト"""
        # モックでConnectionErrorを発生させる
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        # テスト実行
        result = self.checker._check_ollama_connection()
        
        # 検証
        self.assertFalse(result)
    
    @patch('src.logic.ollama_checker.requests.get')
    def test_get_available_models_success(self, mock_get):
        """利用可能モデル取得成功テスト"""
        # モックレスポンス設定
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3:8b"},
                {"name": "nomic-embed-text"},
                {"name": "llama3:latest"}
            ]
        }
        mock_get.return_value = mock_response
        
        # テスト実行
        models = self.checker._get_available_models()
        
        # 検証
        expected_models = ["llama3:8b", "nomic-embed-text", "llama3:latest"]
        self.assertEqual(models, expected_models)
    
    def test_is_model_available_exact_match(self):
        """モデル利用可能チェック - 完全一致"""
        available_models = ["llama3:8b", "nomic-embed-text", "llama3:latest"]
        
        # テスト実行・検証
        self.assertTrue(self.checker._is_model_available("llama3:8b", available_models))
        self.assertTrue(self.checker._is_model_available("nomic-embed-text", available_models))
        self.assertFalse(self.checker._is_model_available("missing-model", available_models))
    
    def test_is_model_available_partial_match(self):
        """モデル利用可能チェック - 部分一致"""
        available_models = ["llama3:latest", "nomic-embed-text:latest"]
        
        # テスト実行・検証
        self.assertTrue(self.checker._is_model_available("llama3:8b", available_models))
        self.assertTrue(self.checker._is_model_available("nomic-embed-text", available_models))
        self.assertFalse(self.checker._is_model_available("codellama:7b", available_models))
    
    @patch.object(OllamaModelChecker, '_check_ollama_connection')
    @patch.object(OllamaModelChecker, '_get_available_models')
    def test_check_required_models_all_available(self, mock_get_models, mock_check_connection):
        """必須モデルチェック - すべて利用可能"""
        # モック設定
        mock_check_connection.return_value = True
        mock_get_models.return_value = ["llama3:8b", "nomic-embed-text"]
        
        # テスト実行
        result = self.checker.check_required_models()
        
        # 検証
        self.assertIsInstance(result, ModelCheckResult)
        self.assertTrue(result.is_available)
        self.assertEqual(len(result.missing_models), 0)
        self.assertTrue(result.ollama_connected)
        self.assertIsNone(result.error_message)
    
    @patch.object(OllamaModelChecker, '_check_ollama_connection')
    @patch.object(OllamaModelChecker, '_get_available_models')
    def test_check_required_models_missing_models(self, mock_get_models, mock_check_connection):
        """必須モデルチェック - モデル不足"""
        # モック設定
        mock_check_connection.return_value = True
        mock_get_models.return_value = ["llama3:8b"]  # nomic-embed-text が不足
        
        # テスト実行
        result = self.checker.check_required_models()
        
        # 検証
        self.assertIsInstance(result, ModelCheckResult)
        self.assertFalse(result.is_available)
        self.assertEqual(len(result.missing_models), 1)
        self.assertEqual(result.missing_models[0].name, "nomic-embed-text")
        self.assertTrue(result.ollama_connected)
        self.assertIsNone(result.error_message)
    
    @patch.object(OllamaModelChecker, '_check_ollama_connection')
    def test_check_required_models_ollama_disconnected(self, mock_check_connection):
        """必須モデルチェック - Ollama接続失敗"""
        # モック設定
        mock_check_connection.return_value = False
        
        # テスト実行
        result = self.checker.check_required_models()
        
        # 検証
        self.assertIsInstance(result, ModelCheckResult)
        self.assertFalse(result.is_available)
        self.assertEqual(len(result.missing_models), 2)  # 全モデルが不足扱い
        self.assertFalse(result.ollama_connected)
        self.assertIsNotNone(result.error_message)
        self.assertIn("接続できません", result.error_message)
    
    def test_get_installation_guide_no_missing_models(self):
        """インストールガイド生成 - 不足モデルなし"""
        missing_models = []
        guide = self.checker.get_installation_guide(missing_models)
        
        self.assertIn("すべての必須モデルがインストール済み", guide)
    
    def test_get_installation_guide_with_missing_models(self):
        """インストールガイド生成 - 不足モデルあり"""
        missing_models = [
            ModelInfo(
                name="llama3:8b",
                display_name="LLaMA 3 8B",
                description="回答生成用モデル",
                install_command="ollama pull llama3:8b"
            )
        ]
        
        guide = self.checker.get_installation_guide(missing_models)
        
        # 検証
        self.assertIn("必須モデルが不足", guide)
        self.assertIn("LLaMA 3 8B", guide)
        self.assertIn("ollama pull llama3:8b", guide)
        self.assertIn("インストール手順", guide)
    
    def test_required_models_configuration(self):
        """必須モデル設定の確認"""
        required_models = OllamaModelChecker.REQUIRED_MODELS
        
        # 必須モデルが正しく定義されていることを確認
        self.assertIn("llama3:8b", required_models)
        self.assertIn("nomic-embed-text", required_models)
        
        # モデル情報が正しく設定されていることを確認
        llama_model = required_models["llama3:8b"]
        self.assertEqual(llama_model.name, "llama3:8b")
        self.assertIn("ollama pull llama3:8b", llama_model.install_command)
        
        embed_model = required_models["nomic-embed-text"]
        self.assertEqual(embed_model.name, "nomic-embed-text")
        self.assertIn("ollama pull nomic-embed-text", embed_model.install_command)


if __name__ == '__main__':
    unittest.main()