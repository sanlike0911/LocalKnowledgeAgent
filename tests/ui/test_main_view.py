"""
メイン画面UIのテストスイート (TDD Red フェーズ)
チャットインターフェース・進捗表示・回答生成機能のテストを定義
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import streamlit as st
from pathlib import Path
import tempfile
import shutil
from typing import Dict, Any, List

from src.models.chat_history import ChatHistory
from src.utils.session_state import ChatMessage
from src.models.config import Config
from src.logic.qa import RAGPipeline
from src.logic.indexing import ChromaDBIndexer
from src.ui.main_view import MainView, StreamlitChatManager


class TestStreamlitChatManager:
    """Streamlit チャット管理のテストスイート"""
    
    def setup_method(self):
        """各テスト前の初期化処理"""
        # Streamlit セッション状態をモック
        self.mock_session_state = {}
        self.chat_manager = StreamlitChatManager()
        
        # パッチ適用
        self.session_state_patcher = patch('streamlit.session_state', self.mock_session_state)
        self.session_state_patcher.start()
    
    def teardown_method(self):
        """各テスト後のクリーンアップ処理"""
        self.session_state_patcher.stop()
    
    # チャット履歴表示テスト
    
    def test_display_chat_history_empty(self):
        """空のチャット履歴表示テスト (Red フェーズ)"""
        # 空のチャット履歴を設定
        self.mock_session_state['chat_history'] = []
        
        with patch('streamlit.chat_message') as mock_chat_message:
            self.chat_manager.display_chat_history()
            
            # チャットメッセージが表示されないことを確認
            mock_chat_message.assert_not_called()
    
    def test_display_chat_history_with_messages(self):
        """メッセージ付きチャット履歴表示テスト (Red フェーズ)"""
        # テスト用チャット履歴を設定
        test_messages = [
            {"role": "user", "content": "Pythonについて教えて"},
            {"role": "assistant", "content": "Pythonは高レベルプログラミング言語です。", "sources": ["python.txt"]},
            {"role": "user", "content": "具体的な特徴は？"},
            {"role": "assistant", "content": "シンプルで読みやすい構文が特徴です。", "sources": ["features.txt"]}
        ]
        self.mock_session_state['chat_history'] = test_messages
        
        with patch('streamlit.chat_message') as mock_chat_message:
            with patch('streamlit.write') as mock_write:
                
                self.chat_manager.display_chat_history()
                
                # 4つのメッセージが表示されることを確認
                assert mock_chat_message.call_count == 4
                
                # ユーザーメッセージの呼び出し確認
                mock_chat_message.assert_any_call("user")
                mock_chat_message.assert_any_call("assistant")
    
    def test_display_chat_history_with_sources(self):
        """ソース付きチャット履歴表示テスト (Red フェーズ)"""
        test_messages = [
            {
                "role": "assistant", 
                "content": "Pythonの特徴について説明します。",
                "sources": [
                    {"filename": "python_intro.txt", "distance": 0.1},
                    {"filename": "python_features.txt", "distance": 0.15}
                ]
            }
        ]
        self.mock_session_state['chat_history'] = test_messages
        
        with patch('streamlit.chat_message') as mock_chat_message:
            with patch('streamlit.write') as mock_write:
                with patch('streamlit.expander') as mock_expander:
                    
                    self.chat_manager.display_chat_history()
                    
                    # アシスタントメッセージが表示されることを確認
                    mock_chat_message.assert_called_with("assistant")
                    
                    # ソース情報の展開表示が呼ばれることを確認
                    mock_expander.assert_called()
    
    def test_add_message_to_history(self):
        """チャット履歴への メッセージ追加テスト (Red フェーズ)"""
        # 初期状態：空の履歴
        self.mock_session_state['chat_history'] = []
        
        # ユーザーメッセージ追加
        user_message = "新しい質問です"
        self.chat_manager.add_user_message(user_message)
        
        # 履歴に追加されたことを確認
        assert len(self.mock_session_state['chat_history']) == 1
        assert self.mock_session_state['chat_history'][0]['role'] == 'user'
        assert self.mock_session_state['chat_history'][0]['content'] == user_message
        
        # アシスタントメッセージ追加
        assistant_response = "回答です"
        sources = [{"filename": "source.txt", "distance": 0.1}]
        self.chat_manager.add_assistant_message(assistant_response, sources)
        
        # 履歴に追加されたことを確認
        assert len(self.mock_session_state['chat_history']) == 2
        assert self.mock_session_state['chat_history'][1]['role'] == 'assistant'
        assert self.mock_session_state['chat_history'][1]['content'] == assistant_response
        assert self.mock_session_state['chat_history'][1]['sources'] == sources
    
    def test_clear_chat_history(self):
        """チャット履歴クリアテスト (Red フェーズ)"""
        # 履歴にメッセージを追加
        self.mock_session_state['chat_history'] = [
            {"role": "user", "content": "質問1"},
            {"role": "assistant", "content": "回答1"}
        ]
        
        # 履歴クリア実行
        self.chat_manager.clear_chat_history()
        
        # 履歴が空になることを確認
        assert len(self.mock_session_state['chat_history']) == 0
    
    def test_get_conversation_history_for_qa(self):
        """QA用会話履歴取得テスト (Red フェーズ)"""
        # テスト用履歴データ
        self.mock_session_state['chat_history'] = [
            {"role": "user", "content": "質問1"},
            {"role": "assistant", "content": "回答1"},
            {"role": "user", "content": "質問2"},
            {"role": "assistant", "content": "回答2"},
            {"role": "user", "content": "質問3"},
        ]
        
        # QA用履歴を取得
        qa_history = self.chat_manager.get_conversation_history_for_qa()
        
        # アシスタントの回答まで含む履歴のみ取得されることを確認
        assert len(qa_history) == 4  # 最後のユーザー質問は除外
        assert qa_history[-1]['role'] == 'assistant'
    
    # チャット入力処理テスト
    
    def test_handle_chat_input_empty(self):
        """空のチャット入力処理テスト (Red フェーズ)"""
        with patch('streamlit.chat_input', return_value=""):
            result = self.chat_manager.handle_chat_input()
            
            # 空の入力は処理されないことを確認
            assert result is None
    
    def test_handle_chat_input_valid(self):
        """有効なチャット入力処理テスト (Red フェーズ)"""
        test_input = "有効な質問です"
        
        with patch('streamlit.chat_input', return_value=test_input):
            result = self.chat_manager.handle_chat_input()
            
            # 入力が返されることを確認
            assert result == test_input
    
    def test_handle_chat_input_whitespace_only(self):
        """空白のみのチャット入力処理テスト (Red フェーズ)"""
        with patch('streamlit.chat_input', return_value="   \n\t  "):
            result = self.chat_manager.handle_chat_input()
            
            # 空白のみの入力は処理されないことを確認
            assert result is None


class TestMainViewProgressDisplay:
    """メイン画面の進捗表示テストスイート"""
    
    def setup_method(self):
        """各テスト前の初期化処理"""
        self.main_view = MainView()
        
        # Streamlit要素をモック
        self.mock_progress = Mock()
        self.mock_spinner = Mock()
        self.mock_status = Mock()
    
    # 進捗表示テスト
    
    def test_show_progress_bar_with_percentage(self):
        """パーセンテージ付き進捗バー表示テスト (Red フェーズ)"""
        with patch('streamlit.progress', return_value=self.mock_progress) as mock_st_progress:
            with patch('streamlit.text') as mock_text:
                
                # 50%の進捗を表示
                self.main_view.show_progress_bar(0.5, "処理中...")
                
                # 進捗バーが作成されることを確認
                mock_st_progress.assert_called_with(0.5)
                
                # 進捗テキストが表示されることを確認
                mock_text.assert_called_with("処理中...")
    
    def test_show_spinner_with_message(self):
        """メッセージ付きスピナー表示テスト (Red フェーズ)"""
        with patch('streamlit.spinner') as mock_st_spinner:
            
            # スピナーを表示
            with self.main_view.show_spinner("データ処理中..."):
                pass
            
            # スピナーが作成されることを確認
            mock_st_spinner.assert_called_with("データ処理中...")
    
    def test_show_status_success(self):
        """成功ステータス表示テスト (Red フェーズ)"""
        with patch('streamlit.success') as mock_success:
            
            self.main_view.show_status("操作が完了しました", "success")
            
            mock_success.assert_called_with("操作が完了しました")
    
    def test_show_status_error(self):
        """エラーステータス表示テスト (Red フェーズ)"""
        with patch('streamlit.error') as mock_error:
            
            self.main_view.show_status("エラーが発生しました", "error")
            
            mock_error.assert_called_with("エラーが発生しました")
    
    def test_show_status_warning(self):
        """警告ステータス表示テスト (Red フェーズ)"""
        with patch('streamlit.warning') as mock_warning:
            
            self.main_view.show_status("注意が必要です", "warning")
            
            mock_warning.assert_called_with("注意が必要です")
    
    def test_show_status_info(self):
        """情報ステータス表示テスト (Red フェーズ)"""
        with patch('streamlit.info') as mock_info:
            
            self.main_view.show_status("情報をお知らせします", "info")
            
            mock_info.assert_called_with("情報をお知らせします")
    
    # キャンセル機能テスト
    
    def test_show_cancel_button(self):
        """キャンセルボタン表示テスト (Red フェーズ)"""
        with patch('streamlit.button', return_value=False) as mock_button:
            
            result = self.main_view.show_cancel_button()
            
            # キャンセルボタンが作成されることを確認
            mock_button.assert_called()
            assert result is False
    
    def test_show_cancel_button_clicked(self):
        """キャンセルボタンクリックテスト (Red フェーズ)"""
        with patch('streamlit.button', return_value=True) as mock_button:
            
            result = self.main_view.show_cancel_button()
            
            # クリック状態が返されることを確認
            assert result is True
    
    def test_update_progress_with_cancellation_check(self):
        """キャンセル確認付き進捗更新テスト (Red フェーズ)"""
        with patch('streamlit.progress') as mock_progress:
            with patch('streamlit.button', return_value=False) as mock_button:
                
                # キャンセルされていない場合
                cancelled = self.main_view.update_progress_with_cancellation(0.3, "進行中...")
                
                assert cancelled is False
                mock_progress.assert_called_with(0.3)
        
        with patch('streamlit.progress') as mock_progress:
            with patch('streamlit.button', return_value=True) as mock_button:
                
                # キャンセルボタンがクリックされた場合
                cancelled = self.main_view.update_progress_with_cancellation(0.7, "進行中...")
                
                assert cancelled is True


class TestMainViewQAIntegration:
    """メイン画面のQAシステム統合テストスイート"""
    
    def setup_method(self):
        """各テスト前の初期化処理"""
        # テスト用ディレクトリ
        self.test_dir = Path(tempfile.mkdtemp())
        
        # モックRAGパイプライン
        self.mock_rag_pipeline = Mock(spec=RAGPipeline)
        
        # メインビューを初期化
        self.main_view = MainView()
        self.main_view.rag_pipeline = self.mock_rag_pipeline
        
        # Streamlit要素をモック
        self.mock_session_state = {}
        self.session_state_patcher = patch('streamlit.session_state', self.mock_session_state)
        self.session_state_patcher.start()
    
    def teardown_method(self):
        """各テスト後のクリーンアップ処理"""
        self.session_state_patcher.stop()
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    # QA処理テスト
    
    def test_process_question_success(self):
        """質問処理成功テスト (Red フェーズ)"""
        # モックQA結果を設定
        mock_qa_result = {
            'query': 'テスト質問',
            'answer': 'テスト回答です',
            'sources': [
                {'filename': 'test.txt', 'distance': 0.1, 'content_preview': 'テスト内容...'}
            ],
            'processing_time': 1.5
        }
        self.mock_rag_pipeline.answer_question.return_value = mock_qa_result
        
        with patch.object(self.main_view, 'show_spinner'):
            with patch.object(self.main_view, 'show_status'):
                
                result = self.main_view.process_question("テスト質問")
                
                # QAパイプラインが呼ばれることを確認
                self.mock_rag_pipeline.answer_question.assert_called_once_with(
                    "テスト質問",
                    conversation_history=None
                )
                
                # 結果が返されることを確認
                assert result == mock_qa_result
    
    def test_process_question_with_history(self):
        """履歴付き質問処理テスト (Red フェーズ)"""
        # チャット履歴を設定
        self.mock_session_state['chat_history'] = [
            {"role": "user", "content": "前の質問"},
            {"role": "assistant", "content": "前の回答"}
        ]
        
        mock_qa_result = {
            'query': '続きの質問',
            'answer': '続きの回答',
            'sources': []
        }
        self.mock_rag_pipeline.answer_question.return_value = mock_qa_result
        
        with patch.object(self.main_view, 'show_spinner'):
            
            result = self.main_view.process_question("続きの質問")
            
            # 履歴付きでQAパイプラインが呼ばれることを確認
            call_args = self.mock_rag_pipeline.answer_question.call_args
            assert call_args[0][0] == "続きの質問"
            assert call_args[1]['conversation_history'] is not None
    
    def test_process_question_error_handling(self):
        """質問処理エラーハンドリングテスト (Red フェーズ)"""
        # QAパイプラインでエラーが発生する場合
        from src.exceptions.base_exceptions import QAError
        self.mock_rag_pipeline.answer_question.side_effect = QAError(
            "QAエラーが発生しました",
            error_code="QA-999"
        )
        
        with patch.object(self.main_view, 'show_spinner'):
            with patch.object(self.main_view, 'show_status') as mock_show_status:
                
                result = self.main_view.process_question("エラーテスト質問")
                
                # エラー結果が返されることを確認
                assert result is None
                
                # エラーステータスが表示されることを確認
                mock_show_status.assert_called_with(
                    "質問の処理中にエラーが発生しました: QAエラーが発生しました",
                    "error"
                )
    
    def test_display_qa_result_with_sources(self):
        """ソース付きQA結果表示テスト (Red フェーズ)"""
        qa_result = {
            'query': 'テスト質問',
            'answer': 'テスト回答です。詳細な説明を含みます。',
            'sources': [
                {
                    'filename': 'document1.txt',
                    'distance': 0.1,
                    'content_preview': 'ドキュメント1の内容プレビュー...'
                },
                {
                    'filename': 'document2.pdf', 
                    'distance': 0.15,
                    'content_preview': 'ドキュメント2の内容プレビュー...'
                }
            ],
            'processing_time': 2.3
        }
        
        with patch('streamlit.chat_message') as mock_chat_message:
            with patch('streamlit.write') as mock_write:
                with patch('streamlit.expander') as mock_expander:
                    with patch('streamlit.markdown') as mock_markdown:
                        
                        self.main_view.display_qa_result(qa_result)
                        
                        # チャットメッセージが表示されることを確認
                        mock_chat_message.assert_called_with("assistant")
                        
                        # 回答内容が表示されることを確認
                        mock_write.assert_called()
                        
                        # ソース展開表示が作成されることを確認
                        mock_expander.assert_called()
    
    def test_display_qa_result_no_sources(self):
        """ソースなしQA結果表示テスト (Red フェーズ)"""
        qa_result = {
            'query': 'テスト質問',
            'answer': 'テスト回答です',
            'sources': [],
            'processing_time': 1.0
        }
        
        with patch('streamlit.chat_message') as mock_chat_message:
            with patch('streamlit.write') as mock_write:
                with patch('streamlit.expander') as mock_expander:
                    
                    self.main_view.display_qa_result(qa_result)
                    
                    # 基本的な表示は行われることを確認
                    mock_chat_message.assert_called_with("assistant")
                    mock_write.assert_called()
                    
                    # ソースがない場合はexpanderは呼ばれない
                    mock_expander.assert_not_called()


class TestMainViewStreamingResponse:
    """メイン画面のストリーミング応答テストスイート"""
    
    def setup_method(self):
        """各テスト前の初期化処理"""
        self.main_view = MainView()
        self.mock_rag_pipeline = Mock(spec=RAGPipeline)
        self.main_view.rag_pipeline = self.mock_rag_pipeline
    
    def test_display_streaming_response(self):
        """ストリーミング応答表示テスト (Red フェーズ)"""
        # ストリーミングレスポンスをモック
        mock_stream_data = [
            {'type': 'sources', 'sources': [{'filename': 'test.txt'}]},
            {'type': 'content', 'content': 'スト', 'done': False},
            {'type': 'content', 'content': 'リー', 'done': False},
            {'type': 'content', 'content': 'ミング', 'done': False},
            {'type': 'content', 'content': 'テスト', 'done': True},
            {'type': 'complete', 'answer': 'ストリーミングテスト'}
        ]
        
        self.mock_rag_pipeline.answer_question_stream.return_value = iter(mock_stream_data)
        
        with patch('streamlit.chat_message') as mock_chat_message:
            with patch('streamlit.empty') as mock_empty:
                with patch('streamlit.expander') as mock_expander:
                    
                    result = self.main_view.process_streaming_question("ストリーミングテスト質問")
                    
                    # ストリーミングQAが呼ばれることを確認
                    self.mock_rag_pipeline.answer_question_stream.assert_called_once()
                    
                    # チャットメッセージ表示が呼ばれることを確認
                    mock_chat_message.assert_called()
                    
                    # 結果が返されることを確認
                    assert result is not None
    
    def test_streaming_response_with_cancellation(self):
        """キャンセル付きストリーミング応答テスト (Red フェーズ)"""
        # 長いストリーミングレスポンスをモック
        def mock_stream_generator():
            for i in range(10):
                yield {'type': 'content', 'content': f'部分{i}', 'done': False}
                # キャンセルボタンのチェックポイント
            yield {'type': 'complete', 'answer': '完全な回答'}
        
        self.mock_rag_pipeline.answer_question_stream.return_value = mock_stream_generator()
        
        with patch('streamlit.chat_message'):
            with patch('streamlit.empty'):
                with patch.object(self.main_view, 'show_cancel_button', side_effect=[False, False, True]) as mock_cancel:
                    
                    result = self.main_view.process_streaming_question_with_cancel("長い質問")
                    
                    # キャンセルボタンが表示されることを確認
                    mock_cancel.assert_called()
                    
                    # キャンセルされた場合の処理確認
                    assert result is None or 'cancelled' in str(result)
    
    def test_streaming_error_handling(self):
        """ストリーミングエラーハンドリングテスト (Red フェーズ)"""
        # ストリーミング中にエラーが発生
        def mock_error_stream():
            yield {'type': 'content', 'content': '開始'}
            raise Exception("ストリーミングエラー")
        
        self.mock_rag_pipeline.answer_question_stream.return_value = mock_error_stream()
        
        with patch('streamlit.chat_message'):
            with patch.object(self.main_view, 'show_status') as mock_show_status:
                
                result = self.main_view.process_streaming_question("エラーテスト")
                
                # エラーステータスが表示されることを確認
                mock_show_status.assert_called_with(
                    "ストリーミング処理中にエラーが発生しました",
                    "error"
                )
                
                # エラー結果が返されることを確認
                assert result is None


class TestMainViewIntegration:
    """メイン画面統合テストスイート"""
    
    def test_full_chat_flow(self):
        """完全なチャットフロー統合テスト (Red フェーズ)"""
        # この統合テストは実際のStreamlit環境での動作確認用
        # 実装完了後に詳細化
        pass
    
    def test_error_recovery_flow(self):
        """エラー回復フロー統合テスト (Red フェーズ)"""
        # エラー発生→回復→正常処理のフロー確認用
        # 実装完了後に詳細化
        pass
    
    def test_performance_with_large_history(self):
        """大きな履歴でのパフォーマンステスト (Red フェーズ)"""
        # 大量の履歴データでの応答性能確認用
        # 実装完了後に詳細化
        pass