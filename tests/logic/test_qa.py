"""
LangChain QAシステムのテストスイート (TDD Red フェーズ)
文書検索・回答生成・Ollama統合機能のテストを定義
"""

import pytest
from pathlib import Path
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import shutil
from dataclasses import dataclass

from src.models.document import Document
from src.exceptions.base_exceptions import QAError
from src.logic.qa import RAGPipeline, OllamaQAEngine
from src.logic.indexing import ChromaDBIndexer


@dataclass
class MockLLMResponse:
    """LLMレスポンスのモッククラス"""
    content: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TestRAGPipeline:
    """RAGパイプライン機能のテストスイート"""
    
    def setup_method(self):
        """各テスト前の初期化処理"""
        self.test_db_path = Path("./test_rag_db")
        self.mock_indexer = Mock(spec=ChromaDBIndexer)
        self.rag_pipeline = RAGPipeline(
            indexer=self.mock_indexer,
            model_name="llama3.1:8b"
        )
    
    def teardown_method(self):
        """各テスト後のクリーンアップ処理"""
        if self.test_db_path.exists():
            shutil.rmtree(self.test_db_path)
    
    # RAG パイプライン基本機能テスト
    
    def test_search_relevant_documents(self):
        """関連文書検索テスト (Red フェーズ)"""
        query = "Pythonのリスト操作について教えて"
        
        # モック検索結果を設定
        mock_search_results = [
            {
                'content': 'Pythonのリストは可変なシーケンス型です。append()やextend()などのメソッドが使用できます。',
                'metadata': {'filename': 'python_basics.txt', 'chunk_index': 0},
                'distance': 0.1
            },
            {
                'content': 'リスト内包表記を使うことで、効率的にリストを生成できます。[x for x in range(10)]のように記述します。',
                'metadata': {'filename': 'python_advanced.txt', 'chunk_index': 3},
                'distance': 0.2
            },
            {
                'content': 'sort()メソッドでリストをソートできます。reverse=Trueで降順ソートも可能です。',
                'metadata': {'filename': 'python_methods.txt', 'chunk_index': 1},
                'distance': 0.15
            }
        ]
        
        self.mock_indexer.search_documents.return_value = mock_search_results
        
        # 検索実行
        results = self.rag_pipeline.search_relevant_documents(query, top_k=3)
        
        # 検証
        assert len(results) == 3
        assert results[0]['content'].startswith('Pythonのリストは可変な')
        assert results[0]['metadata']['filename'] == 'python_basics.txt'
        assert results[0]['distance'] == 0.1
        
        # インデクサーが正しく呼ばれたことを確認
        self.mock_indexer.search_documents.assert_called_once_with(query, top_k=3)
    
    def test_search_no_results(self):
        """検索結果なしテスト (Red フェーズ)"""
        query = "存在しない内容についての質問"
        
        # 空の検索結果を設定
        self.mock_indexer.search_documents.return_value = []
        
        # QAError が発生することを期待
        with pytest.raises(QAError) as exc_info:
            self.rag_pipeline.search_relevant_documents(query)
        
        assert exc_info.value.error_code == "QA-001"
        assert "関連する文書が見つかりません" in str(exc_info.value)
    
    def test_search_indexer_error(self):
        """インデクサーエラーハンドリングテスト (Red フェーズ)"""
        query = "テスト質問"
        
        # インデクサーでエラーが発生する場合
        self.mock_indexer.search_documents.side_effect = Exception("ChromaDB connection error")
        
        with pytest.raises(QAError) as exc_info:
            self.rag_pipeline.search_relevant_documents(query)
        
        assert exc_info.value.error_code == "QA-002"
        assert "文書検索エラー" in str(exc_info.value)
    
    def test_generate_context_from_documents(self):
        """文書からコンテキスト生成テスト (Red フェーズ)"""
        search_results = [
            {
                'content': 'Python は高レベルプログラミング言語です。',
                'metadata': {'filename': 'intro.txt'},
                'distance': 0.1
            },
            {
                'content': '動的型付けとガベージコレクションを特徴とします。',
                'metadata': {'filename': 'features.txt'},  
                'distance': 0.15
            }
        ]
        
        context = self.rag_pipeline._generate_context_from_documents(search_results)
        
        # コンテキストが正しく生成されることを確認
        assert "Python は高レベルプログラミング言語です。" in context
        assert "動的型付けとガベージコレクションを特徴とします。" in context
        assert "[出典: intro.txt]" in context
        assert "[出典: features.txt]" in context
    
    def test_create_qa_prompt(self):
        """QAプロンプト作成テスト (Red フェーズ)"""
        query = "Pythonの特徴は何ですか？"
        context = """
        Python は高レベルプログラミング言語です。[出典: intro.txt]
        動的型付けとガベージコレクションを特徴とします。[出典: features.txt]
        """
        
        prompt = self.rag_pipeline._create_qa_prompt(query, context)
        
        # プロンプトの構成要素が含まれることを確認
        assert query in prompt
        assert context.strip() in prompt
        assert "以下のコンテキスト情報を参考に" in prompt
        assert "日本語で回答してください" in prompt
        assert "参考にした情報源も明記してください" in prompt
    
    def test_answer_question_success(self):
        """質問応答成功テスト (Red フェーズ)"""
        query = "Pythonの主な特徴を教えて"
        
        # モック検索結果を設定
        mock_search_results = [
            {
                'content': 'Pythonは高レベルプログラミング言語で、シンプルで読みやすい構文が特徴です。',
                'metadata': {'filename': 'python_intro.txt'},
                'distance': 0.1
            }
        ]
        self.mock_indexer.search_documents.return_value = mock_search_results
        
        # モックLLM応答を設定
        mock_llm_response = MockLLMResponse(
            content="Pythonの主な特徴は以下の通りです：\n1. シンプルで読みやすい構文\n2. 高レベルプログラミング言語\n\n[参考: python_intro.txt]"
        )
        
        with patch.object(self.rag_pipeline, '_call_llm') as mock_llm_call:
            mock_llm_call.return_value = mock_llm_response
            
            result = self.rag_pipeline.answer_question(query)
            
            # 応答結果の検証
            assert result is not None
            assert result['answer'] == mock_llm_response.content
            assert result['query'] == query
            assert 'sources' in result
            assert len(result['sources']) == 1
            assert result['sources'][0]['filename'] == 'python_intro.txt'
            assert 'context' in result
    
    def test_answer_question_llm_error(self):
        """LLM応答エラーテスト (Red フェーズ)"""
        query = "テスト質問"
        
        # 検索は成功するが、LLMでエラーが発生
        self.mock_indexer.search_documents.return_value = [
            {'content': 'テスト内容', 'metadata': {'filename': 'test.txt'}, 'distance': 0.1}
        ]
        
        with patch.object(self.rag_pipeline, '_call_llm') as mock_llm_call:
            mock_llm_call.side_effect = Exception("LLM API error")
            
            with pytest.raises(QAError) as exc_info:
                self.rag_pipeline.answer_question(query)
            
            assert exc_info.value.error_code == "QA-003"
            assert "回答生成エラー" in str(exc_info.value)
    
    def test_answer_question_with_history(self):
        """履歴付き質問応答テスト (Red フェーズ)"""
        query = "さらに詳しく教えて"
        conversation_history = [
            {"role": "user", "content": "Pythonとは何ですか？"},
            {"role": "assistant", "content": "Pythonは高レベルプログラミング言語です。"}
        ]
        
        # モック設定
        self.mock_indexer.search_documents.return_value = [
            {'content': 'Python詳細情報', 'metadata': {'filename': 'details.txt'}, 'distance': 0.1}
        ]
        
        mock_response = MockLLMResponse(content="より詳細なPython情報をお伝えします...")
        
        with patch.object(self.rag_pipeline, '_call_llm') as mock_llm_call:
            mock_llm_call.return_value = mock_response
            
            result = self.rag_pipeline.answer_question(query, conversation_history)
            
            # 履歴が考慮されることを確認
            mock_llm_call.assert_called_once()
            call_args = mock_llm_call.call_args[0][0]  # プロンプトを取得
            assert "Pythonとは何ですか？" in call_args  # 履歴が含まれる
            assert "さらに詳しく教えて" in call_args  # 現在の質問も含まれる


class TestOllamaQAEngine:
    """Ollama QAエンジンのテストスイート"""
    
    def setup_method(self):
        """各テスト前の初期化処理"""
        self.qa_engine = OllamaQAEngine(
            model_name="llama3.1:8b",
            base_url="http://localhost:11434"
        )
    
    def test_check_ollama_connection_success(self):
        """Ollama接続成功テスト (Red フェーズ)"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "models": [
                    {"name": "llama3.1:8b", "size": 4661211808}
                ]
            }
            mock_get.return_value = mock_response
            
            is_available = self.qa_engine.check_ollama_connection()
            
            assert is_available is True
            mock_get.assert_called_with("http://localhost:11434/api/tags", timeout=5)
    
    def test_check_ollama_connection_failure(self):
        """Ollama接続失敗テスト (Red フェーズ)"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = ConnectionError("Connection refused")
            
            is_available = self.qa_engine.check_ollama_connection()
            
            assert is_available is False
    
    def test_check_model_availability(self):
        """モデル利用可能性チェックテスト (Red フェーズ)"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "models": [
                    {"name": "llama3.1:8b", "size": 4661211808},
                    {"name": "codellama:7b", "size": 3800000000}
                ]
            }
            mock_get.return_value = mock_response
            
            is_available = self.qa_engine.check_model_availability("llama3.1:8b")
            assert is_available is True
            
            is_available = self.qa_engine.check_model_availability("nonexistent:model")
            assert is_available is False
    
    def test_generate_response_success(self):
        """レスポンス生成成功テスト (Red フェーズ)"""
        prompt = "以下の質問に答えてください：Pythonとは何ですか？"
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "response": "Pythonは高レベルプログラミング言語で、シンプルで読みやすい構文が特徴です。",
                "done": True,
                "context": [],
                "total_duration": 1234567890,
                "load_duration": 123456789
            }
            mock_post.return_value = mock_response
            
            response = self.qa_engine.generate_response(prompt)
            
            assert response.content == "Pythonは高レベルプログラミング言語で、シンプルで読みやすい構文が特徴です。"
            assert response.metadata['done'] is True
            assert 'total_duration' in response.metadata
    
    def test_generate_response_api_error(self):
        """API エラーレスポンステスト (Red フェーズ)"""
        prompt = "テストプロンプト"
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal server error"
            mock_post.return_value = mock_response
            
            with pytest.raises(QAError) as exc_info:
                self.qa_engine.generate_response(prompt)
            
            assert exc_info.value.error_code == "QA-004"
            assert "Ollama API エラー" in str(exc_info.value)
    
    def test_generate_response_timeout(self):
        """レスポンス生成タイムアウトテスト (Red フェーズ)"""
        prompt = "長時間かかるプロンプト"
        
        with patch('requests.post') as mock_post:
            mock_post.side_effect = TimeoutError("Request timeout")
            
            with pytest.raises(QAError) as exc_info:
                self.qa_engine.generate_response(prompt, timeout=1.0)
            
            assert exc_info.value.error_code == "QA-005"
            assert "Ollama応答タイムアウト" in str(exc_info.value)
    
    def test_stream_response(self):
        """ストリーミングレスポンステスト (Red フェーズ)"""
        prompt = "ストリーミングテスト"
        
        # ストリーミングレスポンスのモック
        mock_stream_responses = [
            '{"response": "Python", "done": false}',
            '{"response": "は", "done": false}',
            '{"response": "プログラミング言語", "done": false}',
            '{"response": "です。", "done": true, "total_duration": 1000000}'
        ]
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.iter_lines.return_value = [
                line.encode() for line in mock_stream_responses
            ]
            mock_post.return_value = mock_response
            
            responses = list(self.qa_engine.stream_response(prompt))
            
            assert len(responses) == 4
            assert responses[0].content == "Python"
            assert responses[0].metadata['done'] is False
            assert responses[3].content == "です。"
            assert responses[3].metadata['done'] is True
    
    def test_validate_model_parameters(self):
        """モデルパラメータ検証テスト (Red フェーズ)"""
        # 正常なパラメータ
        valid_params = {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "max_tokens": 1000
        }
        
        result = self.qa_engine._validate_model_parameters(valid_params)
        assert result is True
        
        # 異常なパラメータ
        invalid_params = {
            "temperature": 2.5,  # 0-2の範囲外
            "top_p": -0.1,       # 0-1の範囲外
            "max_tokens": -100   # 負の値
        }
        
        with pytest.raises(QAError) as exc_info:
            self.qa_engine._validate_model_parameters(invalid_params)
        
        assert exc_info.value.error_code == "QA-006"
        assert "パラメータ検証エラー" in str(exc_info.value)


class TestRAGPipelineIntegration:
    """RAGパイプライン統合テスト"""
    
    def setup_method(self):
        """統合テスト用セットアップ"""
        self.test_db_path = Path("./test_integration_db")
        self.indexer = ChromaDBIndexer(
            collection_name="integration_test",
            db_path=str(self.test_db_path)
        )
        self.rag_pipeline = RAGPipeline(indexer=self.indexer)
    
    def teardown_method(self):
        """統合テスト後のクリーンアップ"""
        if self.test_db_path.exists():
            shutil.rmtree(self.test_db_path)
    
    def test_end_to_end_qa_flow(self):
        """エンドツーエンドQAフローテスト (Red フェーズ)"""
        # テストドキュメントを準備
        test_doc = Document(
            file_path="/test/python_guide.txt",
            filename="python_guide.txt",
            content="Pythonは1991年にGuido van Rossumによって開発されたプログラミング言語です。シンプルで読みやすい構文が特徴で、初心者にも学びやすい言語として人気があります。",
            file_type="txt",
            file_size=200
        )
        
        # モックを使用してフロー全体をテスト
        with patch.object(self.indexer, 'add_document') as mock_add:
            with patch.object(self.indexer, 'search_documents') as mock_search:
                with patch.object(self.rag_pipeline, '_call_llm') as mock_llm:
                    
                    # 各段階のモック設定
                    mock_add.return_value = "test_doc_id"
                    mock_search.return_value = [
                        {
                            'content': test_doc.content,
                            'metadata': {'filename': test_doc.filename},
                            'distance': 0.1
                        }
                    ]
                    mock_llm.return_value = MockLLMResponse(
                        content="Pythonは1991年にGuido van Rossumによって開発されました。シンプルで読みやすい構文が特徴です。[参考: python_guide.txt]"
                    )
                    
                    # 1. ドキュメント追加
                    doc_id = self.indexer.add_document(test_doc)
                    assert doc_id == "test_doc_id"
                    
                    # 2. 質問応答実行
                    query = "Pythonはいつ、誰が開発しましたか？"
                    result = self.rag_pipeline.answer_question(query)
                    
                    # 3. 結果検証
                    assert result['query'] == query
                    assert "1991年" in result['answer']
                    assert "Guido van Rossum" in result['answer']
                    assert len(result['sources']) == 1
                    assert result['sources'][0]['filename'] == 'python_guide.txt'
    
    def test_multiple_documents_qa(self):
        """複数ドキュメントからのQAテスト (Red フェーズ)"""
        query = "プログラミング言語の比較について"
        
        # 複数の検索結果をモック
        mock_results = [
            {
                'content': 'Pythonはシンプルで読みやすい構文が特徴です。',
                'metadata': {'filename': 'python.txt'},
                'distance': 0.1
            },
            {
                'content': 'JavaScriptはWebブラウザで動作するスクリプト言語です。',
                'metadata': {'filename': 'javascript.txt'},
                'distance': 0.15
            },
            {
                'content': 'Javaは静的型付けのオブジェクト指向言語です。',
                'metadata': {'filename': 'java.txt'},
                'distance': 0.2
            }
        ]
        
        with patch.object(self.indexer, 'search_documents') as mock_search:
            with patch.object(self.rag_pipeline, '_call_llm') as mock_llm:
                
                mock_search.return_value = mock_results
                mock_llm.return_value = MockLLMResponse(
                    content="""プログラミング言語の比較：
                    1. Python: シンプルで読みやすい構文
                    2. JavaScript: Webブラウザで動作
                    3. Java: 静的型付けのオブジェクト指向
                    [参考: python.txt, javascript.txt, java.txt]"""
                )
                
                result = self.rag_pipeline.answer_question(query)
                
                # 複数ソースが統合されることを確認
                assert len(result['sources']) == 3
                source_files = [s['filename'] for s in result['sources']]
                assert 'python.txt' in source_files
                assert 'javascript.txt' in source_files
                assert 'java.txt' in source_files