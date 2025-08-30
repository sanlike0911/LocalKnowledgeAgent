"""
QAInterfaceのテストケース (TDD Red フェーズ)
CLAUDE.md準拠のTDD実装手順に従う
"""

import pytest
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, AsyncMock


class TestQAInterface:
    """QAInterfaceのテストクラス"""
    
    def test_qa_interface_generate_answer(self) -> None:
        """回答生成機能のテストケース"""
        from src.interfaces.qa_interface import QAInterface
        from src.interfaces.indexing_interface import IndexingInterface
        from src.models.config import Config
        from src.models.chat_history import ChatHistory
        
        # テスト用設定
        config = Config()
        indexing_interface = Mock(spec=IndexingInterface)
        chat_history = ChatHistory()
        
        # モックの設定
        indexing_interface.search_documents.return_value = [
            {
                "document": Mock(
                    id="doc1",
                    title="テスト文書",
                    content="これはテスト用の回答に使われる文書です。"
                ),
                "similarity_score": 0.85
            }
        ]
        
        qa_interface = QAInterface(config, indexing_interface)
        
        # 質問に対する回答生成
        result = qa_interface.generate_answer(
            question="テストについて教えてください",
            chat_history=chat_history
        )
        
        # 結果の検証
        assert isinstance(result, dict)
        assert "answer" in result
        assert "sources" in result
        assert "confidence_score" in result
        assert isinstance(result["sources"], list)
        assert len(result["sources"]) > 0
    
    def test_qa_interface_generate_answer_with_context(self) -> None:
        """コンテキスト付き回答生成のテストケース"""
        from src.interfaces.qa_interface import QAInterface
        from src.interfaces.indexing_interface import IndexingInterface
        from src.models.config import Config
        from src.models.chat_history import ChatHistory
        
        config = Config()
        indexing_interface = Mock(spec=IndexingInterface)
        
        # チャット履歴を作成
        chat_history = ChatHistory()
        chat_history.add_user_message("Pythonについて教えてください")
        chat_history.add_assistant_message("Pythonは素晴らしいプログラミング言語です。")
        
        # モック設定
        indexing_interface.search_documents.return_value = [
            {
                "document": Mock(
                    id="doc1",
                    title="Python入門",
                    content="Pythonは初心者にも優しいプログラミング言語です。"
                ),
                "similarity_score": 0.9
            }
        ]
        
        qa_interface = QAInterface(config, indexing_interface)
        
        # コンテキストを考慮した回答生成
        result = qa_interface.generate_answer(
            question="具体的な特徴は何ですか？",
            chat_history=chat_history,
            use_context=True
        )
        
        assert isinstance(result, dict)
        assert "answer" in result
        assert "context_used" in result
        assert result["context_used"] is True
    
    def test_qa_interface_search_relevant_documents(self) -> None:
        """関連文書検索機能のテストケース"""
        from src.interfaces.qa_interface import QAInterface
        from src.interfaces.indexing_interface import IndexingInterface
        from src.models.config import Config
        
        config = Config()
        indexing_interface = Mock(spec=IndexingInterface)
        
        # モック設定
        mock_documents = [
            {
                "document": Mock(
                    id=f"doc{i}",
                    title=f"文書{i}",
                    content=f"これは文書{i}の内容です。"
                ),
                "similarity_score": 0.8 - (i * 0.1)
            }
            for i in range(3)
        ]
        indexing_interface.search_documents.return_value = mock_documents
        
        qa_interface = QAInterface(config, indexing_interface)
        
        # 関連文書検索
        results = qa_interface.search_relevant_documents(
            question="テスト質問",
            top_k=3,
            min_similarity=0.5
        )
        
        assert isinstance(results, list)
        assert len(results) == 3
        assert all("document" in result for result in results)
        assert all("similarity_score" in result for result in results)
    
    def test_qa_interface_validate_question(self) -> None:
        """質問検証機能のテストケース"""
        from src.interfaces.qa_interface import QAInterface
        from src.interfaces.indexing_interface import IndexingInterface
        from src.models.config import Config
        
        config = Config()
        indexing_interface = Mock(spec=IndexingInterface)
        qa_interface = QAInterface(config, indexing_interface)
        
        # 有効な質問
        valid_result = qa_interface.validate_question("これは有効な質問です")
        assert valid_result["is_valid"] is True
        assert len(valid_result["errors"]) == 0
        
        # 無効な質問（空文字）
        invalid_result = qa_interface.validate_question("")
        assert invalid_result["is_valid"] is False
        assert len(invalid_result["errors"]) > 0
        
        # 無効な質問（短すぎる）
        short_result = qa_interface.validate_question("短い")
        assert short_result["is_valid"] is False
    
    def test_qa_interface_generate_answer_streaming(self) -> None:
        """ストリーミング回答生成のテストケース"""
        from src.interfaces.qa_interface import QAInterface
        from src.interfaces.indexing_interface import IndexingInterface
        from src.models.config import Config
        from src.models.chat_history import ChatHistory
        
        config = Config()
        indexing_interface = Mock(spec=IndexingInterface)
        chat_history = ChatHistory()
        
        # モック設定
        indexing_interface.search_documents.return_value = [
            {
                "document": Mock(
                    id="doc1",
                    title="ストリーミングテスト",
                    content="これはストリーミング回答のテスト文書です。"
                ),
                "similarity_score": 0.9
            }
        ]
        
        qa_interface = QAInterface(config, indexing_interface)
        
        # ストリーミング回答生成
        chunks = list(qa_interface.generate_answer_stream(
            question="ストリーミングについて教えてください",
            chat_history=chat_history
        ))
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, dict) for chunk in chunks)
        assert all("chunk" in chunk for chunk in chunks)
        
        # 最後のチャンクには完了フラグがある
        assert chunks[-1].get("is_final", False) is True
    
    def test_qa_interface_get_answer_confidence(self) -> None:
        """回答信頼度計算のテストケース"""
        from src.interfaces.qa_interface import QAInterface
        from src.interfaces.indexing_interface import IndexingInterface
        from src.models.config import Config
        
        config = Config()
        indexing_interface = Mock(spec=IndexingInterface)
        qa_interface = QAInterface(config, indexing_interface)
        
        # 高い類似度のソース
        high_similarity_sources = [
            {"document": Mock(), "similarity_score": 0.9},
            {"document": Mock(), "similarity_score": 0.85}
        ]
        
        confidence = qa_interface.calculate_confidence_score(
            sources=high_similarity_sources,
            answer_length=200
        )
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.7  # 高い信頼度
        
        # 低い類似度のソース
        low_similarity_sources = [
            {"document": Mock(), "similarity_score": 0.3},
            {"document": Mock(), "similarity_score": 0.2}
        ]
        
        low_confidence = qa_interface.calculate_confidence_score(
            sources=low_similarity_sources,
            answer_length=50
        )
        
        assert low_confidence < confidence  # より低い信頼度
    
    def test_qa_interface_format_sources(self) -> None:
        """ソース情報フォーマット機能のテストケース"""
        from src.interfaces.qa_interface import QAInterface
        from src.interfaces.indexing_interface import IndexingInterface
        from src.models.config import Config
        
        config = Config()
        indexing_interface = Mock(spec=IndexingInterface)
        qa_interface = QAInterface(config, indexing_interface)
        
        # テスト用ソース
        sources = [
            {
                "document": Mock(
                    id="doc1",
                    title="ソース文書1",
                    file_path="/path/to/source1.pdf"
                ),
                "similarity_score": 0.9
            },
            {
                "document": Mock(
                    id="doc2",
                    title="ソース文書2", 
                    file_path="/path/to/source2.txt"
                ),
                "similarity_score": 0.8
            }
        ]
        
        formatted_sources = qa_interface.format_sources(sources)
        
        assert isinstance(formatted_sources, list)
        assert len(formatted_sources) == 2
        assert all("title" in source for source in formatted_sources)
        assert all("file_path" in source for source in formatted_sources)
        assert all("similarity_score" in source for source in formatted_sources)
    
    async def test_qa_interface_generate_answer_async(self) -> None:
        """非同期回答生成のテストケース"""
        from src.interfaces.qa_interface import QAInterface
        from src.interfaces.indexing_interface import IndexingInterface
        from src.models.config import Config
        from src.models.chat_history import ChatHistory
        
        config = Config()
        indexing_interface = Mock(spec=IndexingInterface)
        chat_history = ChatHistory()
        
        # 非同期モック設定
        async_mock = AsyncMock()
        async_mock.return_value = [
            {
                "document": Mock(
                    id="async_doc",
                    title="非同期文書",
                    content="これは非同期処理の文書です。"
                ),
                "similarity_score": 0.85
            }
        ]
        indexing_interface.search_documents = async_mock
        
        qa_interface = QAInterface(config, indexing_interface)
        
        # 非同期回答生成
        result = await qa_interface.generate_answer_async(
            question="非同期処理について教えてください",
            chat_history=chat_history
        )
        
        assert isinstance(result, dict)
        assert "answer" in result
        assert "sources" in result
    
    def test_qa_interface_error_handling(self) -> None:
        """エラーハンドリングのテストケース"""
        from src.interfaces.qa_interface import QAInterface, QAError
        from src.interfaces.indexing_interface import IndexingInterface
        from src.models.config import Config
        from src.models.chat_history import ChatHistory
        
        config = Config()
        indexing_interface = Mock(spec=IndexingInterface)
        chat_history = ChatHistory()
        
        # インデックス検索でエラーが発生する設定
        indexing_interface.search_documents.side_effect = Exception("検索エラー")
        
        qa_interface = QAInterface(config, indexing_interface)
        
        # エラー処理の確認
        with pytest.raises(QAError, match="回答生成に失敗しました"):
            qa_interface.generate_answer(
                question="エラーテスト",
                chat_history=chat_history
            )
    
    def test_qa_interface_question_preprocessing(self) -> None:
        """質問前処理機能のテストケース"""
        from src.interfaces.qa_interface import QAInterface
        from src.interfaces.indexing_interface import IndexingInterface
        from src.models.config import Config
        
        config = Config()
        indexing_interface = Mock(spec=IndexingInterface)
        qa_interface = QAInterface(config, indexing_interface)
        
        # 質問の前処理
        raw_question = "  これは　　テスト　質問です。！？  "
        processed = qa_interface.preprocess_question(raw_question)
        
        assert isinstance(processed, str)
        assert processed.strip() == processed  # 前後の空白が削除されている
        assert "　　" not in processed  # 全角スペースが処理されている
    
    def test_qa_interface_answer_postprocessing(self) -> None:
        """回答後処理機能のテストケース"""
        from src.interfaces.qa_interface import QAInterface
        from src.interfaces.indexing_interface import IndexingInterface
        from src.models.config import Config
        
        config = Config()
        indexing_interface = Mock(spec=IndexingInterface)
        qa_interface = QAInterface(config, indexing_interface)
        
        # 生の回答
        raw_answer = "これは生成された回答です。\n\n参考文献については後述します。"
        sources = [{"title": "参考文書", "file_path": "/path/to/ref.pdf"}]
        
        processed = qa_interface.postprocess_answer(raw_answer, sources)
        
        assert isinstance(processed, dict)
        assert "answer" in processed
        assert "formatted_sources" in processed
        assert "metadata" in processed
    
    def test_qa_interface_performance_metrics(self) -> None:
        """パフォーマンス測定のテストケース"""
        from src.interfaces.qa_interface import QAInterface
        from src.interfaces.indexing_interface import IndexingInterface
        from src.models.config import Config
        from src.models.chat_history import ChatHistory
        
        config = Config()
        indexing_interface = Mock(spec=IndexingInterface)
        chat_history = ChatHistory()
        
        # モック設定
        indexing_interface.search_documents.return_value = [
            {
                "document": Mock(
                    id="perf_doc",
                    title="パフォーマンステスト",
                    content="パフォーマンス測定用の文書です。"
                ),
                "similarity_score": 0.8
            }
        ]
        
        qa_interface = QAInterface(config, indexing_interface)
        
        # パフォーマンス測定付きで回答生成
        result = qa_interface.generate_answer_with_metrics(
            question="パフォーマンスについて教えてください",
            chat_history=chat_history
        )
        
        assert isinstance(result, dict)
        assert "answer" in result
        assert "performance_metrics" in result
        assert "processing_time" in result["performance_metrics"]
        assert "search_time" in result["performance_metrics"]
        assert "generation_time" in result["performance_metrics"]