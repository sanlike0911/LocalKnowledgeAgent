import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch, Mock

# Add project root to sys.path
project_root = Path(__file__).resolve().parents[2]
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

from src.ui.navigation import Navigation
from src.utils.session_state import AppState


class TestNavigation(unittest.TestCase):
    """Navigationクラスのユニットテスト"""

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
        
        self.navigation = Navigation()

    @patch('src.ui.navigation.st')
    def test_render_sidebar_navigation(self, mock_st):
        """サイドバーナビゲーション表示テスト"""
        mock_st.sidebar.radio.return_value = "💬 メイン"
        
        self.navigation.render_sidebar()
        
        # サイドバーのラジオボタンが正しく表示されることを確認（アイコン付き）
        mock_st.sidebar.radio.assert_called_once_with(
            "ページ選択",
            ["💬 メイン", "⚙️ 設定"],
            index=0,
            disabled=False,
            help=None
        )

    @patch('src.ui.navigation.st')
    def test_page_selection_main(self, mock_st):
        """メインページ選択テスト"""
        mock_st.sidebar.radio.return_value = "💬 メイン"
        
        page = self.navigation.get_current_page()
        
        self.assertEqual(page, "main")

    @patch('src.ui.navigation.st')
    def test_page_selection_settings(self, mock_st):
        """設定ページ選択テスト"""
        mock_st.sidebar.radio.return_value = "⚙️ 設定"
        
        page = self.navigation.get_current_page()
        
        self.assertEqual(page, "settings")

    @patch('src.ui.navigation.st')
    def test_navigation_state_persistence(self, mock_st):
        """ナビゲーション状態の永続化テスト"""
        # 設定ページを選択
        mock_st.sidebar.radio.return_value = "⚙️ 設定"
        self.navigation.render_sidebar()
        
        # セッションステートに状態が保存されることを確認
        app_state = streamlit_mock.session_state.get('app_state')
        self.assertEqual(app_state.current_page, "settings")

    @patch('src.ui.navigation.st')
    def test_processing_state_navigation_disabled(self, mock_st):
        """処理中のナビゲーション無効化テスト"""
        # 処理中状態に設定
        app_state = AppState(app_state="processing_qa")
        streamlit_mock.session_state['app_state'] = app_state
        
        mock_st.sidebar.radio.return_value = "💬 メイン"
        
        self.navigation.render_sidebar()
        
        # 処理中は無効化されることを確認（アイコン付き）
        mock_st.sidebar.radio.assert_called_with(
            "ページ選択",
            ["💬 メイン", "⚙️ 設定"],
            index=0,
            disabled=True,
            help="処理中のため画面遷移は無効です"
        )

    @patch('src.ui.navigation.st')
    def test_status_display_idle(self, mock_st):
        """ステータス表示テスト（アイドル状態）"""
        app_state = AppState(app_state="idle")
        streamlit_mock.session_state['app_state'] = app_state
        
        self.navigation.render_status()
        
        # アイドル状態では何も表示されないことを確認
        mock_st.sidebar.info.assert_not_called()

    @patch('src.ui.navigation.st')
    def test_status_display_processing_qa(self, mock_st):
        """ステータス表示テスト（QA処理中）"""
        app_state = AppState(app_state="processing_qa")
        streamlit_mock.session_state['app_state'] = app_state
        # st.session_stateのgetメソッドをモック
        with patch('src.ui.navigation.st.session_state.get') as mock_get:
            mock_get.return_value = "質問処理中..."
            
            self.navigation.render_status()
            
            # 処理中メッセージが表示されることを確認
            mock_st.sidebar.info.assert_called_with("🔄 質問処理中...")

    @patch('src.ui.navigation.st')
    def test_status_display_processing_indexing(self, mock_st):
        """ステータス表示テスト（インデックス処理中）"""
        app_state = AppState(app_state="processing_indexing")
        streamlit_mock.session_state['app_state'] = app_state
        # st.session_stateのgetメソッドをモック
        with patch('src.ui.navigation.st.session_state.get') as mock_get:
            mock_get.return_value = "インデックス作成中..."
            
            self.navigation.render_status()
            
            # 処理中メッセージが表示されることを確認
            mock_st.sidebar.info.assert_called_with("🔄 インデックス作成中...")

    @patch('src.ui.navigation.st')
    def test_cancel_button_processing(self, mock_st):
        """キャンセルボタン表示テスト（処理中）"""
        app_state = AppState(app_state="processing_qa")
        streamlit_mock.session_state['app_state'] = app_state
        
        mock_st.sidebar.button.return_value = False
        
        self.navigation.render_cancel_button()
        
        # キャンセルボタンが表示されることを確認
        mock_st.sidebar.button.assert_called_with(
            "⛔ キャンセル",
            key="cancel_button",
            help="現在の処理をキャンセルします"
        )

    @patch('src.ui.navigation.st')
    def test_cancel_button_clicked(self, mock_st):
        """キャンセルボタンクリックテスト"""
        app_state = AppState(app_state="processing_qa")
        streamlit_mock.session_state['app_state'] = app_state
        
        mock_st.sidebar.button.return_value = True
        
        result = self.navigation.render_cancel_button()
        
        # キャンセルがクリックされたことを確認
        self.assertTrue(result)

    @patch('src.ui.navigation.st')
    def test_cancel_button_not_processing(self, mock_st):
        """キャンセルボタン非表示テスト（非処理中）"""
        app_state = AppState(app_state="idle")
        streamlit_mock.session_state['app_state'] = app_state
        
        result = self.navigation.render_cancel_button()
        
        # アイドル状態ではキャンセルボタンが表示されないことを確認
        mock_st.sidebar.button.assert_not_called()
        self.assertFalse(result)

    def test_page_mapping(self):
        """ページマッピングテスト"""
        # 内部的なページマッピングが正しく動作することを確認
        self.assertEqual(self.navigation._page_mapping["メイン"], "main")
        self.assertEqual(self.navigation._page_mapping["設定"], "settings")

    @patch('src.ui.navigation.st')
    def test_progress_display(self, mock_st):
        """プログレス表示テスト"""
        # st.session_stateのgetメソッドをモック
        with patch('src.ui.navigation.st.session_state.get') as mock_get:
            mock_get.return_value = 0.7
            
            self.navigation.render_progress()
            
            # プログレスバーが表示されることを確認
            mock_st.sidebar.progress.assert_called_with(0.7)

    @patch('src.ui.navigation.st')
    def test_error_message_display(self, mock_st):
        """エラーメッセージ表示テスト"""
        mock_st.sidebar.button.return_value = False  # ボタンは押されていない
        
        with patch('src.ui.navigation.st.session_state.get') as mock_get:
            mock_get.side_effect = lambda key, default='': {
                'error_message': 'エラーが発生しました',
                'success_message': ''
            }.get(key, default)
            
            self.navigation.render_messages()
            
            # エラーメッセージが表示されることを確認
            mock_st.sidebar.error.assert_called_with("エラーが発生しました")

    @patch('src.ui.navigation.st')
    def test_success_message_display(self, mock_st):
        """成功メッセージ表示テスト"""
        mock_st.sidebar.button.return_value = False  # ボタンは押されていない
        
        with patch('src.ui.navigation.st.session_state.get') as mock_get:
            mock_get.side_effect = lambda key, default='': {
                'error_message': '',
                'success_message': '処理が完了しました'
            }.get(key, default)
            
            self.navigation.render_messages()
            
            # 成功メッセージが表示されることを確認
            mock_st.sidebar.success.assert_called_with("処理が完了しました")

    @patch('src.ui.navigation.st')  
    def test_full_sidebar_render(self, mock_st):
        """サイドバー全体のレンダリングテスト"""
        mock_st.sidebar.radio.return_value = "メイン"
        streamlit_mock.session_state['processing_message'] = ""
        streamlit_mock.session_state['error_message'] = ""
        streamlit_mock.session_state['success_message'] = ""
        streamlit_mock.session_state['progress_value'] = 0.0
        
        result = self.navigation.render()
        
        # すべてのコンポーネントが正しく呼び出されることを確認
        mock_st.sidebar.radio.assert_called_once()
        self.assertEqual(result, "main")


if __name__ == '__main__':
    unittest.main()