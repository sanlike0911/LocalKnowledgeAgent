import streamlit as st
from typing import Optional
from pathlib import Path
import os

from src.logic.config_manager import ConfigManager
from src.logic.indexing import ChromaDBIndexer
from src.models.config import Config
from src.exceptions.base_exceptions import (
    ConfigError, IndexingError, ConfigValidationError, 
    create_error_handler, ErrorMessages
)

class SettingsView:
    def __init__(self, config_interface: ConfigManager, indexing_interface: ChromaDBIndexer):
        self.config_interface = config_interface
        self.indexing_interface = indexing_interface

    @create_error_handler("config")
    def render(self) -> None:
        """設定画面をレンダリング"""
        st.title("設定")

        try:
            current_config = self.config_interface.load_config()
            
            # フォルダ管理
            st.header("フォルダ管理")
            
            # 既存の対象フォルダを表示
            if current_config.selected_folders:
                st.subheader("登録済みフォルダ")
                for folder in current_config.selected_folders:
                    st.write(f"📁 {folder}")
                
                selected_folders_to_remove = st.multiselect(
                    "削除するフォルダを選択",
                    options=current_config.selected_folders,
                    default=[],
                    help="インデックスから削除したいフォルダを選択してください"
                )
                if st.button("選択したフォルダを削除", type="secondary"):
                    self._handle_folder_removal(current_config, selected_folders_to_remove)
            else:
                st.info("現在、対象フォルダは設定されていません。")

            # フォルダ追加
            st.subheader("フォルダ追加")
            new_folder_path = st.text_input(
                "新しいフォルダパス", 
                key="new_folder_path",
                help="PDF/TXT/DOCX/MDファイルが含まれるフォルダのパスを入力してください",
                placeholder="例: /Users/username/Documents/data"
            )
            if st.button("フォルダを追加", type="primary"):
                self._handle_folder_addition(current_config, new_folder_path)
            st.markdown("---")  # ← 区切り線

            # インデックス管理
            st.header("インデックス管理")
            self._render_index_management(current_config)

            # アプリケーション設定
            st.header("アプリケーション設定")
            self._render_app_settings(current_config)

        except ConfigError as e:
            st.error(f"設定エラー: {e.message}")
        except IndexingError as e:
            st.error(f"インデックス処理エラー: {e.message}")
        except Exception as e:
            st.error(f"予期しないエラーが発生しました: {str(e)}")
    
    def _validate_folder_path(self, folder_path: str) -> bool:
        """
        フォルダパスの検証
        
        Args:
            folder_path: 検証するフォルダパス
            
        Returns:
            bool: 有効な場合True
        """
        if not folder_path or not folder_path.strip():
            st.error("フォルダパスを入力してください")
            return False
            
        path = Path(folder_path.strip())
        
        if not path.exists():
            st.error("指定されたパスが存在しません")
            return False
            
        if not path.is_dir():
            st.error("指定されたパスはディレクトリではありません")
            return False
            
        # 読み取り権限の確認
        if not os.access(path, os.R_OK):
            st.error("指定されたフォルダへの読み取り権限がありません")
            return False
            
        return True
    
    def _handle_folder_addition(self, config: Config, folder_path: str) -> None:
        """
        フォルダ追加処理
        
        Args:
            config: 現在の設定
            folder_path: 追加するフォルダパス
        """
        try:
            if not self._validate_folder_path(folder_path):
                return
                
            normalized_path = str(Path(folder_path.strip()).resolve())
            
            if normalized_path in config.selected_folders:
                st.warning("このフォルダは既に追加されています")
                return
                
            config.selected_folders.append(normalized_path)
            self.config_interface.save_config(config)
            st.success(f"フォルダ '{normalized_path}' を追加しました")
            st.rerun()
            
        except Exception as e:
            raise ConfigError(
                f"フォルダの追加中にエラーが発生しました: {str(e)}",
                error_code="CFG_FOLDER_ADD_FAILED",
                details={"folder_path": folder_path}
            )
    
    def _handle_folder_removal(self, config: Config, folders_to_remove: list) -> None:
        """
        フォルダ削除処理
        
        Args:
            config: 現在の設定
            folders_to_remove: 削除するフォルダのリスト
        """
        try:
            if not folders_to_remove:
                st.warning("削除するフォルダを選択してください")
                return
                
            for folder in folders_to_remove:
                if folder in config.selected_folders:
                    config.selected_folders.remove(folder)
                    
            self.config_interface.save_config(config)
            st.success(f"{len(folders_to_remove)}個のフォルダを削除しました")
            st.rerun()
            
        except Exception as e:
            raise ConfigError(
                f"フォルダの削除中にエラーが発生しました: {str(e)}",
                error_code="CFG_FOLDER_REMOVE_FAILED",
                details={"folders_to_remove": folders_to_remove}
            )
    
    def _render_index_management(self, config: Config) -> None:
        """
        インデックス管理UIをレンダリング
        
        Args:
            config: 現在の設定
        """
        try:
            # インデックス統計表示
            index_stats = self.indexing_interface.get_collection_stats()
            
            # 現在の状態表示
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                # 設定ファイルのindex_statusを表示
                status_color = {
                    "not_created": "🔴",
                    "creating": "🟡", 
                    "created": "🟢",
                    "error": "❌"
                }
                status_text = {
                    "not_created": "未作成",
                    "creating": "作成中",
                    "created": "作成済み", 
                    "error": "エラー"
                }
                current_status = getattr(config, 'index_status', 'not_created')
                st.metric(
                    "インデックス状態", 
                    f"{status_color.get(current_status, '❓')} {status_text.get(current_status, '不明')}"
                )
            with col2:
                st.metric("文書数", index_stats['document_count'])
            with col3:
                st.metric("コレクション名", index_stats['collection_name'])
            with col4:
                st.metric("登録フォルダ数", len(config.selected_folders))
            
            # 状態に応じたメッセージ表示
            if current_status == "not_created" and index_stats['document_count'] == 0:
                st.warning("⚠️ インデックスが作成されていません。「インデックスを作成」ボタンを押してインデックスを作成してください。")
            elif current_status == "created" and index_stats['document_count'] > 0:
                st.success("✅ インデックスは正常に作成されています。チャット機能が利用可能です。")
            elif current_status == "error":
                st.error("❌ インデックス作成でエラーが発生しました。再作成をお試しください。")
            elif current_status == "creating":
                st.info("⏳ インデックスを作成中です。しばらくお待ちください。")
            
            # インデックス操作ボタン
            col1, col2 = st.columns(2)
            
            with col1:
                # フォルダが設定されているかチェック
                if not config.selected_folders:
                    st.button("インデックスを作成", type="primary", disabled=True, use_container_width=True)
                    st.caption("⚠️ フォルダを追加してからインデックスを作成してください")
                else:
                    if st.button("インデックスを作成", type="primary", use_container_width=True):
                        self._handle_index_rebuild(config)
            
            with col2:
                if st.button("インデックスを削除", type="secondary", use_container_width=True):
                    self._handle_index_clear(config)
                    
        except Exception as e:
            st.error(f"インデックス情報の取得中にエラーが発生しました: {str(e)}")
    
    def _handle_index_rebuild(self, config: Config) -> None:
        """
        インデックス再作成処理（index_status更新機能付き）
        
        Args:
            config: 現在の設定
        """
        try:
            if not config.selected_folders:
                st.warning("インデックスを作成するフォルダが選択されていません。フォルダを追加してからお試しください。")
                return
            
            # インデックス作成開始 - status を creating に更新
            config.index_status = "creating"
            self.config_interface.save_config(config)
            st.info("🟡 インデックス作成を開始します...")
            
            # インデックス作成実行
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                status_text.text("📁 フォルダをスキャン中...")
                progress_bar.progress(20)
                
                status_text.text("📄 ドキュメントを処理中...")
                progress_bar.progress(50)
                
                # 実際のインデックス作成処理
                with st.spinner("インデックスを作成しています。しばらくお待ちください..."):
                    self.indexing_interface.rebuild_index_from_folders(config.selected_folders)
                
                progress_bar.progress(90)
                status_text.text("✅ インデックス作成完了...")
                
                # インデックス作成完了 - status を created に更新
                config.index_status = "created"
                self.config_interface.save_config(config)
                
                progress_bar.progress(100)
                status_text.empty()
                progress_bar.empty()
                
                st.success("🎉 インデックスの作成が完了しました！チャット機能が利用可能になりました。")
                st.rerun()
                
            except Exception as e:
                # インデックス作成失敗 - status を error に更新
                config.index_status = "error"
                self.config_interface.save_config(config)
                
                progress_bar.empty()
                status_text.empty()
                
                raise IndexingError(
                    f"インデックス作成中にエラーが発生しました: {str(e)}",
                    error_code="IDX_REBUILD_FAILED",
                    details={"selected_folders": config.selected_folders}
                )
            
        except IndexingError:
            raise
        except Exception as e:
            # 予期しないエラーの場合もstatus を error に更新
            config.index_status = "error"
            self.config_interface.save_config(config)
            
            raise IndexingError(
                f"インデックス作成処理で予期しないエラーが発生しました: {str(e)}",
                error_code="IDX_REBUILD_UNEXPECTED",
                details={"selected_folders": config.selected_folders}
            )
    
    def _handle_index_clear(self, config: Config) -> None:
        """インデックス削除処理（index_status更新機能付き）
        
        Args:
            config: 現在の設定
        """
        try:
            # 確認ダイアログを表示したい場合のロジック
            st.warning("⚠️ この操作により全てのインデックスデータが削除されます。")
            
            # インデックス削除実行
            with st.spinner("インデックスを削除しています..."):
                self.indexing_interface.clear_collection()
            
            # インデックス削除完了 - status を not_created に更新
            config.index_status = "not_created"
            self.config_interface.save_config(config)
            
            st.success("インデックスの削除が完了しました。")
            st.rerun()
            
        except Exception as e:
            # インデックス削除失敗 - status を error に更新
            config.index_status = "error"
            self.config_interface.save_config(config)
            
            raise IndexingError(
                f"インデックス削除中にエラーが発生しました: {str(e)}",
                error_code="IDX_CLEAR_FAILED"
            )
    
    def _render_app_settings(self, config: Config) -> None:
        """
        アプリケーション設定UIをレンダリング
        
        Args:
            config: 現在の設定
        """
        try:
            with st.form("app_settings_form"):
                st.subheader("モデル設定")
                
                # LLMモデル名
                ollama_model = st.text_input(
                    "LLMモデル名", 
                    value=config.ollama_model,
                    help="Ollamaで使用するモデル名を指定してください（例: llama3:8b, codellama）"
                )
                
                st.subheader("データベース設定") 
                
                # ベクトルストアパス
                chroma_db_path = st.text_input(
                    "ベクトルストアパス", 
                    value=config.chroma_db_path,
                    help="ChromaDBデータベースの保存先パスを指定してください"
                )
                
                # 設定保存ボタン
                submitted = st.form_submit_button("設定を保存", type="primary", use_container_width=True)
                
                if submitted:
                    self._handle_config_save(config, ollama_model, chroma_db_path)
                    
        except Exception as e:
            st.error(f"設定表示中にエラーが発生しました: {str(e)}")
    
    def _validate_config_input(self, ollama_model: str, chroma_db_path: str) -> bool:
        """
        設定入力値の検証
        
        Args:
            ollama_model: LLMモデル名
            chroma_db_path: ベクトルストアパス
            
        Returns:
            bool: 有効な場合True
        """
        if not ollama_model or not ollama_model.strip():
            st.error("LLMモデル名を入力してください")
            return False
            
        if not chroma_db_path or not chroma_db_path.strip():
            st.error("ベクトルストアパスを入力してください")
            return False
            
        # パスの親ディレクトリが存在するか確認
        db_path = Path(chroma_db_path.strip())
        parent_dir = db_path.parent
        
        if not parent_dir.exists():
            st.error(f"指定されたパスの親ディレクトリが存在しません: {parent_dir}")
            return False
            
        if not os.access(parent_dir, os.W_OK):
            st.error(f"指定されたパスに書き込み権限がありません: {parent_dir}")
            return False
            
        return True
    
    def _handle_config_save(self, current_config: Config, ollama_model: str, chroma_db_path: str) -> None:
        """
        設定保存処理
        
        Args:
            current_config: 現在の設定
            ollama_model: LLMモデル名
            chroma_db_path: ベクトルストアパス
        """
        try:
            if not self._validate_config_input(ollama_model, chroma_db_path):
                return
                
            updated_config = Config(
                selected_folders=current_config.selected_folders,
                chroma_db_path=chroma_db_path.strip(),
                ollama_model=ollama_model.strip()
            )
            
            self.config_interface.save_config(updated_config)
            st.success("設定を保存しました。変更を反映するにはアプリケーションを再起動してください。")
            
        except Exception as e:
            raise ConfigError(
                f"設定保存中にエラーが発生しました: {str(e)}",
                error_code="CFG_SAVE_FAILED",
                details={
                    "ollama_model": ollama_model,
                    "chroma_db_path": chroma_db_path
                }
            )