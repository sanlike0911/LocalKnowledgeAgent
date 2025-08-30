"""
IndexingInterface実装 (TDD Green フェーズ)
設計書準拠のインデックス管理インターフェースクラス
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
import logging
from datetime import datetime
import asyncio
from pathlib import Path

from src.models.document import Document
from src.models.config import Config


class IndexingError(Exception):
    """インデックス処理関連のエラー"""
    pass


class IndexingInterface(ABC):
    """
    インデックス管理インターフェースクラス
    
    ChromaDBを使用したベクトル検索機能を提供する抽象基底クラス
    """
    
    def __init__(self, config: Config):
        """
        インデックスインターフェースを初期化
        
        Args:
            config: アプリケーション設定
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._document_count = 0
        self._index_status = "not_created"
        self._documents: Dict[str, Document] = {}
        self._last_updated = None
        
        # 設定検証
        validation_result = self.validate_configuration()
        if not validation_result["is_valid"]:
            raise IndexingError(f"設定が無効です: {', '.join(validation_result['errors'])}")
    
    @abstractmethod
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
        pass

    def create_index(self, documents: List[Document]) -> bool:
        """
        文書リストからインデックスを作成
        
        Args:
            documents: インデックス化する文書リスト
            
        Returns:
            bool: 成功した場合True
            
        Raises:
            IndexingError: インデックス作成に失敗した場合
        """
        try:
            self.logger.info(f"インデックス作成開始: {len(documents)}件の文書")
            
            # 既存のインデックスをクリア
            self.clear_index()
            
            # 各文書をインデックスに追加
            for doc in documents:
                self._add_document_to_index(doc)
            
            self._index_status = "created"
            self._last_updated = datetime.now()
            
            self.logger.info(f"インデックス作成完了: {len(documents)}件")
            return True
            
        except Exception as e:
            self._index_status = "error"
            self.logger.error(f"インデックス作成エラー: {e}")
            raise IndexingError(f"インデックス作成に失敗しました: {e}")
    
    def search_documents(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        クエリに基づいて文書を検索
        
        Args:
            query: 検索クエリ
            top_k: 取得する最大文書数
            
        Returns:
            List[Dict[str, Any]]: 検索結果リスト
            
        Raises:
            IndexingError: 検索に失敗した場合
        """
        try:
            if not query.strip():
                raise IndexingError("検索クエリは必須です")
            
            if self._index_status != "created":
                raise IndexingError("インデックスが作成されていません")
            
            self.logger.info(f"文書検索実行: query='{query}', top_k={top_k}")
            
            # シンプルなテキストマッチング実装（実際の実装ではベクトル検索を使用）
            results = []
            for doc in self._documents.values():
                if query.lower() in doc.content.lower() or query.lower() in doc.title.lower():
                    # 簡単な類似度スコア計算
                    content_matches = doc.content.lower().count(query.lower())
                    title_matches = doc.title.lower().count(query.lower())
                    similarity_score = (content_matches + title_matches * 2) / (len(doc.content) + len(doc.title))
                    
                    results.append({
                        "document": doc,
                        "similarity_score": similarity_score
                    })
            
            # スコア順でソート
            results.sort(key=lambda x: x["similarity_score"], reverse=True)
            
            # 上位top_k件を返す
            return results[:top_k]
            
        except Exception as e:
            self.logger.error(f"文書検索エラー: {e}")
            raise IndexingError(f"文書検索に失敗しました: {e}")
    
    def add_document(self, document: Document) -> bool:
        """
        単一文書をインデックスに追加
        
        Args:
            document: 追加する文書
            
        Returns:
            bool: 成功した場合True
            
        Raises:
            IndexingError: 文書追加に失敗した場合
        """
        try:
            self.logger.info(f"文書追加: {document.id}")
            
            self._add_document_to_index(document)
            self._last_updated = datetime.now()
            
            return True
            
        except Exception as e:
            self.logger.error(f"文書追加エラー: {e}")
            raise IndexingError(f"文書追加に失敗しました: {e}")
    
    def remove_document(self, document_id: str) -> bool:
        """
        指定されたIDの文書をインデックスから削除
        
        Args:
            document_id: 削除する文書のID
            
        Returns:
            bool: 成功した場合True
            
        Raises:
            IndexingError: 文書削除に失敗した場合
        """
        try:
            if document_id not in self._documents:
                raise IndexingError(f"文書が見つかりません: {document_id}")
            
            self.logger.info(f"文書削除: {document_id}")
            
            del self._documents[document_id]
            self._document_count -= 1
            self._last_updated = datetime.now()
            
            return True
            
        except Exception as e:
            self.logger.error(f"文書削除エラー: {e}")
            raise IndexingError(f"文書削除に失敗しました: {e}")
    
    def clear_index(self) -> bool:
        """
        インデックス全体をクリア
        
        Returns:
            bool: 成功した場合True
            
        Raises:
            IndexingError: インデックスクリアに失敗した場合
        """
        try:
            self.logger.info("インデックス全削除")
            
            self._documents.clear()
            self._document_count = 0
            self._index_status = "not_created"
            self._last_updated = datetime.now()
            
            return True
            
        except Exception as e:
            self.logger.error(f"インデックスクリアエラー: {e}")
            raise IndexingError(f"インデックスクリアに失敗しました: {e}")
    
    def update_document(self, document: Document) -> bool:
        """
        文書を更新
        
        Args:
            document: 更新する文書
            
        Returns:
            bool: 成功した場合True
            
        Raises:
            IndexingError: 文書更新に失敗した場合
        """
        try:
            self.logger.info(f"文書更新: {document.id}")
            
            # 既存文書があれば削除してから追加
            if document.id in self._documents:
                self.remove_document(document.id)
            
            self.add_document(document)
            
            return True
            
        except Exception as e:
            self.logger.error(f"文書更新エラー: {e}")
            raise IndexingError(f"文書更新に失敗しました: {e}")
    
    def get_document_by_id(self, document_id: str) -> Optional[Document]:
        """
        IDで文書を取得
        
        Args:
            document_id: 取得する文書のID
            
        Returns:
            Optional[Document]: 文書（存在しない場合None）
        """
        return self._documents.get(document_id)
    
    def get_all_document_ids(self) -> List[str]:
        """
        全文書のIDリストを取得
        
        Returns:
            List[str]: 文書IDのリスト
        """
        return list(self._documents.keys())
    
    def get_document_count(self) -> int:
        """
        インデックス内の文書数を取得
        
        Returns:
            int: 文書数
        """
        return self._document_count
    
    def get_index_statistics(self) -> Dict[str, Any]:
        """
        インデックスの統計情報を取得
        
        Returns:
            Dict[str, Any]: 統計情報
        """
        total_size = sum(doc.file_size for doc in self._documents.values())
        
        return {
            "document_count": self._document_count,
            "total_size": total_size,
            "index_status": self._index_status,
            "last_updated": self._last_updated.isoformat() if self._last_updated else None,
            "collection_name": self.config.chroma_collection_name,
            "db_path": self.config.chroma_db_path
        }
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        設定を検証
        
        Returns:
            Dict[str, Any]: 検証結果
        """
        errors = []
        
        # ChromaDBパスの検証
        db_path = Path(self.config.chroma_db_path)
        if not db_path.parent.exists():
            try:
                db_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"ChromaDBパスの作成に失敗: {e}")
        
        # コレクション名の検証
        if not self.config.chroma_collection_name:
            errors.append("コレクション名が設定されていません")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }
    
    async def create_index_async(self, documents: List[Document]) -> bool:
        """
        非同期でインデックスを作成
        
        Args:
            documents: インデックス化する文書リスト
            
        Returns:
            bool: 成功した場合True
        """
        try:
            self.logger.info(f"非同期インデックス作成開始: {len(documents)}件")
            
            # 非同期処理のシミュレーション
            await asyncio.sleep(0.1)
            
            # 実際のインデックス作成は同期版を使用
            return self.create_index(documents)
            
        except Exception as e:
            self.logger.error(f"非同期インデックス作成エラー: {e}")
            raise IndexingError(f"非同期インデックス作成に失敗しました: {e}")
    
    def create_index_with_progress(
        self, 
        documents: List[Document], 
        progress_callback: Callable[[int, int, str], None]
    ) -> bool:
        """
        進捗コールバック付きでインデックスを作成
        
        Args:
            documents: インデックス化する文書リスト
            progress_callback: 進捗コールバック関数
            
        Returns:
            bool: 成功した場合True
        """
        try:
            total = len(documents)
            self.logger.info(f"進捗付きインデックス作成開始: {total}件")
            
            # 初期化
            self.clear_index()
            progress_callback(0, total, "インデックス作成を開始します")
            
            # 各文書を処理
            for i, doc in enumerate(documents, 1):
                self._add_document_to_index(doc)
                progress_callback(i, total, f"文書 '{doc.title}' を処理しました")
            
            self._index_status = "created"
            self._last_updated = datetime.now()
            
            progress_callback(total, total, "インデックス作成が完了しました")
            self.logger.info(f"進捗付きインデックス作成完了: {total}件")
            
            return True
            
        except Exception as e:
            self._index_status = "error"
            progress_callback(-1, len(documents), f"エラーが発生しました: {e}")
            self.logger.error(f"進捗付きインデックス作成エラー: {e}")
            raise IndexingError(f"進捗付きインデックス作成に失敗しました: {e}")
    
    def _add_document_to_index(self, document: Document) -> None:
        """
        文書を内部インデックスに追加（プライベートメソッド）
        
        Args:
            document: 追加する文書
        """
        self._documents[document.id] = document
        self._document_count += 1
        
        # 実際の実装では、ここでChromaDBにベクトルを保存する
        self.logger.debug(f"文書をインデックスに追加: {document.id}")
    
    def __str__(self) -> str:
        """インデックスの文字列表現"""
        return f"IndexingInterface(documents={self._document_count}, status={self._index_status})"
    
    def __repr__(self) -> str:
        """インデックスの詳細文字列表現"""
        return (
            f"IndexingInterface(document_count={self._document_count}, "
            f"index_status='{self._index_status}', "
            f"collection_name='{self.config.chroma_collection_name}', "
            f"last_updated='{self._last_updated}')"
        )