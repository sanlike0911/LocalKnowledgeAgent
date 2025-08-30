"""
ChatHistoryモデル実装 (TDD Green フェーズ)
設計書準拠のチャット履歴管理モデルクラス
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


class ChatHistoryValidationError(Exception):
    """チャット履歴データ検証エラー"""

    pass


@dataclass
class ChatHistory:
    """
    チャット履歴管理モデルクラス

    Attributes:
        messages: メッセージリスト
        max_messages: 最大メッセージ数
        created_at: 作成日時
    """

    messages: List[Dict[str, Any]] = field(default_factory=list)
    max_messages: int = 50
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """データクラス初期化後の検証処理"""
        self._validate()

    def _validate(self) -> None:
        """チャット履歴データの検証"""
        if self.max_messages <= 0:
            raise ChatHistoryValidationError("max_messagesは1以上である必要があります")

    def add_user_message(self, content: str) -> None:
        """
        ユーザーメッセージを追加

        Args:
            content: メッセージ内容

        Raises:
            ChatHistoryValidationError: メッセージ内容が空の場合
        """
        if not content or not content.strip():
            raise ChatHistoryValidationError("メッセージ内容は必須です")

        message = {
            "role": "user",
            "content": content.strip(),
            "timestamp": datetime.now().isoformat(),
        }

        self._add_message(message)
        logging.info(f"ユーザーメッセージを追加: {len(content)}文字")

    def add_assistant_message(
        self, content: str, sources: Optional[List[str]] = None
    ) -> None:
        """
        アシスタントメッセージを追加

        Args:
            content: メッセージ内容
            sources: 参照ソースリスト

        Raises:
            ChatHistoryValidationError: メッセージ内容が空の場合
        """
        if not content or not content.strip():
            raise ChatHistoryValidationError("メッセージ内容は必須です")

        message = {
            "role": "assistant",
            "content": content.strip(),
            "timestamp": datetime.now().isoformat(),
            "sources": sources,
        }

        self._add_message(message)
        log_message = (
            f"アシスタントメッセージを追加: {len(content)}文字, "
            f"ソース数: {len(sources) if sources else 0}"
        )
        logging.info(log_message)

    def _add_message(self, message: Dict[str, Any]) -> None:
        """
        メッセージを内部リストに追加し、制限を適用

        Args:
            message: メッセージデータ
        """
        self.messages.append(message)

        # 最大メッセージ数の制限を適用
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]
            logging.debug(f"メッセージ履歴を{self.max_messages}件に制限しました")

    def get_recent_messages(self, count: int) -> List[Dict[str, Any]]:
        """
        最新のメッセージを指定数取得

        Args:
            count: 取得するメッセージ数

        Returns:
            List[Dict[str, Any]]: 最新メッセージのリスト
        """
        if count <= 0:
            return []

        return (
            self.messages[-count:]
            if count <= len(self.messages)
            else self.messages.copy()
        )

    def get_conversation_context(self, max_pairs: int = 5) -> str:
        """
        会話コンテキストを文字列形式で取得

        Args:
            max_pairs: 最大会話ペア数

        Returns:
            str: 会話コンテキスト
        """
        if not self.messages:
            return ""

        # 最新のメッセージから遡って会話ペアを構築
        context_lines = []
        current_messages = (
            self.messages[-max_pairs * 2 :]
            if max_pairs * 2 <= len(self.messages)
            else self.messages
        )

        i = 0
        while i < len(current_messages):
            message = current_messages[i]
            role = message["role"].capitalize()
            content = message["content"]

            context_lines.append(f"{role}: {content}")
            i += 1

            # ユーザーメッセージの後にアシスタントメッセージがある場合はペアとして処理
            if (
                message["role"] == "user"
                and i < len(current_messages)
                and current_messages[i]["role"] == "assistant"
            ):
                assistant_message = current_messages[i]
                context_lines.append(f"Assistant: {assistant_message['content']}")
                i += 1

        # 最後のペアが完了していない場合（ユーザーメッセージで終わっている場合）は
        # そのペアだけを返す
        if len(context_lines) % 2 == 1:
            return context_lines[-1] if context_lines else ""

        # 完全なペアのみを使用
        complete_pairs = len(context_lines) // 2
        if complete_pairs > max_pairs:
            # 最新のmax_pairs個のペアのみ使用
            start_index = (complete_pairs - max_pairs) * 2
            context_lines = context_lines[start_index:]

        return "\n".join(context_lines)

    def clear_history(self) -> None:
        """チャット履歴をクリア"""
        self.messages.clear()
        logging.info("チャット履歴をクリアしました")

    def to_dict(self) -> Dict[str, Any]:
        """
        チャット履歴オブジェクトを辞書形式に変換

        Returns:
            Dict[str, Any]: チャット履歴データの辞書
        """
        return {
            "messages": [msg.copy() for msg in self.messages],
            "max_messages": self.max_messages,
            "created_at": self.created_at.isoformat()
            if isinstance(self.created_at, datetime)
            else self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatHistory":
        """
        辞書からチャット履歴オブジェクトを作成

        Args:
            data: チャット履歴データの辞書

        Returns:
            ChatHistory: チャット履歴インスタンス
        """
        # 作成日時の変換
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()

        chat_history = cls(
            messages=data.get("messages", []),
            max_messages=data.get("max_messages", 50),
            created_at=created_at,
        )

        return chat_history

    def get_messages_by_role(self, role: str) -> List[Dict[str, Any]]:
        """
        指定された役割のメッセージを取得

        Args:
            role: メッセージの役割 ("user" or "assistant")

        Returns:
            List[Dict[str, Any]]: 指定役割のメッセージリスト
        """
        return [msg.copy() for msg in self.messages if msg.get("role") == role]

    def get_total_message_count(self) -> int:
        """
        総メッセージ数を取得

        Returns:
            int: 総メッセージ数
        """
        return len(self.messages)

    def has_messages(self) -> bool:
        """
        メッセージが存在するかチェック

        Returns:
            bool: メッセージが存在する場合True
        """
        return len(self.messages) > 0

    def get_last_user_message(self) -> Optional[Dict[str, Any]]:
        """
        最後のユーザーメッセージを取得

        Returns:
            Optional[Dict[str, Any]]: 最後のユーザーメッセージ（存在しない場合None）
        """
        for message in reversed(self.messages):
            if message.get("role") == "user":
                return message.copy()
        return None

    def get_last_assistant_message(self) -> Optional[Dict[str, Any]]:
        """
        最後のアシスタントメッセージを取得

        Returns:
            Optional[Dict[str, Any]]: 最後のアシスタントメッセージ（存在しない場合None）
        """
        for message in reversed(self.messages):
            if message.get("role") == "assistant":
                return message.copy()
        return None

    def get_message_statistics(self) -> Dict[str, int]:
        """
        メッセージの統計情報を取得

        Returns:
            Dict[str, int]: 統計情報の辞書
        """
        user_count = len([msg for msg in self.messages if msg.get("role") == "user"])
        assistant_count = len(
            [msg for msg in self.messages if msg.get("role") == "assistant"]
        )

        return {
            "total_messages": len(self.messages),
            "user_messages": user_count,
            "assistant_messages": assistant_count,
            "max_messages": self.max_messages,
        }

    def __str__(self) -> str:
        """チャット履歴の文字列表現"""
        return f"ChatHistory(messages={len(self.messages)}, max_messages={self.max_messages})"

    def __repr__(self) -> str:
        """チャット履歴の詳細文字列表現"""
        stats = self.get_message_statistics()
        return (
            f"ChatHistory(total_messages={stats['total_messages']}, "
            f"user_messages={stats['user_messages']}, "
            f"assistant_messages={stats['assistant_messages']}, "
            f"max_messages={self.max_messages}, "
            f"created_at='{self.created_at}')"
        )
