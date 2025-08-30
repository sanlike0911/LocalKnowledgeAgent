"""
Documentモデルのテストケース (TDD Red フェーズ)
CLAUDE.md準拠のTDD実装手順に従う
"""

from datetime import datetime



import pytest


class TestDocumentModel:
    """Documentモデルのテストクラス"""

    def test_document_creation_with_valid_data(self) -> None:
        """有効なデータでDocumentインスタンスが作成できることをテスト"""
        # このテストは失敗する予定 (Red フェーズ)
        from src.models.document import Document

        doc = Document(
            id="doc_001",
            title="テスト文書",
            content="これはテスト用の文書内容です。",
            file_path="/path/to/test.pdf",
            file_type="pdf",
            file_size=1024,
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 12, 0, 0),
        )

        assert doc.id == "doc_001"
        assert doc.title == "テスト文書"
        assert doc.content == "これはテスト用の文書内容です。"
        assert doc.file_path == "/path/to/test.pdf"
        assert doc.file_type == "pdf"
        assert doc.file_size == 1024
        assert isinstance(doc.created_at, datetime)
        assert isinstance(doc.updated_at, datetime)

    def test_document_validation_empty_id(self) -> None:
        """空のIDでDocument作成時にエラーが発生することをテスト"""
        from src.models.document import Document, DocumentValidationError

        with pytest.raises(DocumentValidationError, match="IDは必須です"):
            Document(
                id="",
                title="テスト文書",
                content="内容",
                file_path="/path/to/test.pdf",
                file_type="pdf",
            )

    def test_document_validation_invalid_file_type(self) -> None:
        """サポートされていないファイル形式でエラーが発生することをテスト"""
        from src.models.document import Document, DocumentValidationError

        with pytest.raises(DocumentValidationError, match="サポートされていないファイル形式"):
            Document(
                id="doc_001",
                title="テスト文書",
                content="内容",
                file_path="/path/to/test.exe",
                file_type="exe",
            )

    def test_document_validation_negative_file_size(self) -> None:
        """負のファイルサイズでエラーが発生することをテスト"""
        from src.models.document import Document, DocumentValidationError

        with pytest.raises(DocumentValidationError, match="ファイルサイズは0以上である必要があります"):
            Document(
                id="doc_001",
                title="テスト文書",
                content="内容",
                file_path="/path/to/test.pdf",
                file_type="pdf",
                file_size=-100,
            )

    def test_document_to_dict(self) -> None:
        """Documentオブジェクトが辞書形式に変換できることをテスト"""
        from src.models.document import Document

        doc = Document(
            id="doc_001",
            title="テスト文書",
            content="内容",
            file_path="/path/to/test.pdf",
            file_type="pdf",
        )

        doc_dict = doc.to_dict()

        assert isinstance(doc_dict, dict)
        assert doc_dict["id"] == "doc_001"
        assert doc_dict["title"] == "テスト文書"
        assert doc_dict["content"] == "内容"
        assert doc_dict["file_path"] == "/path/to/test.pdf"
        assert doc_dict["file_type"] == "pdf"
        assert "created_at" in doc_dict
        assert "updated_at" in doc_dict

    def test_document_from_dict(self) -> None:
        """辞書からDocumentオブジェクトが作成できることをテスト"""
        from src.models.document import Document

        doc_data = {
            "id": "doc_001",
            "title": "テスト文書",
            "content": "内容",
            "file_path": "/path/to/test.pdf",
            "file_type": "pdf",
            "file_size": 1024,
            "created_at": "2024-01-01T12:00:00",
            "updated_at": "2024-01-01T12:00:00",
        }

        doc = Document.from_dict(doc_data)

        assert doc.id == "doc_001"
        assert doc.title == "テスト文書"
        assert doc.content == "内容"
        assert doc.file_path == "/path/to/test.pdf"
        assert doc.file_type == "pdf"
        assert doc.file_size == 1024

    def test_document_get_file_extension(self) -> None:
        """ファイル拡張子が正しく取得できることをテスト"""
        from src.models.document import Document

        doc = Document(
            id="doc_001",
            title="テスト文書",
            content="内容",
            file_path="/path/to/test.pdf",
            file_type="pdf",
        )

        assert doc.get_file_extension() == ".pdf"

    def test_document_is_pdf(self) -> None:
        """PDFファイルかどうかの判定が正しく動作することをテスト"""
        from src.models.document import Document

        pdf_doc = Document(
            id="doc_001",
            title="PDF文書",
            content="内容",
            file_path="/path/to/test.pdf",
            file_type="pdf",
        )

        txt_doc = Document(
            id="doc_002",
            title="テキスト文書",
            content="内容",
            file_path="/path/to/test.txt",
            file_type="txt",
        )

        assert pdf_doc.is_pdf() is True
        assert txt_doc.is_pdf() is False

    def test_document_get_content_preview(self) -> None:
        """内容のプレビューが正しく取得できることをテスト"""
        from src.models.document import Document

        long_content = "あ" * 200  # 200文字の内容

        doc = Document(
            id="doc_001",
            title="長い文書",
            content=long_content,
            file_path="/path/to/test.txt",
            file_type="txt",
        )

        preview = doc.get_content_preview(max_length=100)

        assert len(preview) <= 103  # "..." を含めて103文字以下
        assert preview.endswith("...")

    def test_document_update_content(self) -> None:
        """文書内容の更新が正しく動作することをテスト"""
        from src.models.document import Document

        doc = Document(
            id="doc_001",
            title="テスト文書",
            content="古い内容",
            file_path="/path/to/test.txt",
            file_type="txt",
        )

        original_updated_at = doc.updated_at

        # 少し待機して時間差を作る
        import time

        time.sleep(0.001)

        doc.update_content("新しい内容")

        assert doc.content == "新しい内容"
        assert doc.updated_at > original_updated_at
