"""
ナビゲーションコンポーネント実装（設計書準拠）
Streamlitサイドバーを使用した画面間ナビゲーション機能を提供
"""

import streamlit as st
from typing import Optional, Dict, Any

from src.utils.session_state import SessionStateManager, AppState
from src.exceptions.base_exceptions import create_error_handler


class Navigation:
    """
    ナビゲーションコンポーネントクラス
    
    サイドバーでのページ選択、状態表示、キャンセル機能を提供
    """
    
    def __init__(self):
        """ナビゲーションコンポーネントを初期化"""
        self._page_mapping = {
            "メイン": "main",
            "設定": "settings"
        }
        self._page_icons = {
            "メイン": "💬",
            "設定": "⚙️"
        }
    
    @create_error_handler("general")
    def render(self) -> str:
        """
        ナビゲーション全体をレンダリング
        
        Returns:
            str: 選択されたページ ("main" または "settings")
        """
        try:
            # サイドバーヘッダー
            st.sidebar.title("📚 LocalKnowledgeAgent")
            st.sidebar.markdown("---")
            
            # ナビゲーション
            current_page = self.render_sidebar()
            
            # ステータス表示
            self.render_status()
            
            # プログレス表示
            self.render_progress()
            
            # キャンセルボタン
            self.render_cancel_button()
            
            # メッセージ表示
            self.render_messages()
            
            # デバッグ情報（開発時のみ）
            if st.sidebar.checkbox("デバッグ情報表示", key="show_debug"):
                self.render_debug_info()
            
            return current_page
            
        except Exception as e:
            st.sidebar.error(f"ナビゲーションエラー: {str(e)}")
            return "main"  # デフォルトページ
    
    def render_sidebar(self) -> str:
        """
        サイドバーのメインナビゲーションをレンダリング
        
        Returns:
            str: 選択されたページID
        """
        app_state = SessionStateManager.get_app_state()
        
        # 処理中は画面遷移を無効化
        is_processing = SessionStateManager.is_processing()
        
        # 現在のページインデックスを取得
        current_page_name = self._get_page_name_from_id(app_state.current_page)
        page_options = list(self._page_mapping.keys())
        current_index = 0
        
        if current_page_name in page_options:
            current_index = page_options.index(current_page_name)
        
        # ナビゲーションラジオボタン
        page_options_with_icons = [
            f"{self._page_icons.get(page, '')} {page}" 
            for page in page_options
        ]
        
        selected_page_with_icon = st.sidebar.radio(
            "ページ選択",
            page_options_with_icons,
            index=current_index,
            disabled=is_processing,
            help="処理中のため画面遷移は無効です" if is_processing else None
        )
        
        # アイコンを除去してページ名を取得
        selected_page = selected_page_with_icon.split(" ", 1)[1] if " " in selected_page_with_icon else selected_page_with_icon
        
        # セッションステートを更新
        selected_page_id = self._page_mapping.get(selected_page, "main")
        SessionStateManager.set_app_state(
            app_state.app_state,
            app_state.cancel_requested,
            selected_page_id
        )
        
        return selected_page_id
    
    def get_current_page(self) -> str:
        """
        現在選択されているページを取得
        
        Returns:
            str: 現在のページID
        """
        # サイドバーから直接値を取得する方式
        # 実際のStreamlitでは最新の値を取得
        page_options = [f"{self._page_icons.get(page, '')} {page}" for page in list(self._page_mapping.keys())]
        
        if hasattr(st.sidebar, 'radio') and hasattr(st.sidebar.radio, 'return_value'):
            selected_page_with_icon = st.sidebar.radio.return_value
            selected_page = selected_page_with_icon.split(" ", 1)[1] if " " in selected_page_with_icon else selected_page_with_icon
            return self._page_mapping.get(selected_page, "main")
        
        # フォールバック: セッションステートから取得
        app_state = SessionStateManager.get_app_state()
        return app_state.current_page
    
    def render_status(self) -> None:
        """処理ステータスを表示"""
        app_state = SessionStateManager.get_app_state()
        
        if app_state.app_state != "idle":
            processing_message = st.session_state.get('processing_message', '')
            if processing_message:
                st.sidebar.info(f"🔄 {processing_message}")
    
    def render_progress(self) -> None:
        """プログレスバーを表示"""
        progress_value = st.session_state.get('progress_value', 0.0)
        
        if progress_value > 0.0:
            st.sidebar.progress(progress_value)
    
    def render_cancel_button(self) -> bool:
        """
        キャンセルボタンを表示
        
        Returns:
            bool: キャンセルボタンがクリックされた場合True
        """
        if SessionStateManager.is_processing():
            cancel_clicked = st.sidebar.button(
                "⛔ キャンセル",
                key="cancel_button",
                help="現在の処理をキャンセルします"
            )
            
            if cancel_clicked:
                # キャンセルフラグを設定
                app_state = SessionStateManager.get_app_state()
                SessionStateManager.set_app_state(
                    app_state.app_state,
                    cancel_requested=True,
                    current_page=app_state.current_page
                )
                st.sidebar.warning("キャンセル要求を送信しました...")
                return True
        
        return False
    
    def render_messages(self) -> None:
        """エラー・成功メッセージを表示"""
        error_message = st.session_state.get('error_message', '')
        success_message = st.session_state.get('success_message', '')
        
        if error_message:
            st.sidebar.error(error_message)
            # エラーメッセージは一度表示したらクリア
            if st.sidebar.button("エラーを閉じる", key="close_error"):
                SessionStateManager.set_error_message("")
                st.rerun()
        
        if success_message:
            st.sidebar.success(success_message)
            # 成功メッセージは一定時間後に自動でクリア
            if st.sidebar.button("メッセージを閉じる", key="close_success"):
                SessionStateManager.set_success_message("")
                st.rerun()
    
    def render_debug_info(self) -> None:
        """デバッグ情報を表示"""
        st.sidebar.markdown("---")
        st.sidebar.subheader("🐛 デバッグ情報")
        
        app_state = SessionStateManager.get_app_state()
        
        debug_data = {
            "アプリケーション状態": app_state.app_state,
            "キャンセル要求": app_state.cancel_requested,
            "現在のページ": app_state.current_page,
            "処理中": SessionStateManager.is_processing(),
            "チャット履歴数": len(st.session_state.get('chat_history', [])),
        }
        
        for key, value in debug_data.items():
            st.sidebar.text(f"{key}: {value}")
        
        # セッションステートの詳細表示
        if st.sidebar.expander("セッションステート詳細"):
            st.sidebar.json(dict(st.session_state))
    
    def _get_page_name_from_id(self, page_id: str) -> str:
        """
        ページIDからページ名を取得
        
        Args:
            page_id: ページID ("main", "settings")
            
        Returns:
            str: ページ名 ("メイン", "設定")
        """
        for name, id_val in self._page_mapping.items():
            if id_val == page_id:
                return name
        return "メイン"  # デフォルト
    
    @staticmethod
    def set_page(page: str) -> None:
        """
        プログラムからページを変更
        
        Args:
            page: 変更先ページID ("main", "settings")
        """
        app_state = SessionStateManager.get_app_state()
        SessionStateManager.set_app_state(
            app_state.app_state,
            app_state.cancel_requested,
            page
        )
    
    @staticmethod
    def is_current_page(page: str) -> bool:
        """
        指定ページが現在選択されているかチェック
        
        Args:
            page: チェックするページID
            
        Returns:
            bool: 現在のページの場合True
        """
        app_state = SessionStateManager.get_app_state()
        return app_state.current_page == page