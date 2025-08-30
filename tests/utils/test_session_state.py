import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime

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

from src.utils.session_state import SessionStateManager, AppState, ChatMessage, init_session_state


class TestSessionStateManager(unittest.TestCase):
    """SessionStateManagerのユニットテスト"""

    def setUp(self):
        """テストのセットアップ"""
        # テスト用のsession_stateをリセット
        streamlit_mock.session_state.clear()
        
        # 必要な初期状態を設定
        streamlit_mock.session_state['config'] = {
            "max_chat_history": 50,
        }
        streamlit_mock.session_state['debug_info'] = {
            "last_error": None,
            "performance_metrics": {},
            "session_start_time": None,
        }
        
    def test_initialize_session_state(self):
        """セッションステート初期化テスト"""
        SessionStateManager.initialize_session_state()
        
        # 必須の状態が初期化されることを確認
        self.assertIn('app_state', streamlit_mock.session_state)
        self.assertIn('chat_history', streamlit_mock.session_state)
        self.assertIn('config', streamlit_mock.session_state)
        
        # デフォルト値が正しく設定されることを確認
        self.assertEqual(streamlit_mock.session_state['chat_history'], [])
        self.assertIsInstance(streamlit_mock.session_state['app_state'], AppState)

    def test_get_app_state_initial(self):
        """初期アプリケーション状態取得テスト"""
        app_state = SessionStateManager.get_app_state()
        
        self.assertIsInstance(app_state, AppState)
        self.assertEqual(app_state.app_state, "idle")
        self.assertEqual(app_state.cancel_requested, False)
        self.assertEqual(app_state.current_page, "main")

    def test_set_app_state(self):
        """アプリケーション状態設定テスト"""
        SessionStateManager.set_app_state(
            state="processing_qa",
            cancel_requested=True,
            current_page="settings"
        )
        
        app_state = SessionStateManager.get_app_state()
        self.assertEqual(app_state.app_state, "processing_qa")
        self.assertEqual(app_state.cancel_requested, True)
        self.assertEqual(app_state.current_page, "settings")

    def test_add_chat_message(self):
        """チャットメッセージ追加テスト"""
        SessionStateManager.add_chat_message(
            role="user",
            content="テストメッセージ",
            sources=["test_source.pdf"]
        )
        
        chat_history = streamlit_mock.session_state.get('chat_history', [])
        self.assertEqual(len(chat_history), 1)
        
        message = chat_history[0]
        self.assertEqual(message['role'], "user")
        self.assertEqual(message['content'], "テストメッセージ")
        self.assertEqual(message['sources'], ["test_source.pdf"])
        self.assertIsInstance(message['timestamp'], str)

    def test_add_chat_message_max_history_limit(self):
        """チャットメッセージ履歴制限テスト"""
        # 設定で最大履歴数を3に設定
        SessionStateManager.set_config("max_chat_history", 3)
        
        # 5つのメッセージを追加
        for i in range(5):
            SessionStateManager.add_chat_message("user", f"メッセージ {i}")
        
        chat_history = streamlit_mock.session_state.get('chat_history', [])
        self.assertEqual(len(chat_history), 3)  # 最大履歴数で制限される
        
        # 最新の3つのメッセージのみが残ることを確認
        self.assertEqual(chat_history[0]['content'], "メッセージ 2")
        self.assertEqual(chat_history[1]['content'], "メッセージ 3")
        self.assertEqual(chat_history[2]['content'], "メッセージ 4")

    def test_clear_chat_history(self):
        """チャット履歴クリアテスト"""
        # メッセージを追加
        SessionStateManager.add_chat_message("user", "テストメッセージ")
        self.assertEqual(len(streamlit_mock.session_state.get('chat_history', [])), 1)
        
        # 履歴をクリア
        SessionStateManager.clear_chat_history()
        self.assertEqual(len(streamlit_mock.session_state.get('chat_history', [])), 0)

    def test_get_config_default(self):
        """設定取得テスト（デフォルト値）"""
        value = SessionStateManager.get_config("nonexistent_key", "default_value")
        self.assertEqual(value, "default_value")

    def test_set_config(self):
        """設定設定テスト"""
        SessionStateManager.set_config("test_key", "test_value")
        value = SessionStateManager.get_config("test_key")
        self.assertEqual(value, "test_value")

    def test_set_processing_status(self):
        """処理状況設定テスト"""
        SessionStateManager.set_processing_status("処理中...", 0.5)
        
        self.assertEqual(streamlit_mock.session_state['processing_message'], "処理中...")
        self.assertEqual(streamlit_mock.session_state['progress_value'], 0.5)

    def test_set_error_message(self):
        """エラーメッセージ設定テスト"""
        SessionStateManager.set_error_message("エラーが発生しました")
        
        self.assertEqual(streamlit_mock.session_state['error_message'], "エラーが発生しました")
        self.assertEqual(streamlit_mock.session_state['debug_info']['last_error'], "エラーが発生しました")

    def test_set_success_message(self):
        """成功メッセージ設定テスト"""
        SessionStateManager.set_success_message("成功しました")
        self.assertEqual(streamlit_mock.session_state['success_message'], "成功しました")

    def test_clear_messages(self):
        """メッセージクリアテスト"""
        SessionStateManager.set_error_message("エラー")
        SessionStateManager.set_success_message("成功")
        SessionStateManager.set_processing_status("処理中", 0.7)
        
        SessionStateManager.clear_messages()
        
        self.assertEqual(streamlit_mock.session_state['error_message'], "")
        self.assertEqual(streamlit_mock.session_state['success_message'], "")
        self.assertEqual(streamlit_mock.session_state['processing_message'], "")
        self.assertEqual(streamlit_mock.session_state['progress_value'], 0.0)

    def test_is_processing_idle(self):
        """処理中判定テスト（アイドル状態）"""
        SessionStateManager.set_app_state("idle")
        self.assertFalse(SessionStateManager.is_processing())

    def test_is_processing_qa(self):
        """処理中判定テスト（QA処理中）"""
        SessionStateManager.set_app_state("processing_qa")
        self.assertTrue(SessionStateManager.is_processing())

    def test_is_processing_indexing(self):
        """処理中判定テスト（インデックス処理中）"""
        SessionStateManager.set_app_state("processing_indexing")
        self.assertTrue(SessionStateManager.is_processing())

    def test_is_cancel_requested_false(self):
        """キャンセル要求判定テスト（False）"""
        SessionStateManager.set_app_state("idle", cancel_requested=False)
        self.assertFalse(SessionStateManager.is_cancel_requested())

    def test_is_cancel_requested_true(self):
        """キャンセル要求判定テスト（True）"""
        SessionStateManager.set_app_state("processing_qa", cancel_requested=True)
        self.assertTrue(SessionStateManager.is_cancel_requested())

    def test_reset_cancel_request(self):
        """キャンセル要求リセットテスト"""
        SessionStateManager.set_app_state("processing_qa", cancel_requested=True)
        self.assertTrue(SessionStateManager.is_cancel_requested())
        
        SessionStateManager.reset_cancel_request()
        self.assertFalse(SessionStateManager.is_cancel_requested())

    def test_chat_message_dataclass(self):
        """ChatMessageデータクラステスト"""
        message = ChatMessage(
            role="assistant",
            content="回答です",
            timestamp="2025-08-30T12:00:00",
            sources=["doc1.pdf", "doc2.txt"]
        )
        
        self.assertEqual(message.role, "assistant")
        self.assertEqual(message.content, "回答です")
        self.assertEqual(message.timestamp, "2025-08-30T12:00:00")
        self.assertEqual(message.sources, ["doc1.pdf", "doc2.txt"])

    def test_app_state_dataclass(self):
        """AppStateデータクラステスト"""
        app_state = AppState(
            app_state="processing_indexing",
            cancel_requested=True,
            current_page="settings"
        )
        
        self.assertEqual(app_state.app_state, "processing_indexing")
        self.assertEqual(app_state.cancel_requested, True)
        self.assertEqual(app_state.current_page, "settings")

    def test_init_session_state_function(self):
        """init_session_state関数テスト"""
        # debug_infoのsession_start_timeをNoneに設定
        streamlit_mock.session_state['debug_info']['session_start_time'] = None
        
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2025-08-30T12:00:00"
            
            init_session_state()
            
            # セッション開始時間が設定されることを確認
            self.assertEqual(
                streamlit_mock.session_state['debug_info']['session_start_time'],
                "2025-08-30T12:00:00"
            )

    def test_concurrent_state_operations(self):
        """状態の同時操作テスト"""
        # 複数の状態変更を同時に実行
        SessionStateManager.set_app_state("processing_qa", cancel_requested=True)
        SessionStateManager.add_chat_message("user", "質問")
        SessionStateManager.set_processing_status("処理中", 0.3)
        SessionStateManager.set_config("test_setting", "test_value")
        
        # 全ての状態が正しく設定されることを確認
        self.assertTrue(SessionStateManager.is_processing())
        self.assertTrue(SessionStateManager.is_cancel_requested())
        self.assertEqual(len(streamlit_mock.session_state['chat_history']), 1)
        self.assertEqual(streamlit_mock.session_state['processing_message'], "処理中")
        self.assertEqual(SessionStateManager.get_config("test_setting"), "test_value")


if __name__ == '__main__':
    unittest.main()