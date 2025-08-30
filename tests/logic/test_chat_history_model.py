"""
ChatHistoryモデルのテストケース (TDD Red フェーズ)
CLAUDE.md準拠のTDD実装手順に従う
"""

from datetime import datetime


import pytest


class TestChatHistoryModel:
    """ChatHistoryモデルのテストクラス"""

    def test_chat_history_creation_empty(self) -> None:
        """空のChatHistoryインスタンスが作成できることをテスト"""
        from src.models.chat_history import ChatHistory

        chat_history = ChatHistory()

        assert len(chat_history.messages) == 0
        assert chat_history.max_messages == 50
        assert isinstance(chat_history.created_at, datetime)

    def test_chat_history_creation_with_max_messages(self) -> None:
        """max_messagesを指定してChatHistoryが作成できることをテスト"""
        from src.models.chat_history import ChatHistory

        chat_history = ChatHistory(max_messages=100)

        assert chat_history.max_messages == 100
        assert len(chat_history.messages) == 0

    def test_chat_history_validation_invalid_max_messages(self) -> None:
        """無効なmax_messagesでエラーが発生することをテスト"""
        from src.models.chat_history import ChatHistory, ChatHistoryValidationError

        with pytest.raises(
            ChatHistoryValidationError, match="max_messagesは1以上である必要があります"
        ):
            ChatHistory(max_messages=0)

        with pytest.raises(
            ChatHistoryValidationError, match="max_messagesは1以上である必要があります"
        ):
            ChatHistory(max_messages=-5)

    def test_add_user_message(self) -> None:
        """ユーザーメッセージの追加が正しく動作することをテスト"""
        from src.models.chat_history import ChatHistory

        chat_history = ChatHistory()

        chat_history.add_user_message("こんにちは")

        assert len(chat_history.messages) == 1
        assert chat_history.messages[0]["role"] == "user"
        assert chat_history.messages[0]["content"] == "こんにちは"
        assert "timestamp" in chat_history.messages[0]
        assert "sources" not in chat_history.messages[0]

    def test_add_assistant_message(self) -> None:
        """アシスタントメッセージの追加が正しく動作することをテスト"""
        from src.models.chat_history import ChatHistory

        chat_history = ChatHistory()
        sources = ["document1.pdf", "document2.txt"]

        chat_history.add_assistant_message("こんにちは！何かお手伝いできることはありますか？", sources)

        assert len(chat_history.messages) == 1
        assert chat_history.messages[0]["role"] == "assistant"
        assert chat_history.messages[0]["content"] == "こんにちは！何かお手伝いできることはありますか？"
        assert chat_history.messages[0]["sources"] == sources
        assert "timestamp" in chat_history.messages[0]

    def test_add_assistant_message_without_sources(self) -> None:
        """ソースなしでアシスタントメッセージを追加できることをテスト"""
        from src.models.chat_history import ChatHistory

        chat_history = ChatHistory()

        chat_history.add_assistant_message("回答です")

        assert len(chat_history.messages) == 1
        assert chat_history.messages[0]["role"] == "assistant"
        assert chat_history.messages[0]["content"] == "回答です"
        assert chat_history.messages[0]["sources"] is None

    def test_add_message_validation_empty_content(self) -> None:
        """空の内容でメッセージ追加時にエラーが発生することをテスト"""
        from src.models.chat_history import ChatHistory, ChatHistoryValidationError

        chat_history = ChatHistory()

        with pytest.raises(ChatHistoryValidationError, match="メッセージ内容は必須です"):
            chat_history.add_user_message("")

        with pytest.raises(ChatHistoryValidationError, match="メッセージ内容は必須です"):
            chat_history.add_assistant_message("   ")

    def test_max_messages_limit(self) -> None:
        """最大メッセージ数制限が正しく動作することをテスト"""
        from src.models.chat_history import ChatHistory

        chat_history = ChatHistory(max_messages=3)

        # 4つのメッセージを追加
        chat_history.add_user_message("メッセージ1")
        chat_history.add_assistant_message("回答1")
        chat_history.add_user_message("メッセージ2")
        chat_history.add_assistant_message("回答2")

        # 最新3つだけが残っていることを確認
        assert len(chat_history.messages) == 3
        assert chat_history.messages[0]["content"] == "回答1"
        assert chat_history.messages[1]["content"] == "メッセージ2"
        assert chat_history.messages[2]["content"] == "回答2"

    def test_get_recent_messages(self) -> None:
        """最新メッセージの取得が正しく動作することをテスト"""
        from src.models.chat_history import ChatHistory

        chat_history = ChatHistory()

        chat_history.add_user_message("メッセージ1")
        chat_history.add_assistant_message("回答1")
        chat_history.add_user_message("メッセージ2")
        chat_history.add_assistant_message("回答2")

        recent = chat_history.get_recent_messages(2)

        assert len(recent) == 2
        assert recent[0]["content"] == "メッセージ2"
        assert recent[1]["content"] == "回答2"

    def test_get_recent_messages_more_than_available(self) -> None:
        """利用可能数より多い数を指定した場合の動作をテスト"""
        from src.models.chat_history import ChatHistory

        chat_history = ChatHistory()

        chat_history.add_user_message("メッセージ1")

        recent = chat_history.get_recent_messages(10)

        assert len(recent) == 1
        assert recent[0]["content"] == "メッセージ1"

    def test_get_conversation_context(self) -> None:
        """会話コンテキストの取得が正しく動作することをテスト"""
        from src.models.chat_history import ChatHistory

        chat_history = ChatHistory()

        chat_history.add_user_message("質問1")
        chat_history.add_assistant_message("回答1")
        chat_history.add_user_message("質問2")

        context = chat_history.get_conversation_context(max_pairs=1)

        expected = "User: 質問1\nAssistant: 回答1"
        assert context == expected

    def test_clear_history(self) -> None:
        """履歴のクリアが正しく動作することをテスト"""
        from src.models.chat_history import ChatHistory

        chat_history = ChatHistory()

        chat_history.add_user_message("メッセージ1")
        chat_history.add_assistant_message("回答1")

        assert len(chat_history.messages) == 2

        chat_history.clear_history()

        assert len(chat_history.messages) == 0

    def test_to_dict(self) -> None:
        """辞書形式への変換が正しく動作することをテスト"""
        from src.models.chat_history import ChatHistory

        chat_history = ChatHistory(max_messages=100)
        chat_history.add_user_message("テストメッセージ")

        history_dict = chat_history.to_dict()

        assert isinstance(history_dict, dict)
        assert history_dict["max_messages"] == 100
        assert len(history_dict["messages"]) == 1
        assert history_dict["messages"][0]["content"] == "テストメッセージ"
        assert "created_at" in history_dict

    def test_from_dict(self) -> None:
        """辞書からのオブジェクト作成が正しく動作することをテスト"""
        from src.models.chat_history import ChatHistory

        history_data = {
            "max_messages": 75,
            "messages": [
                {"role": "user", "content": "質問", "timestamp": "2024-01-01T12:00:00"},
                {
                    "role": "assistant",
                    "content": "回答",
                    "timestamp": "2024-01-01T12:00:01",
                    "sources": ["doc1.pdf"],
                },
            ],
            "created_at": "2024-01-01T10:00:00",
        }

        chat_history = ChatHistory.from_dict(history_data)

        assert chat_history.max_messages == 75
        assert len(chat_history.messages) == 2
        assert chat_history.messages[0]["content"] == "質問"
        assert chat_history.messages[1]["sources"] == ["doc1.pdf"]

    def test_get_messages_by_role(self) -> None:
        """役割別メッセージ取得が正しく動作することをテスト"""
        from src.models.chat_history import ChatHistory

        chat_history = ChatHistory()

        chat_history.add_user_message("質問1")
        chat_history.add_assistant_message("回答1")
        chat_history.add_user_message("質問2")

        user_messages = chat_history.get_messages_by_role("user")
        assistant_messages = chat_history.get_messages_by_role("assistant")

        assert len(user_messages) == 2
        assert len(assistant_messages) == 1
        assert user_messages[0]["content"] == "質問1"
        assert user_messages[1]["content"] == "質問2"
        assert assistant_messages[0]["content"] == "回答1"

    def test_get_total_message_count(self) -> None:
        """総メッセージ数取得が正しく動作することをテスト"""
        from src.models.chat_history import ChatHistory

        chat_history = ChatHistory()

        assert chat_history.get_total_message_count() == 0

        chat_history.add_user_message("質問")
        assert chat_history.get_total_message_count() == 1

        chat_history.add_assistant_message("回答")
        assert chat_history.get_total_message_count() == 2

    def test_has_messages(self) -> None:
        """メッセージ存在チェックが正しく動作することをテスト"""
        from src.models.chat_history import ChatHistory

        chat_history = ChatHistory()

        assert chat_history.has_messages() is False

        chat_history.add_user_message("質問")

        assert chat_history.has_messages() is True
