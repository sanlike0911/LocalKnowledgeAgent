import streamlit as st
from typing import Optional
from pathlib import Path
import os

from src.logic.config_manager import ConfigManager
from src.logic.indexing import ChromaDBIndexer
from src.logic.ollama_model_service import OllamaModelService, OllamaConnectionError
from src.models.config import Config
from src.exceptions.base_exceptions import (
    ConfigError, IndexingError, ConfigValidationError, 
    create_error_handler, ErrorMessages
)
from src.utils.structured_logger import get_logger

class SettingsView:
    def __init__(self, config_interface: ConfigManager, indexing_interface: ChromaDBIndexer):
        self.config_interface = config_interface
        self.indexing_interface = indexing_interface
        self.ollama_service = OllamaModelService()
        self.logger = get_logger(__name__)

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
                st.error("❌ インデックス作成でエラーが発生しました。インデックスを削除してから再作成をお試しください。")
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
                # インデックス削除ボタン - エラー状態や作成済み状態で表示
                deletion_enabled = current_status in ["created", "error"] or index_stats['document_count'] > 0
                if deletion_enabled:
                    if st.button("インデックスを削除", type="secondary", use_container_width=True):
                        self._handle_index_clear(config)
                else:
                    st.button("インデックスを削除", type="secondary", disabled=True, use_container_width=True)
                    st.caption("ℹ️ 削除するインデックスがありません")
                    
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
            st.info(f"🟡 インデックス作成を開始します...（埋め込みモデル: {config.embedding_model}）")
            
            # インデックス作成実行
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                status_text.text("📁 フォルダをスキャン中...")
                progress_bar.progress(20)
                
                status_text.text("📄 ドキュメントを処理中...")
                progress_bar.progress(50)
                
                # 実際のインデックス作成処理
                with st.spinner(f"インデックスを作成しています（{config.embedding_model}）。しばらくお待ちください..."):
                    # ISSUE-027対応: 事前に次元数互換性チェック実行
                    status_text.text(f"🔧 埋め込みモデル互換性チェック中...（{config.embedding_model}）")
                    try:
                        self.indexing_interface.recreate_collection_if_incompatible()
                    except Exception as dimension_error:
                        self.logger.warning(f"次元数互換性チェック警告: {dimension_error}")
                    
                    status_text.text(f"📄 ドキュメントをインデックス化中...（{config.embedding_model}）")
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
                
                # LLMモデル名（動的取得）
                ollama_model = self._render_llm_model_selector(config.ollama_model)
                
                # 埋め込みモデル名 - 動的フィルタリング対応
                embedding_model = self._render_embedding_model_selector(config)
                
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
                    self._handle_config_save(config, ollama_model, embedding_model, chroma_db_path)
                    
        except Exception as e:
            st.error(f"設定表示中にエラーが発生しました: {str(e)}")
    
    def _validate_config_input(self, ollama_model: str, embedding_model: str, chroma_db_path: str) -> bool:
        """
        設定入力値の検証
        
        Args:
            ollama_model: LLMモデル名
            embedding_model: 埋め込みモデル名
            chroma_db_path: ベクトルストアパス
            
        Returns:
            bool: 有効な場合True
        """
        if not ollama_model or not ollama_model.strip():
            st.error("LLMモデル名を入力してください")
            return False
            
        if not embedding_model or not embedding_model.strip():
            st.error("埋め込みモデル名を選択してください")
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
    
    def _handle_config_save(self, current_config: Config, ollama_model: str, embedding_model: str, chroma_db_path: str) -> None:
        """
        設定保存処理
        
        Args:
            current_config: 現在の設定
            ollama_model: LLMモデル名
            embedding_model: 埋め込みモデル名
            chroma_db_path: ベクトルストアパス
        """
        try:
            if not self._validate_config_input(ollama_model, embedding_model, chroma_db_path):
                return
            
            # 変更検出
            model_changed = (
                current_config.ollama_model != ollama_model.strip() or
                current_config.embedding_model != embedding_model.strip()
            )
            db_path_changed = current_config.chroma_db_path != chroma_db_path.strip()
                
            updated_config = Config(
                selected_folders=current_config.selected_folders,
                chroma_db_path=chroma_db_path.strip(),
                ollama_model=ollama_model.strip(),
                embedding_model=embedding_model.strip(),
                ollama_host=current_config.ollama_host,
                max_chat_history=current_config.max_chat_history,
                index_status=current_config.index_status,
                chroma_collection_name=current_config.chroma_collection_name,
                max_file_size_mb=current_config.max_file_size_mb,
                force_japanese_response=current_config.force_japanese_response
            )
            
            self.config_interface.save_config(updated_config)
            
            # 変更内容に応じたメッセージを表示
            if model_changed and db_path_changed:
                st.success("✅ 設定を保存しました")
                st.warning("⚠️ モデル設定とデータベースパスが変更されました。変更を反映するには**アプリケーションを再起動**してください。")
                st.info("🔄 再起動後、インデックスの再構築が必要な場合があります。")
            elif model_changed:
                st.success("✅ 設定を保存しました")
                st.warning("⚠️ モデル設定が変更されました。変更を反映するには**アプリケーションを再起動**してください。")
                if current_config.embedding_model != embedding_model.strip():
                    st.info("🔄 埋め込みモデル変更により、インデックスの再構築を推奨します。")
            elif db_path_changed:
                st.success("✅ 設定を保存しました")
                st.info("ℹ️ データベースパスが変更されました。新しいパスでインデックスを再構築してください。")
            else:
                st.success("✅ 設定を保存しました")
            
        except Exception as e:
            raise ConfigError(
                f"設定保存中にエラーが発生しました: {str(e)}",
                error_code="CFG_SAVE_FAILED",
                details={
                    "ollama_model": ollama_model,
                    "embedding_model": embedding_model,
                    "chroma_db_path": chroma_db_path
                }
            )
    
    def _render_llm_model_selector(self, current_model: str) -> str:
        """
        動的LLMモデル選択セレクターをレンダリング
        
        Args:
            current_model: 現在選択されているモデル名
            
        Returns:
            str: 選択されたモデル名
        """
        try:
            # フォールバックモデル一覧（API接続失敗時に使用）
            fallback_models = [
                "llama3:8b",
                "llama3:70b", 
                "mistral:latest",
                "codellama:13b",
                "gemma:2b",
                "gemma:7b"
            ]
            
            # Ollamaから利用可能モデルを取得（フォールバック付き）
            available_models = self.ollama_service.get_available_models_with_fallback(fallback_models)
            
            # 現在のモデルがリストにない場合は追加
            if current_model and current_model not in available_models:
                available_models.insert(0, current_model)
            
            # モデルリストが空の場合のデフォルト
            if not available_models:
                available_models = fallback_models
            
            # 現在のモデルのインデックスを取得
            try:
                current_index = available_models.index(current_model) if current_model in available_models else 0
            except (ValueError, IndexError):
                current_index = 0
            
            # セレクターをレンダリング
            selected_model = st.selectbox(
                "LLMモデル",
                options=available_models,
                index=current_index,
                help="チャット応答に使用するLLMモデルを選択してください。リストはOllamaから自動取得されます。"
            )
            
            # 接続状態の表示
            try:
                # 実際にOllamaサーバーから最新情報を取得してステータス表示
                test_models = self.ollama_service.get_available_models()
                st.success(f"✅ Ollama接続成功 ({len(test_models)}モデル利用可能)")
                
                # 選択されたモデルの詳細情報を表示
                self._render_model_info(selected_model)
                
            except OllamaConnectionError:
                st.warning("⚠️ Ollama接続失敗 - デフォルトモデル一覧を表示")
            
            return selected_model
            
        except Exception as e:
            # 予期しないエラーの場合は安全なフォールバック
            st.error(f"モデル選択での予期しないエラー: {str(e)}")
            return st.text_input(
                "LLMモデル名（手動入力）",
                value=current_model,
                help="自動取得に失敗したため、手動でモデル名を入力してください"
            )

    def _render_model_info(self, model_name: str) -> None:
        """
        選択されたモデルの詳細情報を表示
        
        Args:
            model_name: 表示するモデル名
        """
        try:
            # モデル詳細情報を取得
            model_info = self.ollama_service.get_model_info(model_name)
            
            if not model_info:
                st.info(f"ℹ️ モデル '{model_name}' の詳細情報を取得できませんでした")
                return
            
            # モデル情報を表示するコンテナ
            with st.container():
                st.markdown("**📊 モデル情報**")
                
                # 基本情報を3列で表示
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # サイズ情報
                    size_bytes = model_info.get("size", 0)
                    if size_bytes > 0:
                        size_human = self.ollama_service.format_model_size(size_bytes)
                        st.metric("💾 サイズ", size_human)
                        
                        # メモリ使用量の推定
                        estimated_memory = self.ollama_service.estimate_memory_usage(size_bytes)
                        memory_human = self.ollama_service.format_model_size(estimated_memory)
                        st.caption(f"推定メモリ使用量: {memory_human}")
                    else:
                        st.metric("💾 サイズ", "不明")
                
                with col2:
                    # 更新日時
                    modified_at = model_info.get("modified_at")
                    if modified_at:
                        formatted_date = self.ollama_service.format_datetime(modified_at)
                        st.metric("📅 更新日時", formatted_date)
                    else:
                        st.metric("📅 更新日時", "不明")
                
                with col3:
                    # モデル名
                    st.metric("🤖 モデル名", model_name)
                    
        except Exception as e:
            st.error(f"モデル情報の取得中にエラーが発生しました: {str(e)}")

    def _render_embedding_model_selector(self, config: Config) -> str:
        """
        埋め込みモデル選択UIをレンダリング（動的フィルタリング対応）
        
        Args:
            config: 現在の設定オブジェクト
            
        Returns:
            str: 選択された埋め込みモデル名
        """
        try:
            # 設定ファイルからサポート対象モデルリストを取得
            supported_models = getattr(config, 'supported_embedding_models', [
                "nomic-embed-text", "mxbai-embed-large", "all-minilm", "snowflake-arctic-embed"
            ])
            
            # Ollamaから動的にフィルタリング済みモデル一覧を取得
            available_embedding_models = self.ollama_service.get_filtered_embedding_models_with_fallback(
                supported_models
            )
            
            # 選択肢が空の場合の警告表示とフォールバック
            if not available_embedding_models:
                st.warning("⚠️ 利用可能な埋め込みモデルが見つかりません。サポート対象モデルを表示しています。")
                available_embedding_models = supported_models
            
            # 現在のモデルのインデックスを取得
            current_model = config.embedding_model
            try:
                current_index = available_embedding_models.index(current_model) if current_model in available_embedding_models else 0
            except (ValueError, IndexError):
                current_index = 0
                
            # 動的フィルタリング結果のセレクターをレンダリング
            selected_embedding_model = st.selectbox(
                "埋め込み（ベクトル変換）用モデル",
                options=available_embedding_models,
                index=current_index,
                help=f"ドキュメントのベクトル変換に使用するモデルを選択してください。\n"
                     f"利用可能な埋め込みモデルは「{', '.join(available_embedding_models)}」"
            )
            
            # フィルタリング情報の表示
            try:
                # Ollama接続テストと情報表示
                installed_models = self.ollama_service.get_all_models_info()
                if installed_models:
                    total_filtered = len(available_embedding_models)
                    
                    st.info(
                        f"📊 埋め込み（ベクトル変換）の利用可能モデル： {total_filtered}モデル"
                    )
                else:
                    st.warning("⚠️ Ollama接続失敗 - サポートモデル一覧を表示")
                    
            except Exception as e:
                st.warning(f"⚠️ モデル情報取得エラー: {str(e)}")
                
            return selected_embedding_model
            
        except Exception as e:
            # 予期しないエラーの場合は従来の静的選択に戻す
            st.error(f"埋め込みモデル選択での予期しないエラー: {str(e)}")
            st.warning("静的な選択肢にフォールバックします。")
            
            # 従来の静的選択肢
            fallback_options = ["nomic-embed-text", "mxbai-embed-large", "all-minilm", "snowflake-arctic-embed"]
            current_model = config.embedding_model
            
            try:
                fallback_index = fallback_options.index(current_model) if current_model in fallback_options else 0
            except (ValueError, IndexError):
                fallback_index = 0
                
            return st.selectbox(
                "埋め込み（ベクトル変換）用モデル（フォールバック）",
                options=fallback_options,
                index=fallback_index,
                help="動的選択に失敗したため、静的選択肢を表示しています。"
            )