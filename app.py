"""
LocalKnowledgeAgent メインアプリケーション
Streamlitベースのデスクトップ知識管理システム

設計書とCLAUDE.md完全準拠の実装
"""

import streamlit as st
import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# 環境変数設定
from src.utils.env_validator import get_app_config

# コア機能インポート
from src.utils.session_state import init_session_state, SessionStateManager
from src.ui.navigation import Navigation
from src.ui.main_view import MainView
from src.ui.settings_view import SettingsView
from src.logic.config_manager import ConfigManager
from src.logic.indexing import ChromaDBIndexer  
from src.logic.qa import QAService
from src.logic.ollama_checker import OllamaModelChecker
from src.exceptions.base_exceptions import (
    LocalKnowledgeAgentError, create_error_handler, ErrorMessages
)
from src.utils.structured_logger import setup_logging
from src.utils.monitoring_integration import initialize_monitoring, log_performance, log_error


class LocalKnowledgeAgentApp:
    """
    LocalKnowledgeAgent メインアプリケーションクラス
    
    全体のアプリケーション制御、画面遷移管理、コンポーネント統合を行う
    """
    
    def __init__(self):
        """アプリケーションを初期化"""
        # 統合監視システムを初期化
        self.monitoring = initialize_monitoring()
        
        self.logger = setup_logging()
        self.navigation = Navigation()
        
        # 各種マネージャーとサービスを初期化
        self._initialize_services()
        
        # Ollamaモデルチェッカー初期化
        self.ollama_checker = OllamaModelChecker()
    
    def _initialize_services(self) -> None:
        """サービス層の初期化"""
        try:
            with log_performance("app_initialization"):
                # 設定管理
                self.config_manager = ConfigManager()
                config = self.config_manager.load_config()
                
                # インデックス管理（Configから埋め込みモデルを取得）
                self.indexer = ChromaDBIndexer(
                    collection_name=config.chroma_collection_name,
                    db_path=config.chroma_db_path,
                    embedding_model=config.embedding_model
                )
                
                # QA サービス
                self.qa_service = QAService(
                    indexer=self.indexer
                )
                
                # UI コンポーネント
                self.main_view = MainView(indexer=self.indexer)
                
                self.settings_view = SettingsView(
                    config_interface=self.config_manager,
                    indexing_interface=self.indexer
                )
                
                self.logger.info("全サービス初期化完了")
            
        except Exception as e:
            log_error(e, context={"phase": "service_initialization"}, user_impact="critical")
            self.logger.error(f"サービス初期化エラー: {e}")
            st.error(f"アプリケーションの初期化に失敗しました: {str(e)}")
            st.stop()
    
    @create_error_handler("general")
    def run(self) -> None:
        """メインアプリケーションを実行"""
        try:
            # 環境検証
            self._validate_environment()
            
            # Ollamaモデルチェック
            if not self._check_ollama_models():
                return  # モデル不足の場合は処理を停止
            
            # セッションステート初期化
            init_session_state()
            
            # ページ設定
            self._configure_page()
            
            # ナビゲーション表示
            current_page = self.navigation.render()
            
            # キャンセル処理
            self._handle_cancellation()
            
            # 現在のページに応じてビューを表示
            self._render_current_view(current_page)
            
        except LocalKnowledgeAgentError as e:
            self.logger.error(f"アプリケーションエラー: {e}")
            st.error(f"エラーが発生しました: {e.message}")
            
        except Exception as e:
            self.logger.error(f"予期しないエラー: {e}")
            st.error(f"予期しないエラーが発生しました: {str(e)}")
            
            # デバッグ情報（開発時のみ）
            if st.checkbox("詳細なエラー情報を表示", key="show_error_details"):
                st.exception(e)
    
    def _check_ollama_models(self) -> bool:
        """
        Ollamaの必須モデルをチェック
        
        Returns:
            bool: すべての必須モデルが利用可能な場合True
        """
        try:
            self.logger.info("Ollamaモデルチェックを開始")
            check_result = self.ollama_checker.check_required_models()
            
            if check_result.is_available:
                self.logger.info("すべての必須モデルが利用可能です")
                return True
            
            # モデル不足の場合の処理
            self.logger.warning(f"必須モデル不足: {len(check_result.missing_models)}個")
            self._show_model_installation_guide(check_result)
            return False
            
        except Exception as e:
            self.logger.error(f"Ollamaモデルチェック中にエラー: {e}")
            st.error("Ollamaモデルの確認中にエラーが発生しました")
            return False
    
    def _show_model_installation_guide(self, check_result) -> None:
        """
        モデルインストールガイドを表示
        
        Args:
            check_result: モデルチェック結果
        """
        st.set_page_config(
            page_title="LocalKnowledgeAgent - モデルセットアップ",
            page_icon="🚨",
            layout="centered"
        )
        
        st.title("🚨 必須モデルのセットアップが必要です")
        
        if not check_result.ollama_connected:
            st.error("**Ollamaサーバーに接続できません**")
            st.markdown("""
            **解決方法:**
            1. Ollamaがインストールされているか確認してください
            2. Ollamaサービスが起動しているか確認してください
            3. コマンドで `ollama serve` を実行してみてください
            """)
            return
        
        # インストールガイド表示
        guide_text = self.ollama_checker.get_installation_guide(check_result.missing_models)
        st.markdown(guide_text)
        
        # 利用可能モデル表示
        if check_result.available_models:
            with st.expander("現在利用可能なモデル"):
                for model in check_result.available_models:
                    st.text(f"✅ {model}")
        
        # 再チェックボタン
        if st.button("🔄 再チェック", use_container_width=True):
            st.rerun()
        
        st.markdown("---")
        st.info("**注意:** モデルのダウンロードには時間がかかる場合があります。インストール完了後、このページを再読み込みしてください。")
    
    def _validate_environment(self) -> None:
        """環境変数とシステム要件を検証"""
        try:
            # 環境変数検証
            app_config = get_app_config()
            self.logger.info(f"アプリケーション設定を読み込みました: {len(app_config)}項目")
                
            # 必要なディレクトリの作成
            self._ensure_directories()
            
        except Exception as e:
            self.logger.warning(f"環境検証で問題が発生しました: {e}")
            st.warning("環境設定で問題が発生しました。デフォルト値を使用します。")
    
    def _ensure_directories(self) -> None:
        """必要なディレクトリが存在することを確認"""
        required_dirs = [
            "./data",
            "./data/chroma_db",
            "./logs"
        ]
        
        for dir_path in required_dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    def _configure_page(self) -> None:
        """Streamlitページ設定"""
        st.set_page_config(
            page_title="LocalKnowledgeAgent",
            page_icon="📚",
            layout="wide",
            initial_sidebar_state="expanded",
            menu_items={
                'Get Help': None,
                'Report a bug': None,
                'About': '''
                # LocalKnowledgeAgent
                
                ローカル知識管理システム
                
                **バージョン**: 1.0.0
                **フレームワーク**: Streamlit + LangChain + ChromaDB + Ollama
                '''
            }
        )
        
        # プロダクションモード設定
        st.markdown("""
            <style>
            /* プロダクションモードのスタイル調整 */
            .main .block-container { padding-top: 1rem; }
            .stButton > button { width: 100%; }
            footer { display: none; }
            header { display: none; }
            #MainMenu { display: none; }
            </style>
        """, unsafe_allow_html=True)
    
    def _handle_cancellation(self) -> None:
        """キャンセル処理の制御"""
        if SessionStateManager.is_cancel_requested():
            self._process_cancellation()
    
    def _process_cancellation(self) -> None:
        """キャンセル処理の実行"""
        try:
            self.logger.info("キャンセル処理を開始します")
            
            # 各サービスに対してキャンセル要求を送信
            if hasattr(self.qa_service, 'cancel_current_operation'):
                self.qa_service.cancel_current_operation()
                
            if hasattr(self.indexer, 'cancel_current_operation'):
                self.indexer.cancel_current_operation()
            
            # アプリケーション状態をアイドルに戻す
            SessionStateManager.set_app_state("idle", cancel_requested=False)
            SessionStateManager.clear_messages()
            
            st.success("処理をキャンセルしました")
            st.rerun()
            
        except Exception as e:
            self.logger.error(f"キャンセル処理中にエラー: {e}")
            SessionStateManager.set_error_message("キャンセル処理中にエラーが発生しました")
    
    def _render_current_view(self, current_page: str) -> None:
        """
        現在選択されているページのビューをレンダリング
        
        Args:
            current_page: 現在のページID ("main" または "settings")
        """
        try:
            if current_page == "main":
                self.main_view.render()
            elif current_page == "settings":
                self.settings_view.render()
            else:
                st.error(f"不明なページ: {current_page}")
                
        except Exception as e:
            self.logger.error(f"ビューレンダリングエラー ({current_page}): {e}")
            st.error(f"ページの表示中にエラーが発生しました: {str(e)}")


def main():
    """アプリケーションエントリーポイント"""
    try:
        # アプリケーションインスタンス作成
        app = LocalKnowledgeAgentApp()
        
        # アプリケーション実行
        app.run()
        
    except Exception as e:
        st.error(f"アプリケーションの起動に失敗しました: {str(e)}")
        st.exception(e)


if __name__ == "__main__":
    main()