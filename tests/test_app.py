import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch, Mock

# Add project root to sys.path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

# Mock streamlit before importing
class MockSessionState(dict):
    """StreamlitのSessionStateをモック"""
    def __getattr__(self, name):
        return self.get(name)
    
    def __setattr__(self, name, value):
        self[name] = value
        
    def __delattr__(self, name):
        if name in self:
            del self[name]

streamlit_mock = MagicMock()
streamlit_mock.session_state = MockSessionState()
sys.modules['streamlit'] = streamlit_mock

from app import LocalKnowledgeAgentApp
from src.utils.session_state import AppState


class TestLocalKnowledgeAgentApp(unittest.TestCase):
    """LocalKnowledgeAgentAppのユニットテスト"""

    def setUp(self):
        """テストのセットアップ"""
        streamlit_mock.session_state.clear()
        
        # 初期状態を設定
        streamlit_mock.session_state['app_state'] = AppState()
        streamlit_mock.session_state['processing_message'] = ""
        streamlit_mock.session_state['error_message'] = ""
        streamlit_mock.session_state['success_message'] = ""
        streamlit_mock.session_state['progress_value'] = 0.0
        streamlit_mock.session_state['debug_info'] = {
            "last_error": None,
            "performance_metrics": {},
            "session_start_time": None,
        }
        streamlit_mock.session_state['chat_history'] = []
        streamlit_mock.session_state['config'] = {
            "max_chat_history": 50,
        }

    @patch('app.QAService')
    @patch('app.ChromaDBIndexer')
    @patch('app.ConfigManager')
    @patch('app.setup_logging')
    def test_app_initialization(self, mock_logging, mock_config, mock_indexer, mock_qa):
        """アプリケーション初期化テスト"""
        # モックの設定
        mock_logging.return_value = MagicMock()
        mock_config.return_value = MagicMock()
        mock_indexer.return_value = MagicMock()
        mock_qa.return_value = MagicMock()
        
        # アプリケーション作成
        app = LocalKnowledgeAgentApp()
        
        # 必要なコンポーネントが初期化されることを確認
        self.assertIsNotNone(app.config_manager)
        self.assertIsNotNone(app.indexer)
        self.assertIsNotNone(app.qa_service)
        self.assertIsNotNone(app.main_view)
        self.assertIsNotNone(app.settings_view)
        self.assertIsNotNone(app.navigation)

    @patch('app.Path.mkdir')
    @patch('app.get_app_config')
    @patch('app.QAService')
    @patch('app.ChromaDBIndexer')
    @patch('app.ConfigManager')
    @patch('app.setup_logging')
    def test_environment_validation(self, mock_logging, mock_config, mock_indexer, mock_qa, mock_get_config, mock_mkdir):
        """環境検証テスト"""
        # モックの設定
        mock_logging.return_value = MagicMock()
        mock_config.return_value = MagicMock()
        mock_indexer.return_value = MagicMock()
        mock_qa.return_value = MagicMock()
        mock_get_config.return_value = {'test_config': 'value'}
        
        app = LocalKnowledgeAgentApp()
        app._validate_environment()
        
        # 環境設定取得が呼ばれることを確認
        mock_get_config.assert_called_once()
        # ディレクトリ作成が呼ばれることを確認
        mock_mkdir.assert_called()

    @patch('app.st')
    @patch('app.init_session_state')
    @patch('app.QAService')
    @patch('app.ChromaDBIndexer') 
    @patch('app.ConfigManager')
    @patch('app.setup_logging')
    def test_configure_page(self, mock_logging, mock_config, mock_indexer, mock_qa, mock_init_session, mock_st):
        """ページ設定テスト"""
        # モックの設定
        mock_logging.return_value = MagicMock()
        mock_config.return_value = MagicMock()
        mock_indexer.return_value = MagicMock()
        mock_qa.return_value = MagicMock()
        
        app = LocalKnowledgeAgentApp()
        app._configure_page()
        
        # ページ設定が呼ばれることを確認
        mock_st.set_page_config.assert_called_once()

    @patch('app.SessionStateManager')
    @patch('app.QAService')
    @patch('app.ChromaDBIndexer')
    @patch('app.ConfigManager')
    @patch('app.setup_logging')
    def test_handle_cancellation_not_requested(self, mock_logging, mock_config, mock_indexer, mock_qa, mock_session):
        """キャンセル処理テスト（要求なし）"""
        # モックの設定
        mock_logging.return_value = MagicMock()
        mock_config.return_value = MagicMock()
        mock_indexer.return_value = MagicMock()
        mock_qa.return_value = MagicMock()
        mock_session.is_cancel_requested.return_value = False
        
        app = LocalKnowledgeAgentApp()
        
        # キャンセル要求がない場合は何もしない
        app._handle_cancellation()
        
        mock_session.set_app_state.assert_not_called()

    @patch('app.st')
    @patch('app.SessionStateManager')
    @patch('app.QAService')
    @patch('app.ChromaDBIndexer')
    @patch('app.ConfigManager')
    @patch('app.setup_logging')
    def test_handle_cancellation_requested(self, mock_logging, mock_config, mock_indexer, mock_qa, mock_session, mock_st):
        """キャンセル処理テスト（要求あり）"""
        # モックの設定
        mock_logging.return_value = MagicMock()
        mock_config.return_value = MagicMock()
        mock_indexer.return_value = MagicMock()
        mock_qa.return_value = MagicMock()
        mock_session.is_cancel_requested.return_value = True
        
        app = LocalKnowledgeAgentApp()
        
        # キャンセル要求がある場合の処理
        app._handle_cancellation()
        
        # 状態がアイドルに設定されることを確認
        mock_session.set_app_state.assert_called_with("idle", cancel_requested=False)

    @patch('app.QAService')
    @patch('app.ChromaDBIndexer')
    @patch('app.ConfigManager')
    @patch('app.setup_logging')
    def test_render_main_view(self, mock_logging, mock_config, mock_indexer, mock_qa):
        """メインビューレンダリングテスト"""
        # モックの設定
        mock_logging.return_value = MagicMock()
        mock_config.return_value = MagicMock()
        mock_indexer.return_value = MagicMock()
        mock_qa.return_value = MagicMock()
        
        app = LocalKnowledgeAgentApp()
        
        # メインビューがレンダリングされることを確認
        app._render_current_view("main")
        app.main_view.render.assert_called_once()

    @patch('app.QAService')
    @patch('app.ChromaDBIndexer')
    @patch('app.ConfigManager')
    @patch('app.setup_logging')
    def test_render_settings_view(self, mock_logging, mock_config, mock_indexer, mock_qa):
        """設定ビューレンダリングテスト"""
        # モックの設定
        mock_logging.return_value = MagicMock()
        mock_config.return_value = MagicMock()
        mock_indexer.return_value = MagicMock()
        mock_qa.return_value = MagicMock()
        
        app = LocalKnowledgeAgentApp()
        
        # 設定ビューがレンダリングされることを確認
        app._render_current_view("settings")
        app.settings_view.render.assert_called_once()

    @patch('app.st')
    @patch('app.QAService')
    @patch('app.ChromaDBIndexer')
    @patch('app.ConfigManager')
    @patch('app.setup_logging')
    def test_render_unknown_view(self, mock_logging, mock_config, mock_indexer, mock_qa, mock_st):
        """不明なビューのエラーハンドリングテスト"""
        # モックの設定
        mock_logging.return_value = MagicMock()
        mock_config.return_value = MagicMock()
        mock_indexer.return_value = MagicMock()
        mock_qa.return_value = MagicMock()
        
        app = LocalKnowledgeAgentApp()
        
        # 不明なページの場合エラーが表示される
        app._render_current_view("unknown")
        mock_st.error.assert_called()

    @patch('app.st.stop')
    @patch('app.st.error')
    @patch('app.ConfigManager')
    @patch('app.setup_logging')
    def test_service_initialization_error(self, mock_logging, mock_config, mock_st_error, mock_st_stop):
        """サービス初期化エラーテスト"""
        # モックの設定
        mock_logging.return_value = MagicMock()
        mock_config.side_effect = Exception("設定エラー")
        
        # エラーが発生してもアプリケーションが適切に処理する
        LocalKnowledgeAgentApp()
        
        # エラーメッセージが表示されることを確認
        mock_st_error.assert_called()
        mock_st_stop.assert_called()

    @patch('app.get_app_config')
    @patch('app.init_session_state')
    @patch('app.st')
    @patch('app.QAService')
    @patch('app.ChromaDBIndexer')
    @patch('app.ConfigManager')
    @patch('app.setup_logging')
    def test_run_success(self, mock_logging, mock_config, mock_indexer, mock_qa, mock_st, mock_init_session, mock_get_config):
        """正常実行テスト"""
        # モックの設定
        mock_logging.return_value = MagicMock()
        mock_config.return_value = MagicMock()
        mock_indexer.return_value = MagicMock()
        mock_qa.return_value = MagicMock()
        mock_get_config.return_value = {'test_config': 'value'}
        
        app = LocalKnowledgeAgentApp()
        app.navigation.render = MagicMock(return_value="main")
        app._handle_cancellation = MagicMock()
        app._render_current_view = MagicMock()
        
        app.run()
        
        # 各段階が実行されることを確認
        mock_init_session.assert_called_once()
        app.navigation.render.assert_called_once()
        app._handle_cancellation.assert_called_once()
        app._render_current_view.assert_called_once_with("main")


if __name__ == '__main__':
    unittest.main()