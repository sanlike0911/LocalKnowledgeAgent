"""
メイン画面UI実装 (TDD Green フェーズ)
チャットインターフェース・進捗表示・QAシステム統合機能を提供
"""

import streamlit as st
import logging
import time
from typing import Dict, Any, List, Optional, Iterator
from datetime import datetime
from contextlib import contextmanager

from src.models.chat_history import ChatHistory
from src.utils.session_state import ChatMessage
from src.models.config import Config
from src.logic.qa import RAGPipeline
from src.logic.indexing import ChromaDBIndexer
from src.logic.config_manager import ConfigManager
from src.exceptions.base_exceptions import QAError, IndexingError, ConfigError
from src.utils.structured_logger import get_logger
from src.security.xss_protection import sanitize_user_input
from src.utils.progress_utils import ProgressTracker, should_show_progress
from src.utils.cancellation_utils import CancellableOperation


class StreamlitChatManager:
    """
    Streamlit チャット管理クラス
    
    チャット履歴の表示・更新・管理機能を提供
    """
    
    def __init__(self, indexer=None):
        """Streamlit チャット管理を初期化"""
        self.logger = get_logger(__name__)
        self.indexer = indexer
        
        # セッション状態の初期化
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        if 'processing' not in st.session_state:
            st.session_state.processing = False
        
        if 'cancel_requested' not in st.session_state:
            st.session_state.cancel_requested = False
    
    def display_chat_history(self) -> None:
        """
        チャット履歴を表示
        """
        try:
            chat_history = st.session_state.get('chat_history', [])
            
            if not chat_history:
                return
            
            for message in chat_history:
                role = message.get('role', 'user')
                content = message.get('content', '')
                sources = message.get('sources', [])
                
                with st.chat_message(role):
                    # メッセージ内容を表示
                    st.write(content)
                    
                    # アシスタントメッセージの場合、ソース情報も表示
                    if role == 'assistant' and sources:
                        self._display_sources(sources)
                        
        except Exception as e:
            self.logger.error(f"チャット履歴表示エラー: {e}")
            st.error("チャット履歴の表示中にエラーが発生しました。")
    
    def _display_sources(self, sources: List[Dict[str, Any]]) -> None:
        """
        ソース情報を表示
        
        Args:
            sources: ソース情報リスト
        """
        if not sources:
            return
        
        with st.expander(f"📚 参考ソース ({len(sources)}件)", expanded=False):
            for i, source in enumerate(sources, 1):
                # ChromaDBから取得したmetadataを確認
                metadata = source.get('metadata', {})
                filename = metadata.get('document_filename') or source.get('filename', '不明なファイル')
                distance = source.get('distance', 0.0)
                preview = source.get('content_preview', '')
                
                # ファイル名表示の改善
                if filename == '不明なファイル' or filename == '不明':
                    # メタデータから他の情報を試す
                    chunk_index = metadata.get('chunk_index', 0)
                    filename = f"文書 {i} (チャンク{chunk_index})"
                
                st.markdown(f"**{i}. {filename}**")
                
                # 距離値から類似度への変換を改善
                similarity_score = self._calculate_similarity_score(distance)
                st.markdown(f"類似度: {similarity_score}")
                
                if preview:
                    st.markdown(f"内容: {preview}")
                
                if i < len(sources):
                    st.markdown("---")
    
    def _calculate_similarity_score(self, distance: float) -> str:
        """
        距離値から類似度スコアを計算
        
        Args:
            distance: ChromaDBから返される距離値
            
        Returns:
            str: フォーマットされた類似度表示
        """
        try:
            # 距離値の範囲チェック
            if distance < 0:
                return "計算不可 (負の距離値)"
            elif distance > 100:
                # 異常に大きな距離値の場合、正規化を試みる
                # ChromaDBのコサイン距離は通常0-2の範囲だが、
                # 異常値の場合は別の計算方式を使用
                if distance > 1000:
                    return "低 (距離値異常)"
                else:
                    # 正規化を試す
                    normalized_distance = min(distance / 100.0, 2.0)
                    similarity_percent = max(0, (2.0 - normalized_distance) / 2.0 * 100)
                    return f"{similarity_percent:.1f}% (正規化済み)"
            elif distance <= 2.0:
                # 正常な範囲の距離値（コサイン距離：0-2）
                similarity_percent = max(0, (2.0 - distance) / 2.0 * 100)
                return f"{similarity_percent:.1f}%"
            else:
                # 2を超える場合
                return f"低 (距離値: {distance:.2f})"
                
        except Exception as e:
            return f"計算エラー ({str(e)})"
    
    def add_user_message(self, message: str) -> None:
        """
        ユーザーメッセージをチャット履歴に追加
        
        Args:
            message: ユーザーメッセージ
        """
        try:
            chat_entry = {
                'role': 'user',
                'content': message,
                'timestamp': datetime.now().isoformat()
            }
            
            st.session_state.chat_history.append(chat_entry)
            
            self.logger.info("ユーザーメッセージ追加", extra={
                "message_length": len(message),
                "history_count": len(st.session_state.chat_history)
            })
            
        except Exception as e:
            self.logger.error(f"ユーザーメッセージ追加エラー: {e}")
    
    def add_assistant_message(
        self,
        message: str,
        sources: Optional[List[Dict[str, Any]]] = None,
        processing_time: Optional[float] = None
    ) -> None:
        """
        アシスタントメッセージをチャット履歴に追加
        
        Args:
            message: アシスタントメッセージ
            sources: ソース情報リスト
            processing_time: 処理時間（秒）
        """
        try:
            chat_entry = {
                'role': 'assistant',
                'content': message,
                'timestamp': datetime.now().isoformat()
            }
            
            if sources:
                chat_entry['sources'] = sources
            
            if processing_time:
                chat_entry['processing_time'] = processing_time
            
            st.session_state.chat_history.append(chat_entry)
            
            self.logger.info("アシスタントメッセージ追加", extra={
                "message_length": len(message),
                "sources_count": len(sources) if sources else 0,
                "processing_time": processing_time
            })
            
        except Exception as e:
            self.logger.error(f"アシスタントメッセージ追加エラー: {e}")
    
    def clear_chat_history(self) -> None:
        """チャット履歴をクリア"""
        try:
            history_count = len(st.session_state.get('chat_history', []))
            st.session_state.chat_history = []
            
            self.logger.info(f"チャット履歴クリア完了: {history_count}件削除")
            
        except Exception as e:
            self.logger.error(f"チャット履歴クリアエラー: {e}")
    
    def get_conversation_history_for_qa(self) -> List[Dict[str, str]]:
        """
        QAシステム用の会話履歴を取得
        
        Returns:
            List[Dict[str, str]]: QA用会話履歴
        """
        try:
            chat_history = st.session_state.get('chat_history', [])
            
            # アシスタントの回答まで含む履歴のみを抽出
            qa_history = []
            for message in chat_history:
                if message['role'] in ['user', 'assistant']:
                    qa_history.append({
                        'role': message['role'],
                        'content': message['content']
                    })
            
            # 最後がユーザーメッセージの場合は除外（現在処理中のため）
            if qa_history and qa_history[-1]['role'] == 'user':
                qa_history = qa_history[:-1]
            
            return qa_history[-10:]  # 直近10件のみ
            
        except Exception as e:
            self.logger.error(f"会話履歴取得エラー: {e}")
            return []
    
    def handle_chat_input(self, placeholder: str = "質問を入力してください...") -> Optional[str]:
        """
        チャット入力を処理
        
        Args:
            placeholder: 入力欄のプレースホルダー
            
        Returns:
            Optional[str]: 入力された質問（なければNone）
        """
        try:
            # 処理中は入力を無効化
            disabled = st.session_state.get('processing', False)
            
            user_input = st.chat_input(
                placeholder=placeholder,
                disabled=disabled
            )
            
            # 空の入力や空白のみの入力を除外
            if user_input and user_input.strip():
                return user_input.strip()
            
            return None
            
        except Exception as e:
            self.logger.error(f"チャット入力処理エラー: {e}")
            return None


class MainView(CancellableOperation):
    """
    メイン画面UI クラス
    
    Streamlit メイン画面の表示・操作・QAシステム統合を管理
    """
    
    def __init__(self, indexer=None):
        """メイン画面UIを初期化"""
        super().__init__("Main View")
        
        self.logger = get_logger(__name__)
        self.chat_manager = StreamlitChatManager()
        self.indexer = indexer
        
        # RAGパイプラインとIndexerを初期化
        self._initialize_qa_system()
        
        self.logger.info("メイン画面UI初期化完了")
    
    def _initialize_qa_system(self) -> None:
        """QAシステムを初期化"""
        try:
            # 設定管理
            config_manager = ConfigManager()
            config = config_manager.load_config()
            
            # ChromaDBインデクサーが渡されていない場合のみ初期化
            if self.indexer is None:
                self.indexer = ChromaDBIndexer(
                    collection_name="knowledge_base", 
                    db_path=config.chroma_db_path,
                    embedding_model="nomic-embed-text"
                )
            
            # RAGパイプライン初期化
            self.rag_pipeline = RAGPipeline(
                indexer=self.indexer,
                model_name=config.ollama_model
            )
            
            self.config = config
            
        except Exception as e:
            self.logger.error(f"QAシステム初期化エラー: {e}")
            self.indexer = None
            self.rag_pipeline = None
            self.config = Config()  # デフォルト設定
    
    def render(self) -> None:
        """メイン画面を描画"""
        try:
            self._render_header()
            self._render_system_status()
            self._render_chat_interface()
            self._render_sidebar()
            
        except Exception as e:
            self.logger.error(f"メイン画面描画エラー: {e}")
            st.error("画面の描画中にエラーが発生しました。ページを再読み込みしてください。")
    
    def _render_header(self) -> None:
        """ヘッダー部分を描画"""
        st.title("🤖 LocalKnowledgeAgent")
        st.markdown("**ローカル知識ベース対応AIアシスタント**")
        
        # システム健康状態の簡易表示
        if self.rag_pipeline:
            health_status = self.rag_pipeline.check_system_health()
            status_emoji = "🟢" if health_status['overall_status'] == 'healthy' else "🟡" if health_status['overall_status'] == 'degraded' else "🔴"
            st.markdown(f"システム状態: {status_emoji} {health_status['overall_status'].title()}")
        
        st.markdown("---")
    
    def _render_system_status(self) -> None:
        """システム状態を描画"""
        if not self.rag_pipeline:
            st.warning("⚠️ QAシステムが初期化されていません。設定を確認してください。")
            return
        
        # インデックス統計情報
        try:
            stats = self.indexer.get_collection_stats()
            doc_count = stats.get('document_count', 0)
            
            if doc_count == 0:
                st.info("📚 まだドキュメントがインデックスされていません。設定画面からドキュメントを追加してください。")
            else:
                st.success(f"📚 {doc_count}件のドキュメントが利用可能です")
                
        except Exception as e:
            st.error(f"システム状態の確認中にエラーが発生しました: {e}")
    
    def _render_chat_interface(self) -> None:
        """チャットインターフェースを描画"""
        # チャット履歴表示
        self.chat_manager.display_chat_history()
        
        # チャット入力処理
        if user_input := self.chat_manager.handle_chat_input():
            self._process_user_input(user_input)
    
    def _process_user_input(self, user_input: str) -> None:
        """
        ユーザー入力を処理
        
        Args:
            user_input: ユーザー入力
        """
        try:
            # XSS対策：入力をサニタイズ
            sanitized_input = sanitize_user_input(user_input, allow_markdown=False)
            if sanitized_input != user_input:
                self.logger.warning("ユーザー入力をサニタイズしました", extra={
                    "original_length": len(user_input),
                    "sanitized_length": len(sanitized_input)
                })
            
            # ユーザーメッセージを履歴に追加（サニタイズ済み）
            self.chat_manager.add_user_message(sanitized_input)
            
            # ユーザーメッセージを即座に表示
            with st.chat_message("user"):
                st.write(sanitized_input)
            
            # QAシステムが利用可能かチェック
            if not self.rag_pipeline:
                with st.chat_message("assistant"):
                    st.error("QAシステムが利用できません。システム管理者にお問い合わせください。")
                return
            
            # ストリーミング対応の回答生成（サニタイズ済み入力を使用）
            if getattr(self.config, 'enable_streaming', True):
                self._process_streaming_question(sanitized_input)
            else:
                self._process_standard_question(sanitized_input)
                
        except Exception as e:
            self.logger.error(f"ユーザー入力処理エラー: {e}")
            with st.chat_message("assistant"):
                st.error("質問の処理中にエラーが発生しました。もう一度お試しください。")
    
    def _process_standard_question(self, question: str) -> None:
        """
        標準的な質問処理
        
        Args:
            question: 質問内容
        """
        try:
            st.session_state.processing = True
            
            with st.chat_message("assistant"):
                with self.show_spinner("回答を生成中..."):
                    
                    # 会話履歴を取得
                    conversation_history = self.chat_manager.get_conversation_history_for_qa()
                    
                    # QA実行
                    qa_result = self.rag_pipeline.answer_question(
                        question,
                        conversation_history=conversation_history,
                        top_k=getattr(self.config, 'max_search_results', 5)
                    )
                    
                    if qa_result:
                        # 回答表示
                        st.write(qa_result['answer'])
                        
                        # ソース情報表示
                        if qa_result.get('sources'):
                            self.chat_manager._display_sources(qa_result['sources'])
                        
                        # 処理時間表示
                        processing_time = qa_result.get('processing_time', 0)
                        if processing_time > 0:
                            st.caption(f"⏱️ 処理時間: {processing_time:.1f}秒")
                        
                        # 履歴に追加
                        self.chat_manager.add_assistant_message(
                            qa_result['answer'],
                            qa_result.get('sources', []),
                            processing_time
                        )
                    else:
                        st.error("回答の生成に失敗しました。")
                        
        except QAError as e:
            self.logger.error(f"QAエラー: {e}")
            st.error(f"質問の処理中にエラーが発生しました: {e}")
            
        except Exception as e:
            self.logger.error(f"質問処理エラー: {e}")
            st.error("予期しないエラーが発生しました。もう一度お試しください。")
            
        finally:
            st.session_state.processing = False
    
    def _process_streaming_question(self, question: str) -> None:
        """
        ストリーミング質問処理
        
        Args:
            question: 質問内容
        """
        try:
            st.session_state.processing = True
            st.session_state.cancel_requested = False
            
            with st.chat_message("assistant"):
                # プレースホルダーを作成
                answer_placeholder = st.empty()
                sources_placeholder = st.empty()
                status_placeholder = st.empty()
                
                # キャンセルボタン
                cancel_col1, cancel_col2 = st.columns([1, 4])
                with cancel_col1:
                    cancel_button = st.button("⏹️ キャンセル", key=f"cancel_{time.time()}")
                
                if cancel_button:
                    st.session_state.cancel_requested = True
                
                # 会話履歴を取得
                conversation_history = self.chat_manager.get_conversation_history_for_qa()
                
                # ストリーミング実行
                full_answer = ""
                sources = []
                processing_start = time.time()
                
                try:
                    stream = self.rag_pipeline.answer_question_stream(
                        question,
                        conversation_history=conversation_history,
                        top_k=getattr(self.config, 'max_search_results', 5)
                    )
                    
                    for chunk in stream:
                        # キャンセル確認
                        if st.session_state.get('cancel_requested', False):
                            status_placeholder.warning("⏹️ 処理がキャンセルされました")
                            return
                        
                        chunk_type = chunk.get('type', 'unknown')
                        
                        if chunk_type == 'sources':
                            sources = chunk.get('sources', [])
                            
                        elif chunk_type == 'content':
                            content = chunk.get('content', '')
                            full_answer += content
                            
                            # リアルタイム更新
                            answer_placeholder.write(full_answer)
                            
                        elif chunk_type == 'complete':
                            full_answer = chunk.get('answer', full_answer)
                            break
                            
                        elif chunk_type == 'error':
                            error_msg = chunk.get('error', '不明なエラー')
                            status_placeholder.error(f"エラー: {error_msg}")
                            return
                    
                    # 最終結果表示
                    answer_placeholder.write(full_answer)
                    
                    if sources:
                        self.chat_manager._display_sources(sources)
                    
                    processing_time = time.time() - processing_start
                    status_placeholder.caption(f"⏱️ 処理時間: {processing_time:.1f}秒")
                    
                    # 履歴に追加
                    self.chat_manager.add_assistant_message(
                        full_answer,
                        sources,
                        processing_time
                    )
                    
                except Exception as e:
                    self.logger.error(f"ストリーミング処理エラー: {e}")
                    status_placeholder.error("ストリーミング処理中にエラーが発生しました")
                    
        except Exception as e:
            self.logger.error(f"ストリーミング質問処理エラー: {e}")
            st.error("質問の処理中にエラーが発生しました")
            
        finally:
            st.session_state.processing = False
            st.session_state.cancel_requested = False
    
    def _render_sidebar(self) -> None:
        """サイドバーを描画"""
        with st.sidebar:
            st.header("🛠️ 操作")
            
            # チャット履歴クリア
            if st.button("🗑️ チャット履歴をクリア", use_container_width=True):
                self.chat_manager.clear_chat_history()
                st.rerun()
            
            st.markdown("---")
            
            # システム情報
            st.header("📊 システム情報")
            
            if self.rag_pipeline:
                health_status = self.rag_pipeline.check_system_health()
                
                st.json({
                    "システム状態": health_status['overall_status'],
                    "ChromaDB": health_status['components'].get('chromadb', {}).get('status', 'unknown'),
                    "Ollama": health_status['components'].get('ollama', {}).get('status', 'unknown'),
                    "ドキュメント数": health_status['components'].get('chromadb', {}).get('document_count', 0)
                })
            else:
                st.error("システム情報を取得できません")
            
            st.markdown("---")
            
            # 設定情報
            st.header("⚙️ 現在の設定")
            
            config_summary = {
                "モデル": getattr(self.config, 'ollama_model', 'llama3:8b'),
                "最大検索結果数": getattr(self.config, 'max_search_results', 5),
                "ストリーミング": "有効" if getattr(self.config, 'enable_streaming', True) else "無効",
                "言語": getattr(self.config, 'language', 'ja')
            }
            
            st.json(config_summary)
    
    # ユーティリティメソッド
    
    @contextmanager
    def show_spinner(self, message: str):
        """
        スピナー表示のコンテキストマネージャー
        
        Args:
            message: スピナーメッセージ
        """
        with st.spinner(message):
            yield
    
    def show_progress_bar(self, progress: float, message: str = "") -> None:
        """
        進捗バーを表示
        
        Args:
            progress: 進捗（0.0-1.0）
            message: 進捗メッセージ
        """
        st.progress(progress)
        if message:
            st.text(message)
    
    def show_status(self, message: str, status_type: str = "info") -> None:
        """
        ステータスメッセージを表示
        
        Args:
            message: ステータスメッセージ
            status_type: ステータスタイプ（info, success, warning, error）
        """
        if status_type == "success":
            st.success(message)
        elif status_type == "warning":
            st.warning(message)
        elif status_type == "error":
            st.error(message)
        else:
            st.info(message)
    
    def show_cancel_button(self, key: Optional[str] = None) -> bool:
        """
        キャンセルボタンを表示
        
        Args:
            key: ボタンのキー
            
        Returns:
            bool: ボタンがクリックされた場合True
        """
        return st.button("⏹️ キャンセル", key=key)
    
    def update_progress_with_cancellation(self, progress: float, message: str) -> bool:
        """
        キャンセル確認付きで進捗を更新
        
        Args:
            progress: 進捗（0.0-1.0）
            message: 進捗メッセージ
            
        Returns:
            bool: キャンセルが要求された場合True
        """
        self.show_progress_bar(progress, message)
        return self.show_cancel_button()
    
    # QAシステム統合メソッド
    
    def process_question(self, question: str) -> Optional[Dict[str, Any]]:
        """
        質問を処理（非ストリーミング）
        
        Args:
            question: 質問内容
            
        Returns:
            Optional[Dict[str, Any]]: QA結果
        """
        try:
            if not self.rag_pipeline:
                return None
            
            conversation_history = self.chat_manager.get_conversation_history_for_qa()
            
            with self.show_spinner("回答を生成中..."):
                result = self.rag_pipeline.answer_question(
                    question,
                    conversation_history=conversation_history
                )
            
            return result
            
        except QAError as e:
            self.logger.error(f"QAエラー: {e}", exc_info=True)
            self.show_status(f"質問の処理中にエラーが発生しました: {e}", "error")
            return None
        except Exception as e:
            self.logger.error(f"質問処理エラー: {e}", exc_info=True)
            self.show_status("予期しないエラーが発生しました", "error")
            return None
    
    def process_streaming_question(self, question: str) -> Optional[Iterator[Dict[str, Any]]]:
        """
        ストリーミング形式で質問を処理
        
        Args:
            question: 質問内容
            
        Returns:
            Optional[Iterator[Dict[str, Any]]]: ストリーミング結果
        """
        try:
            if not self.rag_pipeline:
                return None
            
            conversation_history = self.chat_manager.get_conversation_history_for_qa()
            
            return self.rag_pipeline.answer_question_stream(
                question,
                conversation_history=conversation_history
            )
            
        except Exception as e:
            self.logger.error(f"ストリーミング質問処理エラー: {e}")
            self.show_status("ストリーミング処理中にエラーが発生しました", "error")
            return None
    
    def process_streaming_question_with_cancel(self, question: str) -> Optional[Dict[str, Any]]:
        """
        キャンセル機能付きストリーミング質問処理
        
        Args:
            question: 質問内容
            
        Returns:
            Optional[Dict[str, Any]]: 処理結果（キャンセル時はNone）
        """
        try:
            stream = self.process_streaming_question(question)
            if not stream:
                return None
            
            result = None
            for chunk in stream:
                # キャンセル確認（実装時にUIロジックと連携）
                if self.show_cancel_button():
                    return None
                
                if chunk.get('type') == 'complete':
                    result = chunk
                    break
            
            return result
            
        except Exception as e:
            self.logger.error(f"キャンセル付きストリーミング処理エラー: {e}")
            return None
    
    def display_qa_result(self, qa_result: Dict[str, Any]) -> None:
        """
        QA結果を表示
        
        Args:
            qa_result: QA結果
        """
        try:
            with st.chat_message("assistant"):
                # 回答表示
                answer = qa_result.get('answer', '')
                st.write(answer)
                
                # ソース情報表示
                sources = qa_result.get('sources', [])
                if sources:
                    self.chat_manager._display_sources(sources)
                
                # 処理時間表示
                processing_time = qa_result.get('processing_time', 0)
                if processing_time > 0:
                    st.caption(f"⏱️ 処理時間: {processing_time:.1f}秒")
                    
        except Exception as e:
            self.logger.error(f"QA結果表示エラー: {e}")
            st.error("結果の表示中にエラーが発生しました")