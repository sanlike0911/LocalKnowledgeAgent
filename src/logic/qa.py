"""
LangChain QAシステム実装 (TDD Green フェーズ)
RAGパイプライン・Ollama統合・質問応答機能を提供
"""

import logging
import json
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator, Union
from dataclasses import dataclass
from datetime import datetime
import time

from src.models.document import Document
from src.exceptions.base_exceptions import QAError
from src.logic.indexing import ChromaDBIndexer
from src.utils.structured_logger import get_logger
from src.utils.progress_utils import ProgressTracker, should_show_progress
from src.utils.cancellation_utils import CancellableOperation
from src.utils.performance_monitor import measure_function


@dataclass
class QAResponse:
    """QA応答データクラス"""
    content: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class QAResult:
    """QA結果データクラス"""
    query: str
    answer: str
    sources: List[Dict[str, Any]]
    context: str
    confidence_score: float = 0.0
    processing_time: float = 0.0
    response_language: str = "ja"  # 日本語固定
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'query': self.query,
            'answer': self.answer,
            'sources': self.sources,
            'context': self.context,
            'confidence_score': self.confidence_score,
            'processing_time': self.processing_time,
            'response_language': self.response_language,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class OllamaQAEngine(CancellableOperation):
    """
    Ollama QAエンジン
    
    ローカルOllamaサーバーとの通信・レスポンス生成を担当
    """
    
    def __init__(
        self,
        model_name: str = "llama3.1:8b",
        base_url: str = "http://localhost:11434"
    ):
        """
        Ollama QAエンジンを初期化
        
        Args:
            model_name: 使用するモデル名
            base_url: OllamaサーバーのベースURL
        """
        super().__init__(f"Ollama QA Engine ({model_name})")
        
        self.model_name = model_name
        self.base_url = base_url.rstrip('/')
        self.logger = get_logger(__name__)
        
        # API エンドポイント
        self.generate_url = f"{self.base_url}/api/generate"
        self.models_url = f"{self.base_url}/api/tags"
        
        # デフォルトパラメータ
        self.default_params = {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "max_tokens": 2000,
            "stop": ["[DONE]", "<|im_end|>"]
        }
        
        self.logger.info(f"Ollama QAエンジン初期化完了", extra={
            "model_name": model_name,
            "base_url": base_url
        })
    
    def check_ollama_connection(self, timeout: float = 5.0) -> bool:
        """
        Ollamaサーバーへの接続をチェック
        
        Args:
            timeout: タイムアウト時間（秒）
            
        Returns:
            bool: 接続可能な場合True
        """
        try:
            response = requests.get(self.models_url, timeout=timeout)
            if response.status_code == 200:
                self.logger.info("Ollama接続確認成功")
                return True
            else:
                self.logger.warning(f"Ollama接続エラー: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.warning(f"Ollama接続失敗: {e}")
            return False
    
    def check_model_availability(self, model_name: Optional[str] = None) -> bool:
        """
        指定されたモデルの利用可能性をチェック
        
        Args:
            model_name: チェック対象のモデル名（未指定時はデフォルト）
            
        Returns:
            bool: モデルが利用可能な場合True
        """
        target_model = model_name or self.model_name
        
        try:
            response = requests.get(self.models_url, timeout=5)
            if response.status_code == 200:
                models_data = response.json()
                available_models = [model['name'] for model in models_data.get('models', [])]
                
                is_available = target_model in available_models
                
                if is_available:
                    self.logger.info(f"モデル利用可能: {target_model}")
                else:
                    self.logger.warning(
                        f"モデル利用不可: {target_model}",
                        extra={"available_models": available_models}
                    )
                
                return is_available
            else:
                self.logger.error(f"モデル一覧取得エラー: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"モデル確認エラー: {e}")
            return False
    
    def _validate_model_parameters(self, params: Dict[str, Any]) -> bool:
        """
        モデルパラメータの妥当性検証
        
        Args:
            params: 検証対象パラメータ
            
        Returns:
            bool: パラメータが妥当な場合True
            
        Raises:
            QAError: パラメータが不正な場合
        """
        validation_rules = {
            'temperature': (0.0, 2.0),
            'top_p': (0.0, 1.0),
            'top_k': (1, 100),
            'max_tokens': (1, 10000)
        }
        
        for param_name, value in params.items():
            if param_name in validation_rules:
                min_val, max_val = validation_rules[param_name]
                if not (min_val <= value <= max_val):
                    raise QAError(
                        f"パラメータ検証エラー: {param_name}={value} (範囲: {min_val}-{max_val})",
                        error_code="QA-006",
                        details={
                            "parameter": param_name,
                            "value": value,
                            "valid_range": (min_val, max_val)
                        }
                    )
        
        return True
    
    def generate_response(
        self,
        prompt: str,
        timeout: float = 30.0,
        **model_params
    ) -> QAResponse:
        """
        プロンプトからレスポンスを生成
        
        Args:
            prompt: 入力プロンプト
            timeout: タイムアウト時間（秒）
            **model_params: モデルパラメータ
            
        Returns:
            QAResponse: 生成されたレスポンス
            
        Raises:
            QAError: レスポンス生成エラー
        """
        try:
            self.check_cancellation()
            
            # パラメータをマージして検証
            params = {**self.default_params, **model_params}
            self._validate_model_parameters(params)
            
            # リクエストペイロードを構築
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": params
            }
            
            self.logger.info(f"Ollamaレスポンス生成開始", extra={
                "model": self.model_name,
                "prompt_length": len(prompt)
            })
            
            start_time = time.time()
            
            # Ollama API呼び出し
            response = requests.post(
                self.generate_url,
                json=payload,
                timeout=timeout
            )
            
            processing_time = time.time() - start_time
            
            if response.status_code == 200:
                response_data = response.json()
                
                qa_response = QAResponse(
                    content=response_data.get('response', ''),
                    metadata={
                        'model': self.model_name,
                        'done': response_data.get('done', False),
                        'total_duration': response_data.get('total_duration', 0),
                        'load_duration': response_data.get('load_duration', 0),
                        'processing_time': processing_time,
                        'prompt_eval_count': response_data.get('prompt_eval_count', 0),
                        'eval_count': response_data.get('eval_count', 0)
                    }
                )
                
                self.logger.info(f"Ollamaレスポンス生成完了", extra={
                    "processing_time": processing_time,
                    "response_length": len(qa_response.content)
                })
                
                return qa_response
            else:
                raise QAError(
                    f"Ollama API エラー: {response.status_code} - {response.text}",
                    error_code="QA-004",
                    details={
                        "status_code": response.status_code,
                        "response_text": response.text,
                        "model": self.model_name
                    }
                )
                
        except QAError:
            raise
        except (requests.Timeout, TimeoutError) as e:
            raise QAError(
                f"Ollama応答タイムアウト: {timeout}秒",
                error_code="QA-005",
                details={"timeout": timeout, "model": self.model_name}
            ) from e
        except Exception as e:
            raise QAError(
                f"Ollamaレスポンス生成エラー: {e}",
                error_code="QA-007",
                details={"model": self.model_name, "original_error": str(e)}
            ) from e
    
    def stream_response(
        self,
        prompt: str,
        timeout: float = 60.0,
        **model_params
    ) -> Iterator[QAResponse]:
        """
        ストリーミングレスポンスを生成
        
        Args:
            prompt: 入力プロンプト
            timeout: タイムアウト時間（秒）
            **model_params: モデルパラメータ
            
        Yields:
            QAResponse: ストリーミングレスポンス
            
        Raises:
            QAError: ストリーミングエラー
        """
        try:
            self.check_cancellation()
            
            # パラメータをマージして検証
            params = {**self.default_params, **model_params}
            self._validate_model_parameters(params)
            
            # ストリーミングリクエストペイロード
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": True,
                "options": params
            }
            
            self.logger.info(f"Ollamaストリーミング開始", extra={
                "model": self.model_name,
                "prompt_length": len(prompt)
            })
            
            # ストリーミングリクエスト
            response = requests.post(
                self.generate_url,
                json=payload,
                stream=True,
                timeout=timeout
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    self.check_cancellation()
                    
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            
                            yield QAResponse(
                                content=data.get('response', ''),
                                metadata={
                                    'model': self.model_name,
                                    'done': data.get('done', False),
                                    'total_duration': data.get('total_duration', 0),
                                    'eval_count': data.get('eval_count', 0)
                                }
                            )
                            
                            if data.get('done', False):
                                self.logger.info("Ollamaストリーミング完了")
                                break
                                
                        except json.JSONDecodeError as e:
                            self.logger.warning(f"ストリーミングレスポンス解析エラー: {e}")
                            continue
            else:
                raise QAError(
                    f"Ollamaストリーミングエラー: {response.status_code}",
                    error_code="QA-008",
                    details={"status_code": response.status_code}
                )
                
        except QAError:
            raise
        except Exception as e:
            raise QAError(
                f"Ollamaストリーミングエラー: {e}",
                error_code="QA-009",
                details={"original_error": str(e)}
            ) from e


class RAGPipeline(CancellableOperation):
    """
    RAG (Retrieval-Augmented Generation) パイプライン
    
    ChromaDB検索とOllama回答生成を統合したQAシステム
    """
    
    def __init__(
        self,
        indexer: ChromaDBIndexer,
        model_name: str = "llama3.1:8b",
        max_context_length: int = 4000
    ):
        """
        RAGパイプラインを初期化
        
        Args:
            indexer: ChromaDBインデクサー
            model_name: 使用するOllamaモデル名
            max_context_length: 最大コンテキスト長
        """
        super().__init__(f"RAG Pipeline ({model_name})")
        
        self.indexer = indexer
        self.model_name = model_name
        self.max_context_length = max_context_length
        self.logger = get_logger(__name__)
        
        # Ollama QAエンジンを初期化
        self.qa_engine = OllamaQAEngine(model_name)
        
        # プロンプトテンプレート
        self.qa_prompt_template = """日本語で回答してください。

以下のコンテキスト情報を参考にして、ユーザーの質問に正確で有用な回答を提供してください。

【コンテキスト情報】
{context}

【質問】
{query}

【回答要求】
- 提供されたコンテキスト情報に基づいて回答してください
- コンテキストにない情報については「提供された情報では確認できません」と明記してください
- 日本語で分かりやすく回答してください
- 回答の根拠となった情報源（ファイル名）を明記してください
- 可能な限り具体的で詳細な回答を心がけてください

【回答】"""
        
        self.logger.info(f"RAGパイプライン初期化完了", extra={
            "model_name": model_name,
            "max_context_length": max_context_length
        })
    
    def search_relevant_documents(
        self,
        query: str,
        top_k: int = 5,
        min_similarity_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        関連文書を検索
        
        Args:
            query: 検索クエリ
            top_k: 上位K件を取得
            min_similarity_threshold: 最小類似度閾値
            
        Returns:
            List[Dict[str, Any]]: 検索結果リスト
            
        Raises:
            QAError: 検索エラー
        """
        try:
            self.check_cancellation()
            
            self.logger.info(f"関連文書検索開始", extra={
                "query": query,
                "top_k": top_k
            })
            
            # ChromaDBで検索実行
            search_results = self.indexer.search_documents(query, top_k=top_k)
            
            if not search_results:
                raise QAError(
                    f"関連する文書が見つかりません: {query}",
                    error_code="QA-001",
                    details={"query": query, "searched_documents": 0}
                )
            
            # 類似度フィルタリング（距離が小さいほど類似）
            if min_similarity_threshold > 0:
                filtered_results = [
                    result for result in search_results
                    if result.get('distance', 1.0) <= (1.0 - min_similarity_threshold)
                ]
                
                if not filtered_results:
                    raise QAError(
                        f"類似度閾値({min_similarity_threshold})を満たす文書が見つかりません",
                        error_code="QA-001",
                        details={"query": query, "threshold": min_similarity_threshold}
                    )
                
                search_results = filtered_results
            
            self.logger.info(f"関連文書検索完了", extra={
                "query": query,
                "results_count": len(search_results)
            })
            
            return search_results
            
        except QAError:
            raise
        except Exception as e:
            raise QAError(
                f"文書検索エラー: {e}",
                error_code="QA-002",
                details={"query": query, "original_error": str(e)}
            ) from e
    
    def _generate_context_from_documents(
        self,
        search_results: List[Dict[str, Any]]
    ) -> str:
        """
        検索結果からコンテキストを生成
        
        Args:
            search_results: 検索結果リスト
            
        Returns:
            str: 生成されたコンテキスト
        """
        context_parts = []
        total_length = 0
        
        for i, result in enumerate(search_results):
            content = result.get('content', '')
            metadata = result.get('metadata', {})
            filename = metadata.get('filename', '不明なファイル')
            
            # コンテキスト部分を作成
            context_part = f"{content}\n[出典: {filename}]\n"
            
            # 長さ制限チェック
            if total_length + len(context_part) > self.max_context_length:
                self.logger.warning(f"コンテキスト長制限到達 ({self.max_context_length}文字)")
                break
            
            context_parts.append(context_part)
            total_length += len(context_part)
        
        return "\n".join(context_parts)
    
    def _create_qa_prompt(
        self,
        query: str,
        context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        QA用プロンプトを作成
        
        Args:
            query: ユーザー質問
            context: コンテキスト情報
            conversation_history: 会話履歴
            
        Returns:
            str: 生成されたプロンプト
        """
        # 基本プロンプトを生成
        prompt = self.qa_prompt_template.format(
            context=context.strip(),
            query=query
        )
        
        # 会話履歴がある場合は追加
        if conversation_history:
            history_text = "\n【会話履歴】\n"
            for msg in conversation_history[-5:]:  # 直近5件のみ
                role = "ユーザー" if msg.get('role') == 'user' else "アシスタント"
                content = msg.get('content', '')
                history_text += f"{role}: {content}\n"
            
            # プロンプトの質問部分の前に履歴を挿入
            prompt = prompt.replace("【質問】", f"{history_text}\n【質問】")
        
        return prompt
    
    def _create_direct_qa_prompt(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        ドキュメントがない場合の直接QA用プロンプトを作成
        
        Args:
            query: ユーザー質問
            conversation_history: 会話履歴
            
        Returns:
            str: 生成されたプロンプト
        """
        # ドキュメントなしの場合のプロンプトテンプレート
        direct_prompt_template = """日本語で回答してください。

以下の質問に、あなたの知識に基づいて分かりやすく回答してください。

【質問】
{query}

【回答要求】
- 日本語で分かりやすく回答してください
- 知識ベースに参考資料がないため、一般的な知識に基づいて回答します
- 不明な点については正直に「わからない」と答えてください
- 可能な限り有用で建設的な回答を心がけてください

【回答】"""
        
        # 基本プロンプトを生成
        prompt = direct_prompt_template.format(query=query)
        
        # 会話履歴がある場合は追加
        if conversation_history:
            history_text = "\n【会話履歴】\n"
            for msg in conversation_history[-5:]:  # 直近5件のみ
                role = "ユーザー" if msg.get('role') == 'user' else "アシスタント"
                content = msg.get('content', '')
                history_text += f"{role}: {content}\n"
            
            # プロンプトの質問部分の前に履歴を挿入
            prompt = prompt.replace("【質問】", f"{history_text}\n【質問】")
        
        return prompt
    
    def _call_llm(self, prompt: str) -> QAResponse:
        """
        LLMを呼び出してレスポンスを生成
        
        Args:
            prompt: 入力プロンプト
            
        Returns:
            QAResponse: LLMレスポンス
        """
        return self.qa_engine.generate_response(prompt)
    
    @measure_function("rag_pipeline_answer_question")
    def answer_question(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 5,
        min_similarity_threshold: float = 0.0
    ) -> Dict[str, Any]:
        """
        質問に対する回答を生成
        
        Args:
            query: ユーザー質問
            conversation_history: 会話履歴
            top_k: 検索上位K件
            min_similarity_threshold: 最小類似度閾値
            
        Returns:
            Dict[str, Any]: QA結果
            
        Raises:
            QAError: 回答生成エラー
        """
        start_time = time.time()
        
        try:
            self.check_cancellation()
            
            self.logger.info(f"質問応答開始", extra={
                "query": query,
                "top_k": top_k
            })
            
            # 1. 関連文書検索（ドキュメント0件対応）
            search_results = []
            context = ""
            try:
                search_results = self.search_relevant_documents(
                    query, 
                    top_k=top_k, 
                    min_similarity_threshold=min_similarity_threshold
                )
                # 2. コンテキスト生成
                context = self._generate_context_from_documents(search_results)
                
            except QAError as search_error:
                # ドキュメント0件の場合のフォールバック処理
                if "関連する文書が見つかりません" in str(search_error):
                    self.logger.info(f"ドキュメント0件 - 直接LLM回答モードに切り替え", extra={
                        "query": query,
                        "reason": "no_documents_found"
                    })
                    context = ""
                    search_results = []
                else:
                    # その他の検索エラーは再発生
                    raise
            
            self.check_cancellation()
            
            # 3. プロンプト作成（文書なしモード対応）
            if context:
                # 通常のRAGプロンプト
                prompt = self._create_qa_prompt(query, context, conversation_history)
            else:
                # ドキュメントがない場合のプロンプト
                prompt = self._create_direct_qa_prompt(query, conversation_history)
            
            self.check_cancellation()
            
            # 4. LLM回答生成
            try:
                llm_response = self._call_llm(prompt)
            except Exception as e:
                raise QAError(
                    f"回答生成エラー: {e}",
                    error_code="QA-003",
                    details={"query": query, "original_error": str(e)}
                ) from e
            
            processing_time = time.time() - start_time
            
            # 5. ソース情報を抽出
            sources = []
            for result in search_results:
                metadata = result.get('metadata', {})
                sources.append({
                    'filename': metadata.get('filename', '不明'),
                    'chunk_index': metadata.get('chunk_index', 0),
                    'distance': result.get('distance', 1.0),
                    'content_preview': result.get('content', '')[:100] + '...' if len(result.get('content', '')) > 100 else result.get('content', '')
                })
            
            # 6. 結果を構築
            result = {
                'query': query,
                'answer': llm_response.content,
                'sources': sources,
                'context': context,
                'processing_time': processing_time,
                'response_language': "ja",  # 日本語固定
                'model_metadata': llm_response.metadata,
                'created_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"質問応答完了", extra={
                "query": query,
                "processing_time": processing_time,
                "sources_count": len(sources),
                "answer_length": len(llm_response.content)
            })
            
            return result
            
        except QAError:
            raise
        except Exception as e:
            processing_time = time.time() - start_time
            raise QAError(
                f"質問応答エラー: {e}",
                error_code="QA-010",
                details={
                    "query": query,
                    "processing_time": processing_time,
                    "original_error": str(e)
                }
            ) from e
    
    def answer_question_stream(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 5
    ) -> Iterator[Dict[str, Any]]:
        """
        ストリーミング形式で質問に回答
        
        Args:
            query: ユーザー質問
            conversation_history: 会話履歴
            top_k: 検索上位K件
            
        Yields:
            Dict[str, Any]: ストリーミング結果
        """
        try:
            self.check_cancellation()
            
            # 関連文書検索
            search_results = self.search_relevant_documents(query, top_k=top_k)
            
            # コンテキスト生成
            context = self._generate_context_from_documents(search_results)
            
            # プロンプト作成
            prompt = self._create_qa_prompt(query, context, conversation_history)
            
            # ソース情報を準備
            sources = [
                {
                    'filename': result.get('metadata', {}).get('filename', '不明'),
                    'distance': result.get('distance', 1.0)
                }
                for result in search_results
            ]
            
            # 最初に検索結果を送信
            yield {
                'type': 'sources',
                'query': query,
                'sources': sources,
                'context_length': len(context)
            }
            
            # ストリーミングレスポンスを生成
            full_answer = ""
            for chunk in self.qa_engine.stream_response(prompt):
                self.check_cancellation()
                
                full_answer += chunk.content
                
                yield {
                    'type': 'content',
                    'content': chunk.content,
                    'done': chunk.metadata.get('done', False),
                    'full_answer': full_answer
                }
                
                if chunk.metadata.get('done', False):
                    break
            
            # 最終結果を送信
            yield {
                'type': 'complete',
                'query': query,
                'answer': full_answer,
                'sources': sources
            }
            
        except Exception as e:
            yield {
                'type': 'error',
                'error': str(e),
                'query': query
            }
    
    def check_system_health(self) -> Dict[str, Any]:
        """
        RAGシステムの健康状態をチェック
        
        Returns:
            Dict[str, Any]: システム状態情報
        """
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'components': {}
        }
        
        try:
            # ChromaDB状態チェック
            indexer_stats = self.indexer.get_collection_stats()
            health_status['components']['chromadb'] = {
                'status': 'healthy' if indexer_stats.get('document_count', 0) >= 0 else 'error',
                'document_count': indexer_stats.get('document_count', 0),
                'collection_name': indexer_stats.get('collection_name', 'unknown')
            }
            
            # Ollama状態チェック
            ollama_available = self.qa_engine.check_ollama_connection()
            model_available = self.qa_engine.check_model_availability() if ollama_available else False
            
            health_status['components']['ollama'] = {
                'status': 'healthy' if (ollama_available and model_available) else 'error',
                'connection': ollama_available,
                'model_available': model_available,
                'model_name': self.model_name
            }
            
            # 全体ステータス判定
            component_statuses = [comp['status'] for comp in health_status['components'].values()]
            if 'error' in component_statuses:
                health_status['overall_status'] = 'degraded'
            
        except Exception as e:
            health_status['overall_status'] = 'error'
            health_status['error'] = str(e)
            
        return health_status


class QAService:
    """
    QAサービス (アプリケーションレイヤー)
    
    RAGPipelineのラッパーとして動作し、アプリケーション層に
    統一されたQAインターフェースを提供する
    """
    
    def __init__(
        self,
        indexer: ChromaDBIndexer,
        model_name: str = "llama3.1:8b",
        max_context_length: int = 4000
    ):
        """
        QAサービスを初期化
        
        Args:
            indexer: ChromaDBインデクサー
            model_name: 使用するOllamaモデル名
            max_context_length: 最大コンテキスト長
        """
        self.indexer = indexer
        self.model_name = model_name
        self.max_context_length = max_context_length
        self.logger = get_logger(__name__)
        
        # RAGPipelineを内部で使用
        self.rag_pipeline = RAGPipeline(
            indexer=indexer,
            model_name=model_name,
            max_context_length=max_context_length
        )
        
        self.logger.info(f"QAサービス初期化完了", extra={
            "model_name": model_name,
            "max_context_length": max_context_length
        })
    
    @measure_function("qa_service_ask_question")
    def ask_question(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 5,
        min_similarity_threshold: float = 0.0
    ) -> Dict[str, Any]:
        """
        質問に対する回答を生成
        
        Args:
            query: ユーザー質問
            conversation_history: 会話履歴
            top_k: 検索上位K件
            min_similarity_threshold: 最小類似度閾値
            
        Returns:
            Dict[str, Any]: QA結果
            
        Raises:
            QAError: 回答生成エラー
        """
        try:
            return self.rag_pipeline.answer_question(
                query=query,
                conversation_history=conversation_history,
                top_k=top_k,
                min_similarity_threshold=min_similarity_threshold
            )
        except QAError as e:
            # QAErrorは詳細ログとともに再発生
            self.logger.error(f"QAError in ask_question: {e}", exc_info=True, 
                            extra={"query": query, "top_k": top_k})
            raise
    
    def ask_question_stream(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 5
    ) -> Iterator[Dict[str, Any]]:
        """
        ストリーミング形式で質問に回答
        
        Args:
            query: ユーザー質問
            conversation_history: 会話履歴
            top_k: 検索上位K件
            
        Yields:
            Dict[str, Any]: ストリーミング結果
        """
        try:
            yield from self.rag_pipeline.answer_question_stream(
                query=query,
                conversation_history=conversation_history,
                top_k=top_k
            )
        except QAError:
            # QAErrorはそのまま再発生
            raise
    
    def search_documents(
        self,
        query: str,
        top_k: int = 5,
        min_similarity_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        関連文書を検索
        
        Args:
            query: 検索クエリ
            top_k: 上位K件を取得
            min_similarity_threshold: 最小類似度閾値
            
        Returns:
            List[Dict[str, Any]]: 検索結果リスト
            
        Raises:
            QAError: 検索エラー
        """
        try:
            return self.rag_pipeline.search_relevant_documents(
                query=query,
                top_k=top_k,
                min_similarity_threshold=min_similarity_threshold
            )
        except QAError:
            # QAErrorはそのまま再発生
            raise
    
    def check_system_health(self) -> Dict[str, Any]:
        """
        システムの健康状態をチェック
        
        Returns:
            Dict[str, Any]: システム状態情報
        """
        return self.rag_pipeline.check_system_health()
    
    def cancel(self) -> None:
        """
        現在実行中の操作をキャンセル
        """
        self.rag_pipeline.cancel()