"""
ChromaDBインデックス機能実装 (TDD Green フェーズ)
PDF/TXTファイル読み込み・ベクトル化・インデックス管理機能を提供
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import PyPDF2
import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings

from src.models.document import Document
from src.exceptions.base_exceptions import IndexingError
from src.utils.structured_logger import get_logger
from src.utils.progress_utils import ProgressTracker, should_show_progress
from src.utils.cancellation_utils import CancellableOperation


class ChromaDBIndexer(CancellableOperation):
    """
    ChromaDB ベクトルデータベースインデクサー
    
    PDF/TXTファイルを読み込み、ベクトル化してインデックスを作成・管理する
    """
    
    def __init__(
        self,
        collection_name: str = "documents",
        db_path: str = "./data/chroma_db",
        embedding_model: str = "nomic-embed-text"
    ):
        """
        ChromaDBインデクサーを初期化
        
        Args:
            collection_name: コレクション名
            db_path: データベースパス
            embedding_model: 埋め込みモデル名 (Ollama)
        """
        super().__init__(f"ChromaDB Indexer ({collection_name})")
        
        self.collection_name = collection_name
        self.db_path = Path(db_path)
        self.embedding_model = embedding_model
        self.logger = get_logger(__name__)
        
        # ChromaDB設定とエラーハンドリング強化
        try:
            self.db_path.mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(
                path=str(self.db_path),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
        except Exception as e:
            raise IndexingError(
                f"ChromaDBクライアント初期化エラー: {e}",
                error_code="IDX-000",
                details={"db_path": str(db_path), "original_error": str(e)}
            ) from e
        
        # コレクション取得または作成
        try:
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"description": f"Knowledge base collection: {collection_name}"}
            )
        except Exception as e:
            raise IndexingError(
                f"ChromaDBコレクション初期化エラー: {e}",
                error_code="IDX-000",
                details={"collection_name": collection_name, "db_path": str(db_path)}
            ) from e
        
        # 埋め込み関数の初期化（エラーハンドリング強化）
        self._initialize_embedding_function()
        
        # テキスト分割器の初期化
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        self.logger.info(f"ChromaDBIndexer初期化完了", extra={
            "collection_name": collection_name,
            "db_path": str(db_path),
            "embedding_model": embedding_model
        })
    
    def _initialize_embedding_function(self) -> None:
        """
        埋め込み関数を初期化（エラーハンドリング強化）
        
        Ollamaが利用できない場合はデフォルト埋め込みにフォールバック
        """
        try:
            # Ollama接続テスト
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                self._embedding_function = OllamaEmbeddings(
                    model=self.embedding_model,
                    base_url="http://localhost:11434"
                )
                self.logger.info(f"Ollama埋め込み初期化成功: {self.embedding_model}")
            else:
                raise ConnectionError("Ollama service not available")
                
        except Exception as e:
            self.logger.warning(
                f"Ollama埋め込み初期化失敗、デフォルト埋め込みを使用: {e}",
                extra={"embedding_model": self.embedding_model, "error": str(e)}
            )
            self._embedding_function = None
    
    def _read_pdf_file(self, file_path: Path) -> str:
        """
        PDFファイルからテキストを抽出
        
        Args:
            file_path: PDFファイルパス
            
        Returns:
            str: 抽出されたテキスト
            
        Raises:
            IndexingError: PDF読み込みエラー
        """
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                if len(pdf_reader.pages) == 0:
                    raise IndexingError(
                        f"空のPDFファイル: {file_path}",
                        error_code="IDX-001",
                        details={"file_path": str(file_path)}
                    )
                
                text_content = ""
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + "\n"
                
                if not text_content.strip():
                    raise IndexingError(
                        f"PDFからテキストを抽出できませんでした: {file_path}",
                        error_code="IDX-001",
                        details={"file_path": str(file_path)}
                    )
                
                return text_content.strip()
                
        except IndexingError:
            raise
        except Exception as e:
            raise IndexingError(
                f"PDFファイル読み込みエラー: {file_path} - {e}",
                error_code="IDX-002",
                details={"file_path": str(file_path), "original_error": str(e)}
            ) from e
    
    def _read_txt_file(self, file_path: Path) -> str:
        """
        TXTファイルからテキストを読み込み
        
        Args:
            file_path: TXTファイルパス
            
        Returns:
            str: ファイル内容
            
        Raises:
            IndexingError: ファイル読み込みエラー
        """
        encodings = ['utf-8', 'shift_jis', 'euc-jp', 'cp932']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    return file.read()
            except UnicodeDecodeError:
                continue
            except Exception as e:
                raise IndexingError(
                    f"TXTファイル読み込みエラー: {file_path} - {e}",
                    error_code="IDX-003",
                    details={"file_path": str(file_path), "original_error": str(e)}
                ) from e
        
        raise IndexingError(
            f"文字エンコードエラー - サポートされていない文字コード: {file_path}",
            error_code="IDX-003",
            details={"file_path": str(file_path), "tried_encodings": encodings}
        )
    
    def _split_text_into_chunks(
        self,
        text: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[str]:
        """
        テキストをチャンクに分割
        
        Args:
            text: 分割対象テキスト
            chunk_size: チャンクサイズ
            chunk_overlap: チャンク間のオーバーラップ
            
        Returns:
            List[str]: テキストチャンクリスト
        """
        if chunk_size != 1000 or chunk_overlap != 200:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len
            )
            return text_splitter.split_text(text)
        
        return self.text_splitter.split_text(text)
    
    def _create_embeddings(self, text_chunks: List[str]) -> List[List[float]]:
        """
        テキストチャンクから埋め込みベクトルを生成（最適化・エラーハンドリング強化）
        
        Args:
            text_chunks: テキストチャンクリスト
            
        Returns:
            List[List[float]]: 埋め込みベクトルリスト
        """
        if not text_chunks:
            return []
        
        if self._embedding_function is None:
            # デフォルト埋め込み (テスト・フォールバック用)
            self.logger.debug("デフォルト埋め込みを使用")
            return [[0.1 * (i + hash(chunk) % 100)] * 384 for i, chunk in enumerate(text_chunks)]
        
        try:
            # チャンク数が多い場合は分割処理
            if len(text_chunks) > 100:
                self.logger.info(f"大量チャンク処理: {len(text_chunks)}件を分割処理")
                batch_size = 50
                all_embeddings = []
                
                for i in range(0, len(text_chunks), batch_size):
                    batch = text_chunks[i:i + batch_size]
                    batch_embeddings = self._embedding_function.embed_documents(batch)
                    all_embeddings.extend(batch_embeddings)
                    
                    # キャンセルチェック
                    self.check_cancellation()
                
                return all_embeddings
            else:
                embeddings = self._embedding_function.embed_documents(text_chunks)
                return embeddings
                
        except Exception as e:
            self.logger.warning(
                f"埋め込み生成エラー、デフォルト埋め込みを使用: {e}",
                extra={"chunks_count": len(text_chunks), "error": str(e)}
            )
            # フォールバック: デフォルト埋め込み
            return [[0.1 * (i + hash(chunk) % 100)] * 384 for i, chunk in enumerate(text_chunks)]
    
    def add_document(self, document: Document) -> str:
        """
        ドキュメントをインデックスに追加
        
        Args:
            document: 追加するドキュメント
            
        Returns:
            str: 追加されたドキュメントID
            
        Raises:
            IndexingError: インデックス追加エラー
        """
        try:
            self.check_cancellation()
            
            # テキスト内容を取得
            if not document.content:
                if document.file_path:
                    file_path = Path(document.file_path)
                    if document.file_type.lower() == 'pdf':
                        content = self._read_pdf_file(file_path)
                    elif document.file_type.lower() == 'txt':
                        content = self._read_txt_file(file_path)
                    else:
                        raise IndexingError(
                            f"サポートされていないファイル形式: {document.file_type}",
                            error_code="IDX-005",
                            details={"file_type": document.file_type, "file_path": document.file_path}
                        )
                    # ドキュメントのcontentを更新
                    document.content = content
                else:
                    raise IndexingError(
                        "ドキュメントの内容またはファイルパスが必要です",
                        error_code="IDX-006"
                    )
            
            # テキストをチャンクに分割
            text_chunks = self._split_text_into_chunks(document.content)
            if not text_chunks:
                raise IndexingError(
                    f"テキストチャンクの生成に失敗: {document.filename}",
                    error_code="IDX-007",
                    details={"filename": document.filename}
                )
            
            self.check_cancellation()
            
            # 埋め込みベクトルを生成
            embeddings = self._create_embeddings(text_chunks)
            
            self.check_cancellation()
            
            # ドキュメントIDを生成
            document_id = document.document_id
            
            # メタデータを準備
            metadatas = []
            ids = []
            for i, chunk in enumerate(text_chunks):
                chunk_id = f"{document_id}_{i}"
                metadata = {
                    "filename": document.filename,
                    "file_path": document.file_path or "",
                    "file_type": document.file_type,
                    "file_size": document.file_size,
                    "chunk_index": i,
                    "document_id": document_id,
                    "created_at": document.created_at.isoformat() if document.created_at else ""
                }
                metadatas.append(metadata)
                ids.append(chunk_id)
            
            # ChromaDBコレクションに追加
            self.collection.add(
                documents=text_chunks,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            self.logger.info(f"ドキュメントインデックス追加完了: {document.filename}", extra={
                "document_id": document_id,
                "filename": document.filename,
                "chunks_count": len(text_chunks)
            })
            
            return document_id
            
        except IndexingError:
            raise
        except Exception as e:
            raise IndexingError(
                f"ドキュメントインデックス追加エラー: {document.filename} - {e}",
                error_code="IDX-008",
                details={"filename": document.filename, "original_error": str(e)}
            ) from e
    
    def add_documents(self, documents: List[Document]) -> List[str]:
        """
        複数のドキュメントを一括でインデックスに追加
        
        Args:
            documents: 追加するドキュメントリスト
            
        Returns:
            List[str]: 追加されたドキュメントIDリスト
        """
        document_ids = []
        total_docs = len(documents)
        
        # 進捗表示が必要な場合のみProgressTrackerを使用
        progress_tracker = None
        if should_show_progress(total_docs * 2):  # 1ドキュメントあたり約2秒と仮定
            progress_tracker = ProgressTracker(
                total=total_docs,
                description="ドキュメントインデックス作成"
            )
        
        try:
            for i, document in enumerate(documents):
                self.check_cancellation()
                
                if progress_tracker:
                    progress_tracker.update(
                        message=f"処理中: {document.filename} ({i+1}/{total_docs})"
                    )
                
                document_id = self.add_document(document)
                document_ids.append(document_id)
            
            if progress_tracker:
                progress_tracker.finish("インデックス作成完了")
            
            return document_ids
            
        except Exception as e:
            if progress_tracker:
                progress_tracker.cancel()
            raise
    
    def search_documents(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        ドキュメントを検索
        
        Args:
            query: 検索クエリ
            top_k: 上位K件を取得
            
        Returns:
            List[Dict[str, Any]]: 検索結果リスト
        """
        try:
            # クエリの埋め込みベクトルを生成
            query_embedding = self._create_embeddings([query])[0]
            
            # ChromaDBで検索実行
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            # 結果を整形
            search_results = []
            for i in range(len(results['documents'][0])):
                search_results.append({
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i]
                })
            
            self.logger.info(f"ドキュメント検索完了", extra={
                "query": query,
                "results_count": len(search_results),
                "top_k": top_k
            })
            
            return search_results
            
        except Exception as e:
            raise IndexingError(
                f"ドキュメント検索エラー: {e}",
                error_code="IDX-009",
                details={"query": query, "top_k": top_k, "original_error": str(e)}
            ) from e
    
    def update_document(self, document_id: str, updated_document: Document) -> bool:
        """
        ドキュメントを更新
        
        Args:
            document_id: 更新対象ドキュメントID
            updated_document: 更新後のドキュメント
            
        Returns:
            bool: 更新成功フラグ
        """
        try:
            # 既存のドキュメントを削除
            self.delete_document(document_id)
            
            # 新しいドキュメントを追加 (IDを維持)
            updated_document.document_id = document_id
            self.add_document(updated_document)
            
            return True
            
        except Exception as e:
            raise IndexingError(
                f"ドキュメント更新エラー: {document_id} - {e}",
                error_code="IDX-010",
                details={"document_id": document_id, "original_error": str(e)}
            ) from e
    
    def delete_document(self, document_id: str) -> bool:
        """
        ドキュメントをインデックスから削除
        
        Args:
            document_id: 削除対象ドキュメントID
            
        Returns:
            bool: 削除成功フラグ
        """
        try:
            # ドキュメントのチャンクIDを検索
            results = self.collection.get(
                where={"document_id": document_id},
                include=["metadatas"]
            )
            
            if not results['ids']:
                raise IndexingError(
                    f"削除対象ドキュメントが見つかりません: {document_id}",
                    error_code="IDX-004",
                    details={"document_id": document_id}
                )
            
            # 関連するチャンクIDをすべて削除
            chunk_ids = results['ids']
            self.collection.delete(ids=chunk_ids)
            
            self.logger.info(f"ドキュメント削除完了: {document_id}", extra={
                "document_id": document_id,
                "deleted_chunks": len(chunk_ids)
            })
            
            return True
            
        except IndexingError:
            raise
        except Exception as e:
            raise IndexingError(
                f"ドキュメント削除エラー: {document_id} - {e}",
                error_code="IDX-004",
                details={"document_id": document_id, "original_error": str(e)}
            ) from e
    
    def clear_collection(self) -> bool:
        """
        コレクション内の全ドキュメントをクリア
        
        Returns:
            bool: クリア成功フラグ
        """
        try:
            # コレクション内のドキュメント数を確認
            doc_count = self.collection.count()
            
            if doc_count > 0:
                # 全ドキュメントを削除
                self.collection.delete(
                    where={}  # 空の条件で全削除
                )
            
            self.logger.info(f"コレクションクリア完了", extra={
                "collection_name": self.collection_name,
                "deleted_documents": doc_count
            })
            
            return True
            
        except Exception as e:
            raise IndexingError(
                f"コレクションクリアエラー: {e}",
                error_code="IDX-011",
                details={"collection_name": self.collection_name, "original_error": str(e)}
            ) from e
    
    def rebuild_from_directory(self, directory_path: Path) -> List[str]:
        """
        ディレクトリからインデックスを再構築
        
        Args:
            directory_path: 処理対象ディレクトリ
            
        Returns:
            List[str]: 追加されたドキュメントIDリスト
        """
        try:
            # サポート対象ファイルを収集
            supported_extensions = ['*.pdf', '*.txt']
            file_paths = []
            
            for ext in supported_extensions:
                file_paths.extend(directory_path.glob(f"**/{ext}"))
            
            if not file_paths:
                self.logger.warning(f"処理対象ファイルが見つかりません: {directory_path}")
                return []
            
            # ドキュメントオブジェクトを作成
            documents = []
            for file_path in file_paths:
                doc = Document.from_file(file_path)
                documents.append(doc)
            
            # 一括でインデックスに追加
            document_ids = self.add_documents(documents)
            
            self.logger.info(f"ディレクトリからインデックス再構築完了", extra={
                "directory_path": str(directory_path),
                "processed_files": len(file_paths),
                "document_ids": len(document_ids)
            })
            
            return document_ids
            
        except Exception as e:
            raise IndexingError(
                f"ディレクトリインデックス再構築エラー: {directory_path} - {e}",
                error_code="IDX-012",
                details={"directory_path": str(directory_path), "original_error": str(e)}
            ) from e
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        コレクション統計情報を取得
        
        Returns:
            Dict[str, Any]: コレクション統計情報
        """
        try:
            doc_count = self.collection.count()
            
            return {
                "collection_name": self.collection_name,
                "document_count": doc_count,
                "db_path": str(self.db_path),
                "embedding_model": self.embedding_model
            }
            
        except Exception as e:
            self.logger.warning(f"統計情報取得エラー: {e}")
            return {
                "collection_name": self.collection_name,
                "document_count": 0,
                "db_path": str(self.db_path),
                "embedding_model": self.embedding_model,
                "error": str(e)
            }
    
    def rebuild_index_from_folders(self, folder_paths: List[str]) -> bool:
        """
        指定されたフォルダパスから文書を読み込み、インデックスを再構築します。

        Args:
            folder_paths: インデックス化するフォルダのパスリスト

        Returns:
            bool: 成功した場合True

        Raises:
            IndexingError: インデックス再構築に失敗した場合
        """
        self.logger.info(f"フォルダからインデックス再構築開始: {folder_paths}")
        try:
            self.clear_collection() # 既存のインデックスをクリア

            total_files_to_process = 0
            for folder_path_str in folder_paths:
                folder_path = Path(folder_path_str)
                if folder_path.is_dir():
                    # サポート対象ファイルを収集 (rebuild_from_directoryと同じロジック)
                    supported_extensions = ['*.pdf', '*.txt']
                    for ext in supported_extensions:
                        total_files_to_process += len(list(folder_path.glob(f"**/{ext}")))
                else:
                    self.logger.warning(f"指定されたパスはディレクトリではありません: {folder_path_str}")

            if total_files_to_process == 0:
                self.logger.info("処理対象ファイルが見つかりませんでした。")
                return True

            progress_tracker = ProgressTracker(
                total=total_files_to_process,
                description="フォルダからインデックスを再構築中"
            )

            processed_files_count = 0
            for folder_path_str in folder_paths:
                folder_path = Path(folder_path_str)
                if folder_path.is_dir():
                    self.check_cancellation()
                    self.logger.info(f"フォルダ処理中: {folder_path_str}")
                    
                    # rebuild_from_directoryのロジックをここに統合
                    supported_extensions = ['*.pdf', '*.txt']
                    file_paths = []
                    for ext in supported_extensions:
                        file_paths.extend(folder_path.glob(f"**/{ext}"))

                    for file_path in file_paths:
                        self.check_cancellation()
                        doc = Document.from_file(file_path)
                        self.add_document(doc) # 個別にドキュメントを追加
                        processed_files_count += 1
                        progress_tracker.update(
                            processed_files_count,
                            message=f"処理中: {file_path.name} ({processed_files_count}/{total_files_to_process})"
                        )
                
            progress_tracker.finish("インデックス再構築完了")
            self.logger.info("フォルダからのインデックス再構築完了")
            return True

        except Exception as e:
            self.logger.error(f"フォルダからのインデックス再構築エラー: {e}")
            if 'progress_tracker' in locals() and progress_tracker:
                progress_tracker.cancel()
            raise IndexingError(f"フォルダからのインデックス再構築に失敗しました: {e}")