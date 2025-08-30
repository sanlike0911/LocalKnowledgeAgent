"""
Documentモデル実装 (TDD Green フェーズ)
設計書準拠の文書モデルクラス
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class DocumentValidationError(Exception):
    """文書データ検証エラー"""

    pass


@dataclass
class Document:
    """
    文書モデルクラス

    Attributes:
        id: 文書の一意識別子
        title: 文書のタイトル
        content: 文書の内容
        file_path: ファイルパス
        file_type: ファイル形式 (pdf, txt, docx)
        file_size: ファイルサイズ (バイト)
        created_at: 作成日時
        updated_at: 更新日時
    """

    id: str
    title: str
    content: str
    file_path: str
    file_type: str
    file_size: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # サポートされているファイル形式
    SUPPORTED_FILE_TYPES = {"pdf", "txt", "docx"}

    def __post_init__(self) -> None:
        """データクラス初期化後の検証処理"""
        self._validate()

    def _validate(self) -> None:
        """文書データの検証"""
        if not self.id or not self.id.strip():
            raise DocumentValidationError("IDは必須です")

        if self.file_type not in self.SUPPORTED_FILE_TYPES:
            raise DocumentValidationError(
                f"サポートされていないファイル形式: {self.file_type}. "
                f"サポート形式: {', '.join(self.SUPPORTED_FILE_TYPES)}"
            )

        if self.file_size < 0:
            raise DocumentValidationError("ファイルサイズは0以上である必要があります")

    @classmethod
    def create_new(
        cls, title: str, content: str, file_path: str, file_size: Optional[int] = None
    ) -> "Document":
        """
        新規文書インスタンスを作成

        Args:
            title: 文書タイトル
            content: 文書内容
            file_path: ファイルパス
            file_size: ファイルサイズ（指定しない場合は自動取得を試行）

        Returns:
            Document: 新規文書インスタンス
        """
        # ファイル形式を拡張子から推定
        file_ext = Path(file_path).suffix.lower().lstrip(".")
        if file_ext not in cls.SUPPORTED_FILE_TYPES:
            file_ext = "txt"  # デフォルト

        # ファイルサイズの自動取得
        if file_size is None:
            try:
                file_size = Path(file_path).stat().st_size
            except (FileNotFoundError, OSError):
                file_size = len(content.encode("utf-8"))

        return cls(
            id=str(uuid.uuid4()),
            title=title,
            content=content,
            file_path=file_path,
            file_type=file_ext,
            file_size=file_size,
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        文書オブジェクトを辞書形式に変換

        Returns:
            Dict[str, Any]: 文書データの辞書
        """
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "created_at": self.created_at.isoformat()
            if isinstance(self.created_at, datetime)
            else self.created_at,
            "updated_at": self.updated_at.isoformat()
            if isinstance(self.updated_at, datetime)
            else self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Document":
        """
        辞書から文書オブジェクトを作成

        Args:
            data: 文書データの辞書

        Returns:
            Document: 文書インスタンス
        """
        # 日時文字列をdatetimeオブジェクトに変換
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.now()

        return cls(
            id=data["id"],
            title=data["title"],
            content=data["content"],
            file_path=data["file_path"],
            file_type=data["file_type"],
            file_size=data.get("file_size", 0),
            created_at=created_at,
            updated_at=updated_at,
        )

    def get_file_extension(self) -> str:
        """
        ファイル拡張子を取得

        Returns:
            str: ファイル拡張子 (例: ".pdf")
        """
        return f".{self.file_type}"

    def is_pdf(self) -> bool:
        """
        PDFファイルかどうかを判定

        Returns:
            bool: PDFファイルの場合True
        """
        return self.file_type.lower() == "pdf"

    def is_text_file(self) -> bool:
        """
        テキストファイルかどうかを判定

        Returns:
            bool: テキストファイルの場合True
        """
        return self.file_type.lower() in {"txt", "docx"}

    def get_content_preview(self, max_length: int = 100) -> str:
        """
        文書内容のプレビューを取得

        Args:
            max_length: 最大文字数

        Returns:
            str: プレビューテキスト
        """
        if len(self.content) <= max_length:
            return self.content

        return self.content[:max_length] + "..."

    def update_content(self, new_content: str) -> None:
        """
        文書内容を更新

        Args:
            new_content: 新しい内容
        """
        self.content = new_content
        self.updated_at = datetime.now()
        self.file_size = len(new_content.encode("utf-8"))

    def get_word_count(self) -> int:
        """
        文書の単語数を取得

        Returns:
            int: 単語数
        """
        # 日本語の場合は文字数、英語の場合は単語数を返す
        if any(
            "\u3040" <= char <= "\u309F" or "\u30A0" <= char <= "\u30FF"
            for char in self.content
        ):
            # ひらがな・カタカナが含まれている場合は文字数
            return len(self.content.replace(" ", "").replace("\n", ""))
        else:
            # 英語の場合は単語数
            return len(self.content.split())

    def __str__(self) -> str:
        """文書の文字列表現"""
        return f"Document(id={self.id}, title='{self.title}', type={self.file_type})"

    def __repr__(self) -> str:
        """文書の詳細文字列表現"""
        return (
            f"Document(id='{self.id}', title='{self.title}', "
            f"file_type='{self.file_type}', file_size={self.file_size}, "
            f"created_at='{self.created_at}')"
        )
