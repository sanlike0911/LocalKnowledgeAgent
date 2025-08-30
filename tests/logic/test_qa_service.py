"""
QAService TDDテスト (Red フェーズ)
アプリケーションレイヤーのQAService実装テスト
"""

import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch, call
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.logic.qa import QAService, RAGPipeline
from src.logic.indexing import ChromaDBIndexer
from src.exceptions.base_exceptions import QAError


class TestQAService(unittest.TestCase):
    """QAServiceのユニットテスト"""

    def setUp(self):
        """テストのセットアップ"""
        self.mock_indexer = MagicMock(spec=ChromaDBIndexer)
        self.mock_rag_pipeline = MagicMock(spec=RAGPipeline)

    @patch('src.logic.qa.RAGPipeline')
    def test_qa_service_initialization(self, mock_rag_class):
        """QAService初期化テスト"""
        mock_rag_class.return_value = self.mock_rag_pipeline
        
        qa_service = QAService(
            indexer=self.mock_indexer,
            model_name="llama3.1:8b",
            max_context_length=4000
        )
        
        # RAGPipeline が正しいパラメータで初期化される
        mock_rag_class.assert_called_once_with(
            indexer=self.mock_indexer,
            model_name="llama3.1:8b",
            max_context_length=4000
        )
        
        # 必要な属性が設定される
        self.assertEqual(qa_service.model_name, "llama3.1:8b")
        self.assertEqual(qa_service.max_context_length, 4000)
        self.assertIsNotNone(qa_service.logger)

    @patch('src.logic.qa.RAGPipeline')
    def test_ask_question_success(self, mock_rag_class):
        """質問応答成功テスト"""
        mock_rag_class.return_value = self.mock_rag_pipeline
        
        # RAGPipelineの戻り値を設定
        expected_answer = {
            'query': 'テストクエリ',
            'answer': 'テスト回答',
            'sources': [{'filename': 'test.txt', 'distance': 0.1}],
            'context': 'テストコンテキスト',
            'processing_time': 1.5
        }
        self.mock_rag_pipeline.answer_question.return_value = expected_answer
        
        qa_service = QAService(self.mock_indexer)
        
        result = qa_service.ask_question(
            query="テストクエリ",
            conversation_history=[{"role": "user", "content": "前の質問"}],
            top_k=3
        )
        
        # RAGPipelineが正しいパラメータで呼ばれる
        self.mock_rag_pipeline.answer_question.assert_called_once_with(
            query="テストクエリ",
            conversation_history=[{"role": "user", "content": "前の質問"}],
            top_k=3,
            min_similarity_threshold=0.0
        )
        
        # 期待した結果が返される
        self.assertEqual(result, expected_answer)

    @patch('src.logic.qa.RAGPipeline')
    def test_ask_question_with_custom_similarity_threshold(self, mock_rag_class):
        """カスタム類似度閾値テスト"""
        mock_rag_class.return_value = self.mock_rag_pipeline
        self.mock_rag_pipeline.answer_question.return_value = {"answer": "test"}
        
        qa_service = QAService(self.mock_indexer)
        
        qa_service.ask_question(
            query="テスト",
            min_similarity_threshold=0.7
        )
        
        self.mock_rag_pipeline.answer_question.assert_called_once_with(
            query="テスト",
            conversation_history=None,
            top_k=5,
            min_similarity_threshold=0.7
        )

    @patch('src.logic.qa.RAGPipeline')
    def test_ask_question_error_handling(self, mock_rag_class):
        """質問応答エラーハンドリングテスト"""
        mock_rag_class.return_value = self.mock_rag_pipeline
        
        # RAGPipelineでエラーが発生
        self.mock_rag_pipeline.answer_question.side_effect = QAError(
            "テストエラー",
            error_code="QA-TEST"
        )
        
        qa_service = QAService(self.mock_indexer)
        
        # QAErrorがそのまま再発生することを確認
        with self.assertRaises(QAError) as context:
            qa_service.ask_question("テストクエリ")
        
        self.assertEqual(context.exception.error_code, "QA-TEST")

    @patch('src.logic.qa.RAGPipeline')
    def test_ask_question_stream_success(self, mock_rag_class):
        """ストリーミング質問応答成功テスト"""
        mock_rag_class.return_value = self.mock_rag_pipeline
        
        # ストリーミングレスポンスを設定
        mock_stream_responses = [
            {'type': 'sources', 'sources': ['test.txt']},
            {'type': 'content', 'content': 'テスト', 'done': False},
            {'type': 'content', 'content': '回答', 'done': True},
            {'type': 'complete', 'answer': 'テスト回答'}
        ]
        self.mock_rag_pipeline.answer_question_stream.return_value = iter(mock_stream_responses)
        
        qa_service = QAService(self.mock_indexer)
        
        # ストリーミング結果を取得
        results = list(qa_service.ask_question_stream(
            query="テストクエリ",
            conversation_history=[],
            top_k=3
        ))
        
        # RAGPipelineが正しいパラメータで呼ばれる
        self.mock_rag_pipeline.answer_question_stream.assert_called_once_with(
            query="テストクエリ",
            conversation_history=[],
            top_k=3
        )
        
        # 期待した結果が返される
        self.assertEqual(results, mock_stream_responses)

    @patch('src.logic.qa.RAGPipeline')
    def test_ask_question_stream_error_handling(self, mock_rag_class):
        """ストリーミング質問応答エラーハンドリングテスト"""
        mock_rag_class.return_value = self.mock_rag_pipeline
        
        # ストリーミングでエラーが発生
        def error_stream():
            yield {'type': 'sources', 'sources': []}
            raise QAError("ストリームエラー", error_code="QA-STREAM")
        
        self.mock_rag_pipeline.answer_question_stream.return_value = error_stream()
        
        qa_service = QAService(self.mock_indexer)
        
        # エラーが適切にハンドリングされることを確認
        stream_generator = qa_service.ask_question_stream("テスト")
        
        # 最初の結果は正常に取得できる
        first_result = next(stream_generator)
        self.assertEqual(first_result['type'], 'sources')
        
        # 2番目でエラーが発生する
        with self.assertRaises(QAError) as context:
            next(stream_generator)
        
        self.assertEqual(context.exception.error_code, "QA-STREAM")

    @patch('src.logic.qa.RAGPipeline')
    def test_check_system_health(self, mock_rag_class):
        """システム健康状態チェックテスト"""
        mock_rag_class.return_value = self.mock_rag_pipeline
        
        expected_health = {
            'overall_status': 'healthy',
            'components': {
                'chromadb': {'status': 'healthy'},
                'ollama': {'status': 'healthy'}
            }
        }
        self.mock_rag_pipeline.check_system_health.return_value = expected_health
        
        qa_service = QAService(self.mock_indexer)
        result = qa_service.check_system_health()
        
        self.mock_rag_pipeline.check_system_health.assert_called_once()
        self.assertEqual(result, expected_health)

    @patch('src.logic.qa.RAGPipeline')
    def test_search_documents(self, mock_rag_class):
        """文書検索テスト"""
        mock_rag_class.return_value = self.mock_rag_pipeline
        
        expected_results = [
            {
                'content': 'テスト文書内容',
                'metadata': {'filename': 'test.txt'},
                'distance': 0.1
            }
        ]
        self.mock_rag_pipeline.search_relevant_documents.return_value = expected_results
        
        qa_service = QAService(self.mock_indexer)
        results = qa_service.search_documents(
            query="テスト検索",
            top_k=10,
            min_similarity_threshold=0.3
        )
        
        self.mock_rag_pipeline.search_relevant_documents.assert_called_once_with(
            query="テスト検索",
            top_k=10,
            min_similarity_threshold=0.3
        )
        self.assertEqual(results, expected_results)

    @patch('src.logic.qa.RAGPipeline')
    def test_cancel_operation(self, mock_rag_class):
        """操作キャンセルテスト"""
        mock_rag_class.return_value = self.mock_rag_pipeline
        
        qa_service = QAService(self.mock_indexer)
        qa_service.cancel()
        
        # RAGPipelineのキャンセルメソッドが呼ばれる
        self.mock_rag_pipeline.cancel.assert_called_once()

    @patch('src.logic.qa.RAGPipeline') 
    def test_default_parameters(self, mock_rag_class):
        """デフォルトパラメータテスト"""
        mock_rag_class.return_value = self.mock_rag_pipeline
        
        # デフォルトパラメータで初期化
        qa_service = QAService(self.mock_indexer)
        
        mock_rag_class.assert_called_once_with(
            indexer=self.mock_indexer,
            model_name="llama3.1:8b",
            max_context_length=4000
        )
        
        self.assertEqual(qa_service.model_name, "llama3.1:8b")
        self.assertEqual(qa_service.max_context_length, 4000)

    @patch('src.logic.qa.RAGPipeline')
    def test_logging_integration(self, mock_rag_class):
        """ログ統合テスト"""
        mock_rag_class.return_value = self.mock_rag_pipeline
        
        qa_service = QAService(self.mock_indexer)
        
        # ロガーが適切に設定されている
        self.assertIsNotNone(qa_service.logger)
        self.assertEqual(qa_service.logger.name, "src.logic.qa")

    @patch('src.logic.qa.RAGPipeline')
    def test_service_layer_abstraction(self, mock_rag_class):
        """サービス層抽象化テスト"""
        mock_rag_class.return_value = self.mock_rag_pipeline
        
        qa_service = QAService(self.mock_indexer)
        
        # QAServiceがRAGPipelineの適切なラッパーとして動作する
        self.assertIsInstance(qa_service.rag_pipeline, MagicMock)
        self.assertEqual(qa_service.rag_pipeline, self.mock_rag_pipeline)


if __name__ == '__main__':
    unittest.main()