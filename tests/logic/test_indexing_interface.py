"""
IndexingInterfaceのテストケース (TDD Red フェーズ)
CLAUDE.md準拠のTDD実装手順に従う
"""

import pytest
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock


class TestIndexingInterface:
    """IndexingInterfaceのテストクラス"""
    
    def test_indexing_interface_create_index(self) -> None:
        """インデックス作成機能のテストケース"""
        from src.interfaces.indexing_interface import IndexingInterface
        from src.models.document import Document
        from src.models.config import Config
        
        # テスト用の設定
        config = Config()
        interface = IndexingInterface(config)
        
        # テスト用文書
        documents = [
            Document(
                id="doc1",
                title="テスト文書1",
                content="これはテスト用の文書です。",
                file_path="/path/to/test1.txt",
                file_type="txt"
            )
        ]
        
        # インデックス作成
        result = interface.create_index(documents)
        
        # 結果の検証
        assert result is True
        assert interface.get_document_count() == 1
    
    def test_indexing_interface_search_documents(self) -> None:
        """文書検索機能のテストケース"""
        from src.interfaces.indexing_interface import IndexingInterface
        from src.models.document import Document
        from src.models.config import Config
        
        config = Config()
        interface = IndexingInterface(config)
        
        # テスト用文書を追加
        documents = [
            Document(
                id="doc1",
                title="Python プログラミング",
                content="Pythonは素晴らしいプログラミング言語です。",
                file_path="/path/to/python.txt",
                file_type="txt"
            ),
            Document(
                id="doc2", 
                title="機械学習入門",
                content="機械学習は人工知能の重要な分野です。",
                file_path="/path/to/ml.txt",
                file_type="txt"
            )
        ]
        interface.create_index(documents)
        
        # 検索実行
        results = interface.search_documents("Python", top_k=5)
        
        # 結果の検証
        assert isinstance(results, list)
        assert len(results) > 0
        assert results[0]["document"]["title"] == "Python プログラミング"
        assert "similarity_score" in results[0]
    
    def test_indexing_interface_add_document(self) -> None:
        """単一文書追加機能のテストケース"""
        from src.interfaces.indexing_interface import IndexingInterface
        from src.models.document import Document
        from src.models.config import Config
        
        config = Config()
        interface = IndexingInterface(config)
        
        # 文書を追加
        document = Document(
            id="doc1",
            title="新しい文書",
            content="これは新しく追加された文書です。",
            file_path="/path/to/new.txt",
            file_type="txt"
        )
        
        result = interface.add_document(document)
        
        assert result is True
        assert interface.get_document_count() == 1
    
    def test_indexing_interface_remove_document(self) -> None:
        """文書削除機能のテストケース"""
        from src.interfaces.indexing_interface import IndexingInterface
        from src.models.document import Document
        from src.models.config import Config
        
        config = Config()
        interface = IndexingInterface(config)
        
        # 文書を追加してから削除
        document = Document(
            id="doc1",
            title="削除予定文書",
            content="この文書は削除されます。",
            file_path="/path/to/delete.txt",
            file_type="txt"
        )
        interface.add_document(document)
        
        # 削除実行
        result = interface.remove_document("doc1")
        
        assert result is True
        assert interface.get_document_count() == 0
    
    def test_indexing_interface_clear_index(self) -> None:
        """インデックス全削除機能のテストケース"""
        from src.interfaces.indexing_interface import IndexingInterface
        from src.models.document import Document
        from src.models.config import Config
        
        config = Config()
        interface = IndexingInterface(config)
        
        # 複数文書を追加
        documents = [
            Document(
                id=f"doc{i}",
                title=f"文書{i}",
                content=f"これは文書{i}の内容です。",
                file_path=f"/path/to/doc{i}.txt",
                file_type="txt"
            )
            for i in range(3)
        ]
        interface.create_index(documents)
        
        # インデックス全削除
        result = interface.clear_index()
        
        assert result is True
        assert interface.get_document_count() == 0
    
    def test_indexing_interface_update_document(self) -> None:
        """文書更新機能のテストケース"""
        from src.interfaces.indexing_interface import IndexingInterface
        from src.models.document import Document
        from src.models.config import Config
        
        config = Config()
        interface = IndexingInterface(config)
        
        # 元の文書を追加
        original_doc = Document(
            id="doc1",
            title="元のタイトル",
            content="元の内容です。",
            file_path="/path/to/original.txt",
            file_type="txt"
        )
        interface.add_document(original_doc)
        
        # 更新された文書
        updated_doc = Document(
            id="doc1",
            title="更新されたタイトル",
            content="更新された内容です。",
            file_path="/path/to/updated.txt",
            file_type="txt"
        )
        
        result = interface.update_document(updated_doc)
        
        assert result is True
        assert interface.get_document_count() == 1
        
        # 検索して更新を確認
        results = interface.search_documents("更新", top_k=1)
        assert len(results) > 0
        assert results[0]["document"]["title"] == "更新されたタイトル"
    
    def test_indexing_interface_get_document_by_id(self) -> None:
        """ID による文書取得機能のテストケース"""
        from src.interfaces.indexing_interface import IndexingInterface
        from src.models.document import Document
        from src.models.config import Config
        
        config = Config()
        interface = IndexingInterface(config)
        
        # 文書を追加
        document = Document(
            id="target_doc",
            title="対象文書",
            content="これは対象の文書です。",
            file_path="/path/to/target.txt",
            file_type="txt"
        )
        interface.add_document(document)
        
        # ID で取得
        retrieved_doc = interface.get_document_by_id("target_doc")
        
        assert retrieved_doc is not None
        assert retrieved_doc.id == "target_doc"
        assert retrieved_doc.title == "対象文書"
    
    def test_indexing_interface_get_all_document_ids(self) -> None:
        """全文書ID取得機能のテストケース"""
        from src.interfaces.indexing_interface import IndexingInterface
        from src.models.document import Document
        from src.models.config import Config
        
        config = Config()
        interface = IndexingInterface(config)
        
        # 複数文書を追加
        doc_ids = ["doc1", "doc2", "doc3"]
        for doc_id in doc_ids:
            document = Document(
                id=doc_id,
                title=f"文書_{doc_id}",
                content=f"{doc_id}の内容",
                file_path=f"/path/to/{doc_id}.txt",
                file_type="txt"
            )
            interface.add_document(document)
        
        # 全ID取得
        retrieved_ids = interface.get_all_document_ids()
        
        assert isinstance(retrieved_ids, list)
        assert len(retrieved_ids) == 3
        assert set(retrieved_ids) == set(doc_ids)
    
    def test_indexing_interface_get_index_statistics(self) -> None:
        """インデックス統計情報取得のテストケース"""
        from src.interfaces.indexing_interface import IndexingInterface
        from src.models.document import Document
        from src.models.config import Config
        
        config = Config()
        interface = IndexingInterface(config)
        
        # 複数文書を追加
        documents = [
            Document(
                id=f"doc{i}",
                title=f"文書{i}",
                content=f"これは文書{i}の内容です。" * 10,  # 長いコンテンツ
                file_path=f"/path/to/doc{i}.txt",
                file_type="txt"
            )
            for i in range(5)
        ]
        interface.create_index(documents)
        
        # 統計情報取得
        stats = interface.get_index_statistics()
        
        assert isinstance(stats, dict)
        assert stats["document_count"] == 5
        assert stats["total_size"] > 0
        assert "index_status" in stats
        assert "last_updated" in stats
    
    def test_indexing_interface_validate_configuration(self) -> None:
        """設定検証機能のテストケース"""
        from src.interfaces.indexing_interface import IndexingInterface
        from src.models.config import Config
        
        # 有効な設定
        valid_config = Config(
            chroma_db_path="./valid/path",
            chroma_collection_name="valid_collection"
        )
        
        interface = IndexingInterface(valid_config)
        validation_result = interface.validate_configuration()
        
        assert validation_result["is_valid"] is True
        assert len(validation_result["errors"]) == 0
    
    def test_indexing_interface_error_handling(self) -> None:
        """エラーハンドリングのテストケース"""
        from src.interfaces.indexing_interface import IndexingInterface, IndexingError
        from src.models.config import Config
        
        config = Config()
        interface = IndexingInterface(config)
        
        # 存在しない文書の削除を試行
        with pytest.raises(IndexingError, match="文書が見つかりません"):
            interface.remove_document("nonexistent_doc")
    
    async def test_indexing_interface_async_operations(self) -> None:
        """非同期操作のテストケース"""
        from src.interfaces.indexing_interface import IndexingInterface
        from src.models.document import Document
        from src.models.config import Config
        
        config = Config()
        interface = IndexingInterface(config)
        
        # 大量の文書を非同期で追加
        documents = [
            Document(
                id=f"async_doc{i}",
                title=f"非同期文書{i}",
                content=f"これは非同期で処理される文書{i}です。",
                file_path=f"/path/to/async{i}.txt",
                file_type="txt"
            )
            for i in range(10)
        ]
        
        # 非同期インデックス作成
        result = await interface.create_index_async(documents)
        
        assert result is True
        assert interface.get_document_count() == 10
    
    def test_indexing_interface_progress_callback(self) -> None:
        """進捗コールバック機能のテストケース"""
        from src.interfaces.indexing_interface import IndexingInterface
        from src.models.document import Document
        from src.models.config import Config
        
        config = Config()
        interface = IndexingInterface(config)
        
        # 進捗を追跡するためのコールバック
        progress_updates = []
        
        def progress_callback(current: int, total: int, message: str) -> None:
            progress_updates.append({
                "current": current,
                "total": total,
                "message": message,
                "progress": current / total if total > 0 else 0
            })
        
        # 文書を追加
        documents = [
            Document(
                id=f"progress_doc{i}",
                title=f"進捗文書{i}",
                content=f"これは進捗確認用の文書{i}です。",
                file_path=f"/path/to/progress{i}.txt",
                file_type="txt"
            )
            for i in range(5)
        ]
        
        # 進捗コールバック付きでインデックス作成
        result = interface.create_index_with_progress(documents, progress_callback)
        
        assert result is True
        assert len(progress_updates) > 0
        assert progress_updates[-1]["current"] == progress_updates[-1]["total"]