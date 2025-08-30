import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch, Mock

# Add project root to sys.path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

# Mock streamlit before importing
streamlit_mock = MagicMock()
sys.modules['streamlit'] = streamlit_mock

from src.ui.settings_view import SettingsView
from src.interfaces.config_interface import ConfigInterface
from src.interfaces.indexing_interface import IndexingInterface
from src.models.config import Config


class TestSettingsView(unittest.TestCase):
    """SettingsViewのユニットテスト"""

    def setUp(self):
        """テストのセットアップ"""
        self.mock_config_interface = MagicMock(spec=ConfigInterface)
        self.mock_indexing_interface = MagicMock(spec=IndexingInterface)
        
        # 初期設定をモック
        self.initial_config = Config(
            selected_folders=["/path/to/docs"],
            chroma_db_path="/path/to/db",
            ollama_model="test_model"
        )
        self.mock_config_interface.load_configuration_with_env_override.return_value = self.initial_config
        self.mock_config_interface.default_config_file = "./data/config.json"

        # インデックス統計をモック
        self.mock_indexing_interface.get_index_statistics.return_value = {
            'index_status': 'ready',
            'document_count': 5,
            'last_updated': '2025-08-30 12:00:00'
        }

        self.settings_view = SettingsView(
            self.mock_config_interface,
            self.mock_indexing_interface
        )

    @patch('src.ui.settings_view.st')
    def test_render_basic_structure(self, mock_st):
        """基本的なUI構造が正しくレンダリングされるかテスト"""
        # すべてのUI要素をモック（何も実行しない状態）
        mock_st.button.return_value = False
        mock_st.text_input.return_value = ""
        mock_st.multiselect.return_value = []
        mock_st.form_submit_button.return_value = False
        mock_st.form.return_value.__enter__.return_value = None
        mock_st.form.return_value.__exit__.return_value = None
        mock_st.columns.return_value = [Mock(), Mock(), Mock()]

        # renderメソッドを呼び出す
        self.settings_view.render()

        # 基本的なUI要素が呼ばれることを確認
        mock_st.title.assert_called_with("設定")
        self.assertTrue(any(call.args[0] == "フォルダ管理" for call in mock_st.header.call_args_list))
        self.assertTrue(any(call.args[0] == "インデックス管理" for call in mock_st.header.call_args_list))
        self.assertTrue(any(call.args[0] == "アプリケーション設定" for call in mock_st.header.call_args_list))

    def test_validate_folder_path_valid(self):
        """フォルダパス検証テスト（有効な場合）"""
        with patch('src.ui.settings_view.Path') as mock_path_class, \
             patch('src.ui.settings_view.os.access') as mock_access, \
             patch('src.ui.settings_view.st') as mock_st:
            
            mock_path = mock_path_class.return_value
            mock_path.exists.return_value = True
            mock_path.is_dir.return_value = True
            mock_access.return_value = True
            
            result = self.settings_view._validate_folder_path("/valid/path")
            self.assertTrue(result)

    def test_validate_folder_path_invalid_empty(self):
        """フォルダパス検証テスト（空の場合）"""
        with patch('src.ui.settings_view.st') as mock_st:
            result = self.settings_view._validate_folder_path("")
            self.assertFalse(result)
            mock_st.error.assert_called_with("フォルダパスを入力してください")

    def test_validate_folder_path_not_exists(self):
        """フォルダパス検証テスト（存在しない場合）"""
        with patch('src.ui.settings_view.Path') as mock_path_class, \
             patch('src.ui.settings_view.st') as mock_st:
            
            mock_path = mock_path_class.return_value
            mock_path.exists.return_value = False
            
            result = self.settings_view._validate_folder_path("/nonexistent/path")
            self.assertFalse(result)
            mock_st.error.assert_called_with("指定されたパスが存在しません")

    def test_handle_folder_addition_success(self):
        """フォルダ追加処理成功テスト"""
        config = Config(
            selected_folders=["/existing/folder"],
            chroma_db_path="/path/to/db",
            ollama_model="test_model"
        )

        with patch.object(self.settings_view, '_validate_folder_path', return_value=True), \
             patch('src.ui.settings_view.Path') as mock_path_class, \
             patch('src.ui.settings_view.st') as mock_st:
            
            mock_path = mock_path_class.return_value
            mock_path.resolve.return_value = "/resolved/new/folder"
            
            self.settings_view._handle_folder_addition(config, "/new/folder")
            
            # 設定が保存されることを確認
            self.mock_config_interface.save_configuration.assert_called_once()
            saved_config = self.mock_config_interface.save_configuration.call_args[0][0]
            self.assertIn("/resolved/new/folder", saved_config.selected_folders)

    def test_handle_folder_removal_success(self):
        """フォルダ削除処理成功テスト"""
        config = Config(
            selected_folders=["/folder1", "/folder2"],
            chroma_db_path="/path/to/db",
            ollama_model="test_model"
        )

        with patch('src.ui.settings_view.st') as mock_st:
            self.settings_view._handle_folder_removal(config, ["/folder1"])
            
            # 設定が保存されることを確認
            self.mock_config_interface.save_configuration.assert_called_once()
            saved_config = self.mock_config_interface.save_configuration.call_args[0][0]
            self.assertEqual(saved_config.selected_folders, ["/folder2"])

    def test_handle_index_rebuild_success(self):
        """インデックス再作成成功テスト"""
        config = Config(
            selected_folders=["/folder1"],
            chroma_db_path="/path/to/db",
            ollama_model="test_model"
        )

        with patch('src.ui.settings_view.st') as mock_st:
            self.settings_view._handle_index_rebuild(config)
            
            # インデックス再作成が呼ばれることを確認
            self.mock_indexing_interface.rebuild_index_from_folders.assert_called_once_with(["/folder1"])

    def test_handle_index_rebuild_no_folders(self):
        """インデックス再作成テスト（フォルダなしの場合）"""
        config = Config(
            selected_folders=[],
            chroma_db_path="/path/to/db",
            ollama_model="test_model"
        )

        with patch('src.ui.settings_view.st') as mock_st:
            self.settings_view._handle_index_rebuild(config)
            
            # 警告メッセージが表示されることを確認
            mock_st.warning.assert_called_with("インデックスを作成するフォルダが選択されていません。フォルダを追加してからお試しください。")
            # インデックス再作成は呼ばれないことを確認
            self.mock_indexing_interface.rebuild_index_from_folders.assert_not_called()

    def test_handle_index_clear_success(self):
        """インデックス削除成功テスト"""
        with patch('src.ui.settings_view.st') as mock_st:
            self.settings_view._handle_index_clear()
            
            # インデックス削除が呼ばれることを確認
            self.mock_indexing_interface.clear_index.assert_called_once()

    def test_validate_config_input_valid(self):
        """設定入力値検証テスト（有効な場合）"""
        with patch('src.ui.settings_view.Path') as mock_path_class, \
             patch('src.ui.settings_view.os.access') as mock_access:
            
            mock_path = mock_path_class.return_value
            mock_path.parent.exists.return_value = True
            mock_access.return_value = True
            
            result = self.settings_view._validate_config_input("valid_model", "/valid/path")
            self.assertTrue(result)

    def test_handle_config_save_success(self):
        """設定保存成功テスト"""
        config = Config(
            selected_folders=["/folder1"],
            chroma_db_path="/old/path",
            ollama_model="old_model"
        )

        with patch.object(self.settings_view, '_validate_config_input', return_value=True), \
             patch('src.ui.settings_view.st') as mock_st:
            
            self.settings_view._handle_config_save(config, "new_model", "/new/path")
            
            # 設定が保存されることを確認
            self.mock_config_interface.save_configuration.assert_called_once()
            saved_config = self.mock_config_interface.save_configuration.call_args[0][0]
            self.assertEqual(saved_config.ollama_model, "new_model")
            self.assertEqual(saved_config.chroma_db_path, "/new/path")


if __name__ == '__main__':
    unittest.main()