"""
ChromaDBインデックス機能のテストスイート (TDD Red フェーズ)
PDF/TXT読み込み・ベクトル化・インデックス管理機能のテストを定義
"""

import pytest
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import Mock, patch, mock_open
import tempfile
import shutil

from src.models.document import Document
from src.exceptions.base_exceptions import IndexingError
from src.logic.indexing import ChromaDBIndexer


class TestChromaDBIndexer:
    """ChromaDBIndexer クラスのテストスイート"""
    
    def setup_method(self):
        """各テスト前の初期化処理"""
        self.test_db_path = Path("./test_chroma_db")
        self.indexer = ChromaDBIndexer(
            collection_name="test_collection",
            db_path=str(self.test_db_path)
        )
    
    def teardown_method(self):
        """各テスト後のクリーンアップ処理"""
        if self.test_db_path.exists():
            shutil.rmtree(self.test_db_path)
    
    # インデックス作成テスト
    
    def test_read_pdf_file_success(self):
        """PDF ファイル読み込み成功テスト (Red フェーズ)"""
        # 期待される動作: PDFファイルからテキスト抽出
        pdf_path = Path("test.pdf")
        
        with patch("PyPDF2.PdfReader") as mock_reader:
            # モックPDFリーダーの設定
            mock_page = Mock()
            mock_page.extract_text.return_value = "テストPDFの内容です。\n複数行にわたるテキストです。"
            mock_reader.return_value.pages = [mock_page]
            
            # テスト実行
            result = self.indexer._read_pdf_file(pdf_path)
            
            # 検証
            assert result == "テストPDFの内容です。\n複数行にわたるテキストです。"
    
    def test_read_pdf_file_empty(self):
        """空のPDFファイル読み込みテスト (Red フェーズ)"""
        pdf_path = Path("empty.pdf")
        
        with patch("PyPDF2.PdfReader") as mock_reader:
            mock_reader.return_value.pages = []
            
            # IndexingError が発生することを期待
            with pytest.raises(IndexingError) as exc_info:
                self.indexer._read_pdf_file(pdf_path)
            
            assert exc_info.value.error_code == "IDX-001"
            assert "空のPDFファイル" in str(exc_info.value)
    
    def test_read_pdf_file_corrupted(self):
        """破損したPDFファイル読み込みテスト (Red フェーズ)"""
        pdf_path = Path("corrupted.pdf")
        
        with patch("PyPDF2.PdfReader", side_effect=Exception("PDF reading error")):
            with pytest.raises(IndexingError) as exc_info:
                self.indexer._read_pdf_file(pdf_path)
            
            assert exc_info.value.error_code == "IDX-002"
            assert "PDFファイル読み込みエラー" in str(exc_info.value)
    
    def test_read_txt_file_success(self):
        """TXT ファイル読み込み成功テスト (Red フェーズ)"""
        txt_content = "テストTXTファイルの内容です。\nUTF-8エンコードされています。"
        
        with patch("builtins.open", mock_open(read_data=txt_content)):
            result = self.indexer._read_txt_file(Path("test.txt"))
            assert result == txt_content
    
    def test_read_txt_file_encoding_error(self):
        """TXTファイル文字エンコードエラーテスト (Red フェーズ)"""
        txt_path = Path("invalid_encoding.txt")
        
        with patch("builtins.open", side_effect=UnicodeDecodeError(
            'utf-8', b'', 0, 1, 'invalid start byte'
        )):
            with pytest.raises(IndexingError) as exc_info:
                self.indexer._read_txt_file(txt_path)
            
            assert exc_info.value.error_code == "IDX-003"
            assert "文字エンコードエラー" in str(exc_info.value)
    
    def test_split_text_into_chunks(self):
        """テキストチャンク分割テスト (Red フェーズ)"""
        long_text = "テスト文書です。" * 100  # 長いテキストを生成
        
        chunks = self.indexer._split_text_into_chunks(
            long_text, 
            chunk_size=50, 
            chunk_overlap=10
        )
        
        # チャンクが作成されることを確認
        assert len(chunks) > 1
        # 各チャンクのサイズが制限内であることを確認
        for chunk in chunks:
            assert len(chunk) <= 50
        # オーバーラップが機能していることを確認 (詳細実装後に検証)
    
    def test_create_embeddings(self):
        """テキスト埋め込み生成テスト (Red フェーズ)"""
        text_chunks = ["テストチャンク1", "テストチャンク2", "テストチャンク3"]
        
        with patch.object(self.indexer, "_embedding_function") as mock_embedding:
            mock_embedding.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]
            
            embeddings = self.indexer._create_embeddings(text_chunks)
            
            assert len(embeddings) == 3
            assert embeddings[0] == [0.1, 0.2, 0.3]
    
    def test_add_document_to_index(self):
        """ドキュメントインデックス追加テスト (Red フェーズ)"""
        document = Document(
            file_path="/test/path/document.pdf",
            filename="document.pdf",
            content="テストドキュメントの内容です。",
            file_type="pdf",
            file_size=1024
        )
        
        with patch.object(self.indexer, "collection") as mock_collection:
            # インデックス追加実行
            result = self.indexer.add_document(document)
            
            # ドキュメントIDが返されることを確認
            assert result is not None
            assert isinstance(result, str)
            
            # ChromaDBのコレクションに追加されたことを確認
            mock_collection.add.assert_called_once()
    
    def test_add_multiple_documents(self):
        """複数ドキュメント一括インデックス追加テスト (Red フェーズ)"""
        documents = [
            Document(
                file_path="/test/doc1.pdf",
                filename="doc1.pdf", 
                content="ドキュメント1の内容",
                file_type="pdf",
                file_size=512
            ),
            Document(
                file_path="/test/doc2.txt",
                filename="doc2.txt",
                content="ドキュメント2の内容", 
                file_type="txt",
                file_size=256
            )
        ]
        
        with patch.object(self.indexer, "collection") as mock_collection:
            results = self.indexer.add_documents(documents)
            
            assert len(results) == 2
            assert all(isinstance(doc_id, str) for doc_id in results)
    
    def test_search_documents(self):
        """ドキュメント検索テスト (Red フェーズ)"""
        query = "検索クエリのテスト"
        
        with patch.object(self.indexer, "collection") as mock_collection:
            # モック検索結果の設定
            mock_collection.query.return_value = {
                'documents': [["関連ドキュメント1", "関連ドキュメント2"]],
                'metadatas': [[
                    {"filename": "doc1.pdf", "file_path": "/test/doc1.pdf"},
                    {"filename": "doc2.txt", "file_path": "/test/doc2.txt"}
                ]],
                'distances': [[0.1, 0.3]]
            }
            
            results = self.indexer.search_documents(query, top_k=2)
            
            assert len(results) == 2
            assert results[0]['content'] == "関連ドキュメント1"
            assert results[0]['metadata']['filename'] == "doc1.pdf"
            assert results[0]['distance'] == 0.1
    
    def test_get_collection_stats(self):
        """コレクション統計情報取得テスト (Red フェーズ)"""
        with patch.object(self.indexer, "collection") as mock_collection:
            mock_collection.count.return_value = 5
            
            stats = self.indexer.get_collection_stats()
            
            assert stats['document_count'] == 5
            assert 'collection_name' in stats
            assert stats['collection_name'] == "test_collection"


class TestIndexingManager:
    """インデックス管理機能のテストスイート"""
    
    def setup_method(self):
        """各テスト前の初期化処理"""
        self.test_db_path = Path("./test_crud_db")
        self.indexer = ChromaDBIndexer(
            collection_name="test_crud",
            db_path=str(self.test_db_path)
        )
    
    def teardown_method(self):
        """各テスト後のクリーンアップ処理"""
        if self.test_db_path.exists():
            shutil.rmtree(self.test_db_path)
    
    def test_update_document_index(self):
        """ドキュメントインデックス更新テスト (Red フェーズ)"""
        # 更新対象ドキュメント
        document_id = "test_doc_123"
        updated_document = Document(
            file_path="/test/updated_doc.pdf",
            filename="updated_doc.pdf",
            content="更新されたドキュメントの内容",
            file_type="pdf",
            file_size=2048
        )
        
        with patch.object(self.indexer, "delete_document", return_value=True) as mock_delete:
            with patch.object(self.indexer, "add_document", return_value=document_id) as mock_add:
                result = self.indexer.update_document(document_id, updated_document)
                
                # 更新が成功したことを確認
                assert result is True
                
                # 削除→追加の順序で呼ばれることを確認
                mock_delete.assert_called_once_with(document_id)
                mock_add.assert_called_once()
                
                # ドキュメントIDが維持されることを確認
                assert updated_document.document_id == document_id
    
    def test_delete_document_from_index(self):
        """ドキュメントインデックス削除テスト (Red フェーズ)"""
        document_id = "test_doc_456"
        
        with patch.object(self.indexer, "collection") as mock_collection:
            # 削除対象のチャンクが存在することをモック
            mock_collection.get.return_value = {
                'ids': [f"{document_id}_0", f"{document_id}_1", f"{document_id}_2"]
            }
            
            result = self.indexer.delete_document(document_id)
            
            assert result is True
            mock_collection.get.assert_called_once()
            mock_collection.delete.assert_called_once()
    
    def test_delete_nonexistent_document(self):
        """存在しないドキュメント削除テスト (Red フェーズ)"""
        document_id = "nonexistent_doc"
        
        with patch.object(self.indexer, "collection") as mock_collection:
            # 削除対象のドキュメントが見つからない場合をモック
            mock_collection.get.return_value = {'ids': []}
            
            with pytest.raises(IndexingError) as exc_info:
                self.indexer.delete_document(document_id)
            
            assert exc_info.value.error_code == "IDX-004"
            assert "削除対象ドキュメントが見つかりません" in str(exc_info.value)
    
    def test_clear_all_documents(self):
        """全ドキュメントクリアテスト (Red フェーズ)"""
        with patch.object(self.indexer, "collection") as mock_collection:
            mock_collection.count.return_value = 10
            
            result = self.indexer.clear_collection()
            
            assert result is True
            mock_collection.count.assert_called_once()
            mock_collection.delete.assert_called_once_with(where={})
    
    def test_rebuild_index_from_directory(self):
        """ディレクトリからインデックス再構築テスト (Red フェーズ)"""
        test_directory = Path("/test/documents")
        
        with patch.object(test_directory, "glob") as mock_glob:
            # テスト用ファイルリストを設定
            mock_files = [
                Path("/test/documents/doc1.pdf"),
                Path("/test/documents/doc2.txt"),
                Path("/test/documents/doc3.pdf")
            ]
            
            # glob呼び出しに対するモック設定
            def mock_glob_side_effect(pattern):
                if pattern == "**/pdf":
                    return [Path("/test/documents/doc1.pdf"), Path("/test/documents/doc3.pdf")]
                elif pattern == "**/txt": 
                    return [Path("/test/documents/doc2.txt")]
                return []
            
            mock_glob.side_effect = mock_glob_side_effect
            
            # Document.from_fileとadd_documentsをモック
            with patch("src.models.document.Document.from_file") as mock_from_file:
                with patch.object(self.indexer, "add_documents") as mock_add_docs:
                    
                    # from_fileのモック設定
                    mock_documents = [
                        Document(file_path=str(f), filename=f.name, content="test", file_type="test", file_size=100)
                        for f in mock_files
                    ]
                    mock_from_file.side_effect = mock_documents
                    mock_add_docs.return_value = ["doc1_id", "doc2_id", "doc3_id"]
                    
                    results = self.indexer.rebuild_from_directory(test_directory)
                    
                    # 結果の検証
                    assert len(results) == 3


class TestIndexingPerformance:
    """インデックス性能テスト (Red フェーズ)"""
    
    def test_large_document_processing(self):
        """大容量ドキュメント処理性能テスト"""
        # 大容量テキスト (1MB相当)
        large_content = "テスト文書の内容です。" * 50000
        
        large_document = Document(
            file_path="/test/large_doc.txt",
            filename="large_doc.txt",
            content=large_content,
            file_type="txt",
            file_size=len(large_content.encode('utf-8'))
        )
        
        indexer = ChromaDBIndexer("performance_test")
        
        with patch.object(indexer, "collection"):
            # 処理時間の測定 (実装後に時間検証を追加)
            result = indexer.add_document(large_document)
            assert result is not None
    
    def test_concurrent_indexing(self):
        """並行インデックス処理テスト"""
        documents = [
            Document(
                file_path=f"/test/doc_{i}.txt",
                filename=f"doc_{i}.txt",
                content=f"ドキュメント{i}の内容です。",
                file_type="txt",
                file_size=100
            )
            for i in range(10)
        ]
        
        indexer = ChromaDBIndexer("concurrent_test")
        
        with patch.object(indexer, "collection"):
            # 並行処理での一括追加 (実装後に並行処理検証を追加)
            results = indexer.add_documents(documents)
            assert len(results) == 10