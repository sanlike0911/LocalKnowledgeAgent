"""
日本語回答制御機能のテストケース
ISSUE-016: 日本語固定回答制御の実装 - テスト実装
"""

import pytest
from unittest.mock import Mock, patch
from src.logic.qa import RAGPipeline, QAService, QAResult
from src.logic.indexing import ChromaDBIndexer
from src.exceptions.base_exceptions import QAError


class TestJapaneseResponseControl:
    """日本語回答制御機能のテストクラス"""
    
    @pytest.fixture
    def mock_indexer(self):
        """モックインデクサーを作成"""
        indexer = Mock(spec=ChromaDBIndexer)
        indexer.search_documents.return_value = [
            {
                'content': 'テストドキュメントの内容です。',
                'metadata': {'filename': 'test.pdf', 'chunk_index': 0},
                'distance': 0.2
            }
        ]
        return indexer
    
    @pytest.fixture
    def rag_pipeline(self, mock_indexer):
        """RAGパイプラインを初期化"""
        with patch('src.logic.qa.OllamaQAEngine'):
            pipeline = RAGPipeline(
                indexer=mock_indexer,
                model_name="llama3.1:8b"
            )
            return pipeline
    
    @pytest.fixture
    def qa_service(self, mock_indexer):
        """QAサービスを初期化"""
        with patch('src.logic.qa.OllamaQAEngine'):
            service = QAService(
                indexer=mock_indexer,
                model_name="llama3.1:8b"
            )
            return service
    
    def test_japanese_prompt_template_contains_japanese_instruction(self, rag_pipeline):
        """日本語固定プロンプトテンプレートが日本語指示を含むことを確認"""
        # プロンプトテンプレートに日本語指示が含まれていることを確認
        assert "日本語で回答してください" in rag_pipeline.qa_prompt_template
        
        # テストクエリでプロンプト生成
        test_query = "How are you?"
        test_context = "Test context information"
        
        prompt = rag_pipeline._create_qa_prompt(test_query, test_context)
        
        # 生成されたプロンプトに日本語指示が含まれていることを確認
        assert "日本語で回答してください" in prompt
        assert test_query in prompt
        assert test_context in prompt
    
    def test_direct_prompt_template_contains_japanese_instruction(self, rag_pipeline):
        """直接QAプロンプトテンプレートが日本語指示を含むことを確認"""
        test_query = "What is AI?"
        
        prompt = rag_pipeline._create_direct_qa_prompt(test_query)
        
        # 生成されたプロンプトに日本語指示が含まれていることを確認
        assert "日本語で回答してください" in prompt
        assert test_query in prompt
    
    def test_qa_result_has_japanese_response_language(self):
        """QAResultが日本語レスポンス言語を持つことを確認"""
        result = QAResult(
            query="テスト質問",
            answer="テスト回答",
            sources=[],
            context="テストコンテキスト"
        )
        
        # response_languageが日本語固定であることを確認
        assert result.response_language == "ja"
        
        # to_dict()でも正しく含まれることを確認
        result_dict = result.to_dict()
        assert result_dict['response_language'] == "ja"
    
    def test_answer_question_returns_japanese_language(self, rag_pipeline):
        """answer_questionが日本語言語情報を返すことを確認"""
        # 既存のモックエンジンにレスポンスを設定
        rag_pipeline.qa_engine.generate_response.return_value = Mock(
            content="これは日本語の回答です。",
            metadata={'model': 'llama3.1:8b'}
        )
        
        # 質問実行
        result = rag_pipeline.answer_question("What is Python?")
        
        # レスポンス言語が日本語であることを確認
        assert result['response_language'] == "ja"
        assert result['answer'] == "これは日本語の回答です。"
    
    def test_multiple_query_types_all_return_japanese(self, rag_pipeline):
        """様々な質問タイプで全て日本語設定が返されることを確認"""
        with patch.object(rag_pipeline.qa_engine, 'generate_response') as mock_generate:
            mock_generate.return_value = Mock(
                content="日本語の回答",
                metadata={'model': 'llama3.1:8b'}
            )
            
            test_queries = [
                "Hello, how are you?",  # 英語質問
                "こんにちは、元気ですか？",  # 日本語質問
                "¿Cómo estás?",  # スペイン語質問
                "Wie geht es dir?",  # ドイツ語質問
                "Comment allez-vous?"  # フランス語質問
            ]
            
            for query in test_queries:
                result = rag_pipeline.answer_question(query)
                
                # 全ての質問に対して日本語言語設定を確認
                assert result['response_language'] == "ja", f"Failed for query: {query}"
    
    def test_qa_service_maintains_japanese_response_language(self, qa_service):
        """QAServiceでも日本語レスポンス言語が維持されることを確認"""
        # 既存のモックエンジンにレスポンスを設定
        qa_service.rag_pipeline.qa_engine.generate_response.return_value = Mock(
            content="QAServiceからの日本語回答です。",
            metadata={'model': 'llama3.1:8b'}
        )
        
        # QAServiceを通じて質問実行
        result = qa_service.ask_question("Test question in English")
        
        # レスポンス言語が日本語であることを確認
        assert result['response_language'] == "ja"
        assert result['answer'] == "QAServiceからの日本語回答です。"
    
    def test_direct_qa_mode_also_uses_japanese(self, rag_pipeline):
        """直接QAモード（ドキュメント0件）でも日本語が使用されることを確認"""
        # ドキュメント検索で「関連する文書が見つかりません」エラーを発生させてフォールバックモードをテスト
        from src.exceptions.base_exceptions import QAError
        rag_pipeline.indexer.search_documents.side_effect = QAError(
            "関連する文書が見つかりません", 
            error_code="QA-001"
        )
        
        # モックレスポンスを設定
        rag_pipeline.qa_engine.generate_response.return_value = Mock(
            content="ドキュメントがない場合の日本語回答です。",
            metadata={'model': 'llama3.1:8b'}
        )
        
        # 直接QAモードで質問実行
        result = rag_pipeline.answer_question("What is machine learning?")
        
        # 直接QAモードでも日本語言語設定を確認
        assert result['response_language'] == "ja"
        assert result['answer'] == "ドキュメントがない場合の日本語回答です。"
    
    def test_japanese_instruction_appears_at_prompt_beginning(self, rag_pipeline):
        """日本語指示がプロンプトの先頭に配置されることを確認"""
        test_query = "Explain quantum computing"
        test_context = "Context about quantum computing"
        
        # 通常のQAプロンプト
        qa_prompt = rag_pipeline._create_qa_prompt(test_query, test_context)
        assert qa_prompt.startswith("IMPORTANT: You MUST respond in Japanese only.")
        
        # 直接QAプロンプト
        direct_prompt = rag_pipeline._create_direct_qa_prompt(test_query)
        assert direct_prompt.startswith("IMPORTANT: You MUST respond in Japanese only.")
    
    def test_conversation_history_with_japanese_instruction(self, rag_pipeline):
        """会話履歴がある場合でも日本語指示が維持されることを確認"""
        conversation_history = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"}
        ]
        
        test_query = "Follow-up question"
        test_context = "Test context"
        
        prompt = rag_pipeline._create_qa_prompt(test_query, test_context, conversation_history)
        
        # 日本語指示が含まれていることを確認
        assert "日本語で回答してください。" in prompt
        # 会話履歴も含まれていることを確認
        assert "Previous question" in prompt
        assert "Previous answer" in prompt


class TestJapaneseResponseIntegration:
    """日本語回答制御の統合テスト"""
    
    @pytest.fixture
    def integration_qa_service(self):
        """統合テスト用QAサービス（実際のコンポーネントを使用）"""
        # 実際のChromaDBIndexerをモック
        with patch('src.logic.indexing.ChromaDBIndexer') as mock_indexer_class:
            mock_indexer = mock_indexer_class.return_value
            mock_indexer.search_documents.return_value = []
            
            # 実際のQAServiceを作成（OllamaQAEngineはモック）
            with patch('src.logic.qa.OllamaQAEngine') as mock_engine_class:
                mock_engine = mock_engine_class.return_value
                mock_engine.generate_response.return_value = Mock(
                    content="統合テストでの日本語回答",
                    metadata={'model': 'llama3.1:8b'}
                )
                
                return QAService(indexer=mock_indexer)
    
    def test_end_to_end_japanese_response(self, integration_qa_service):
        """エンドツーエンドで日本語回答が生成されることを確認"""
        # 様々なタイプの質問をテスト
        test_cases = [
            ("Hello", "英語の挨拶"),
            ("What is Python?", "プログラミング言語に関する英語質問"),
            ("こんにちは", "日本語の挨拶"),
            ("Pythonとは何ですか？", "プログラミング言語に関する日本語質問"),
            ("机器学习是什么？", "中国語の質問"),
        ]
        
        for query, description in test_cases:
            result = integration_qa_service.ask_question(query)
            
            # 全ての質問に対して日本語応答設定を確認
            assert result['response_language'] == "ja", f"Failed for {description}: {query}"
            
            # 回答が取得されていることを確認
            assert result['answer'] == "統合テストでの日本語回答"
    
    def test_system_consistency_across_components(self, integration_qa_service):
        """システム全体で日本語設定の一貫性を確認"""
        query = "Test system consistency"
        
        # QAService経由で質問
        service_result = integration_qa_service.ask_question(query)
        
        # 結果の一貫性を確認
        assert service_result['response_language'] == "ja"
        assert 'query' in service_result
        assert 'answer' in service_result
        assert 'sources' in service_result
        assert 'processing_time' in service_result
        
        # 日本語レスポンス言語が辞書に正しく含まれていることを確認
        required_fields = ['query', 'answer', 'sources', 'context', 'processing_time', 'response_language']
        for field in required_fields:
            assert field in service_result, f"Missing field: {field}"