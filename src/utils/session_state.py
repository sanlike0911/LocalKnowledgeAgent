"""
Streamlitセッションステート初期化機能モジュール
設計書準拠のセッションステート管理を提供
"""


import logging
from dataclasses import asdict, dataclass
from typing import Any, List, Optional, cast

import streamlit as st


@dataclass
class ChatMessage:
    """チャットメッセージクラス"""

    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str
    sources: Optional[List[str]] = None


@dataclass
class AppState:
    """アプリケーション状態クラス"""

    app_state: str = "idle"  # 'idle', 'processing_qa', 'processing_indexing'
    cancel_requested: bool = False
    current_page: str = "main"  # 'main', 'settings'


class SessionStateManager:
    """セッションステート管理クラス"""

    DEFAULT_STATES = {
        # アプリケーション状態
        "app_state": AppState(),
        # チャット履歴
        "chat_history": [],
        # 設定
        "config": {
            "ollama_host": "http://localhost:11434",
            "ollama_model": "llama3:8b",
            "chroma_db_path": "./data/chroma_db",
            "chroma_collection_name": "knowledge_base",
            "max_chat_history": 50,
            "selected_folders": [],
            # 'not_created', 'creating', 'created', 'error'
            "index_status": "not_created",
        },
        # UI状態
        "processing_message": "",
        "progress_value": 0.0,
        "error_message": "",
        "success_message": "",
        # ファイル管理
        "uploaded_files": [],
        "indexed_documents": [],
        "last_index_update": None,
        # フォーム状態
        "form_data": {},
        # デバッグ情報
        "debug_info": {
            "last_error": None,
            "performance_metrics": {},
            "session_start_time": None,
        },
    }

    @classmethod
    def initialize_session_state(cls) -> None:
        """
        セッションステートを初期化
        """
        for key, default_value in cls.DEFAULT_STATES.items():
            if key not in st.session_state:
                st.session_state[key] = (
                    default_value.copy()
                    if isinstance(default_value, (dict, list))
                    else default_value
                )
                logging.info(f"セッションステート初期化: {key}")

    @classmethod
    def get_app_state(cls) -> AppState:
        """
        アプリケーション状態を取得

        Returns:
            AppState: 現在のアプリケーション状態
        """
        if "app_state" not in st.session_state:
            st.session_state.app_state = AppState()
        return cast(AppState, st.session_state.app_state)

    @classmethod
    def set_app_state(
        cls,
        state: str,
        cancel_requested: bool = False,
        current_page: Optional[str] = None,
    ) -> None:
        """
        アプリケーション状態を設定

        Args:
            state: アプリケーション状態 ('idle', 'processing_qa', 'processing_indexing')
            cancel_requested: キャンセル要求フラグ
            current_page: 現在のページ
        """
        app_state = cls.get_app_state()
        app_state.app_state = state
        app_state.cancel_requested = cancel_requested
        if current_page:
            app_state.current_page = current_page

        st.session_state.app_state = app_state
        logging.info(f"アプリケーション状態変更: {state}")

    @classmethod
    def add_chat_message(
        cls, role: str, content: str, sources: Optional[List[str]] = None
    ) -> None:
        """
        チャットメッセージを追加

        Args:
            role: メッセージの役割 ('user' or 'assistant')
            content: メッセージ内容
            sources: 参照ソース一覧
        """
        import datetime

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        message = ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.datetime.now().isoformat(),
            sources=sources,
        )

        st.session_state.chat_history.append(asdict(message))

        # 最大履歴数制限
        max_history = st.session_state.config.get("max_chat_history", 50)
        if len(st.session_state.chat_history) > max_history:
            st.session_state.chat_history = st.session_state.chat_history[-max_history:]

        logging.info(f"チャットメッセージ追加: {role} - {len(content)}文字")

    @classmethod
    def clear_chat_history(cls) -> None:
        """チャット履歴をクリア"""
        st.session_state.chat_history = []
        logging.info("チャット履歴をクリアしました")

    @classmethod
    def get_config(cls, key: str, default: Any = None) -> Any:
        """
        設定値を取得

        Args:
            key: 設定キー
            default: デフォルト値

        Returns:
            設定値
        """
        if "config" not in st.session_state:
            st.session_state.config = cast(dict, cls.DEFAULT_STATES["config"]).copy()

        return st.session_state.config.get(key, default)

    @classmethod
    def set_config(cls, key: str, value: Any) -> None:
        """
        設定値を設定

        Args:
            key: 設定キー
            value: 設定値
        """
        if "config" not in st.session_state:
            st.session_state.config = cast(dict, cls.DEFAULT_STATES["config"]).copy()

        st.session_state.config[key] = value
        logging.info(f"設定更新: {key} = {value}")

    @classmethod
    def set_processing_status(cls, message: str, progress: float = 0.0) -> None:
        """
        処理状況を設定

        Args:
            message: 処理メッセージ
            progress: 進捗率 (0.0-1.0)
        """
        st.session_state.processing_message = message
        st.session_state.progress_value = progress
        logging.info(f"処理状況: {message} ({progress*100:.1f}%)")

    @classmethod
    def set_error_message(cls, message: str) -> None:
        """
        エラーメッセージを設定

        Args:
            message: エラーメッセージ
        """
        st.session_state.error_message = message
        st.session_state.debug_info["last_error"] = message
        logging.error(f"エラー: {message}")

    @classmethod
    def set_success_message(cls, message: str) -> None:
        """
        成功メッセージを設定

        Args:
            message: 成功メッセージ
        """
        st.session_state.success_message = message
        logging.info(f"成功: {message}")

    @classmethod
    def clear_messages(cls) -> None:
        """メッセージをクリア"""
        st.session_state.error_message = ""
        st.session_state.success_message = ""
        st.session_state.processing_message = ""
        st.session_state.progress_value = 0.0

    @classmethod
    def is_processing(cls) -> bool:
        """
        処理中かどうかを判定

        Returns:
            bool: 処理中の場合True
        """
        app_state = cls.get_app_state()
        return app_state.app_state in ["processing_qa", "processing_indexing"]

    @classmethod
    def is_cancel_requested(cls) -> bool:
        """
        キャンセル要求があるかを判定

        Returns:
            bool: キャンセル要求がある場合True
        """
        app_state = cls.get_app_state()
        return app_state.cancel_requested

    @classmethod
    def reset_cancel_request(cls) -> None:
        """キャンセル要求をリセット"""
        app_state = cls.get_app_state()
        app_state.cancel_requested = False
        st.session_state.app_state = app_state


def init_session_state() -> None:
    """
    セッションステート初期化の便利関数
    """
    SessionStateManager.initialize_session_state()

    # セッション開始時間を記録
    if st.session_state.debug_info["session_start_time"] is None:
        import datetime

        st.session_state.debug_info[
            "session_start_time"
        ] = datetime.datetime.now().isoformat()
        logging.info("新しいセッションを開始しました")
