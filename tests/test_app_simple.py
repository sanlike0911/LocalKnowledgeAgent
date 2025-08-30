import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

# Add project root to sys.path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

# 依存関係のモックはconftest.pyで処理されるため、ここでは不要


class TestAppImport(unittest.TestCase):
    """アプリケーションの基本的なインポートテスト"""
    
    def test_app_import(self):
        """app.pyがインポートできることを確認"""
        try:
            from app import LocalKnowledgeAgentApp, main
            self.assertTrue(True, "アプリケーションのインポートが成功")
        except ImportError as e:
            self.fail(f"アプリケーションのインポートが失敗: {e}")
    
    def test_main_function_exists(self):
        """main関数が存在することを確認"""
        from app import main
        self.assertTrue(callable(main), "main関数が呼び出し可能")


if __name__ == '__main__':
    unittest.main()