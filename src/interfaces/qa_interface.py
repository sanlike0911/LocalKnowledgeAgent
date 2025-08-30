"""
QAInterface実装 (TDD Green フェーズ)
設計書準拠の質問応答インターフェースクラス
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Generator, Callable
import logging
from datetime import datetime
import time
import re
import asyncio

from src.models.config import Config
from src.models.chat_history import ChatHistory
from src.interfaces.indexing_interface import IndexingInterface


class QAError(Exception):
    """質問応答処理関連のエラー"""
    pass


class QAInterface:
    """
    質問応答インターフェースクラス
    
    LangChain + Ollamaを使用した回答生成機能を提供
    """
    
    def __init__(self, config: Config, indexing_interface: IndexingInterface):
        """
        QAインターフェースを初期化
        
        Args:
            config: アプリケーション設定
            indexing_interface: インデックス管理インターフェース
        """
        self.config = config
        self.indexing_interface = indexing_interface
        self.logger = logging.getLogger(__name__)
        
        # 回答生成設定
        self.max_answer_length = 1000
        self.min_similarity_threshold = 0.3
        self.context_window_size = 3000
        
        self.logger.info("QAInterface初期化完了")
    
    def generate_answer(
        self, 
        question: str, 
        chat_history: ChatHistory,
        use_context: bool = False
    ) -> Dict[str, Any]:
        """
        質問に対する回答を生成
        
        Args:
            question: 質問文
            chat_history: チャット履歴
            use_context: 会話コンテキストを使用するか
            
        Returns:
            Dict[str, Any]: 回答結果
            
        Raises:
            QAError: 回答生成に失敗した場合
        """
        try:
            self.logger.info(f"回答生成開始: question='{question[:50]}...'")
            
            # 質問の検証と前処理
            validation_result = self.validate_question(question)
            if not validation_result["is_valid"]:
                raise QAError(f"質問が無効です: {', '.join(validation_result['errors'])}")
            
            processed_question = self.preprocess_question(question)
            
            # 関連文書の検索
            sources = self.search_relevant_documents(
                question=processed_question,
                top_k=5,
                min_similarity=self.min_similarity_threshold
            )
            
            if not sources:
                return {
                    "answer": "申し訳ございませんが、お質問に関連する情報が見つかりませんでした。他の質問をお試しください。",
                    "sources": [],
                    "confidence_score": 0.0,
                    "context_used": use_context
                }
            
            # コンテキストの準備
            context = ""
            if use_context and chat_history.has_messages():
                context = chat_history.get_conversation_context(max_pairs=2)
            
            # 回答の生成
            answer = self._generate_llm_response(
                question=processed_question,
                sources=sources,
                context=context
            )
            
            # 信頼度の計算
            confidence_score = self.calculate_confidence_score(
                sources=sources,
                answer_length=len(answer)
            )
            
            # 回答の後処理
            result = self.postprocess_answer(answer, sources)
            result.update({
                "confidence_score": confidence_score,
                "context_used": use_context
            })
            
            self.logger.info(f"回答生成完了: confidence={confidence_score:.2f}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"回答生成エラー: {e}")
            raise QAError(f"回答生成に失敗しました: {e}")
    
    def search_relevant_documents(
        self, 
        question: str, 
        top_k: int = 10,
        min_similarity: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        質問に関連する文書を検索
        
        Args:
            question: 質問文
            top_k: 最大取得数
            min_similarity: 最小類似度閾値
            
        Returns:
            List[Dict[str, Any]]: 関連文書リスト
        """
        try:
            self.logger.debug(f"関連文書検索: question='{question}', top_k={top_k}")
            
            # インデックスから関連文書を検索
            all_results = self.indexing_interface.search_documents(
                query=question,
                top_k=top_k * 2  # 閾値フィルタリング用に多めに取得
            )
            
            # 類似度閾値でフィルタリング
            filtered_results = [
                result for result in all_results
                if result["similarity_score"] >= min_similarity
            ]
            
            # 上位top_k件を返す
            return filtered_results[:top_k]
            
        except Exception as e:
            self.logger.error(f"関連文書検索エラー: {e}")
            return []
    
    def validate_question(self, question: str) -> Dict[str, Any]:
        """
        質問を検証
        
        Args:
            question: 質問文
            
        Returns:
            Dict[str, Any]: 検証結果
        """
        errors = []
        
        # 空文字チェック
        if not question or not question.strip():
            errors.append("質問は必須です")
        
        # 長さチェック
        elif len(question.strip()) < 3:
            errors.append("質問が短すぎます（3文字以上入力してください）")
        elif len(question) > 1000:
            errors.append("質問が長すぎます（1000文字以内で入力してください）")
        
        # 文字種チェック
        if question.strip() and not re.search(r'[あ-んア-ンa-zA-Z0-9]', question):
            errors.append("有効な文字が含まれていません")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }
    
    def preprocess_question(self, question: str) -> str:
        """
        質問の前処理
        
        Args:
            question: 生の質問文
            
        Returns:
            str: 前処理済み質問文
        """
        # 前後の空白を削除
        processed = question.strip()
        
        # 全角スペースを半角スペースに変換
        processed = processed.replace("　", " ")
        
        # 連続する空白を単一に変換
        processed = re.sub(r'\s+', ' ', processed)
        
        # 特殊文字の正規化
        processed = processed.replace("？", "?").replace("！", "!")
        
        return processed
    
    def postprocess_answer(self, answer: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        回答の後処理
        
        Args:
            answer: 生成された回答
            sources: ソース文書リスト
            
        Returns:
            Dict[str, Any]: 後処理済み回答
        """
        # ソース情報のフォーマット
        formatted_sources = self.format_sources(sources)
        
        # メタデータの生成
        metadata = {
            "answer_length": len(answer),
            "source_count": len(sources),
            "generated_at": datetime.now().isoformat()
        }
        
        return {
            "answer": answer.strip(),
            "sources": formatted_sources,
            "formatted_sources": formatted_sources,
            "metadata": metadata
        }
    
    def format_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        ソース情報をフォーマット
        
        Args:
            sources: 生のソース情報リスト
            
        Returns:
            List[Dict[str, Any]]: フォーマット済みソース情報
        """
        formatted = []
        
        for i, source in enumerate(sources, 1):
            document = source["document"]
            similarity_score = source["similarity_score"]
            
            formatted.append({
                "index": i,
                "title": document.title,
                "file_path": document.file_path,
                "similarity_score": round(similarity_score, 3),
                "preview": document.get_content_preview(150)
            })
        
        return formatted
    
    def calculate_confidence_score(
        self, 
        sources: List[Dict[str, Any]], 
        answer_length: int
    ) -> float:
        """
        回答の信頼度スコアを計算
        
        Args:
            sources: ソース文書リスト
            answer_length: 回答の長さ
            
        Returns:
            float: 信頼度スコア (0.0-1.0)
        """
        if not sources:
            return 0.0
        
        # 平均類似度を計算
        avg_similarity = sum(source["similarity_score"] for source in sources) / len(sources)
        
        # ソース数による調整
        source_factor = min(len(sources) / 3.0, 1.0)  # 3つ以上のソースで最大
        
        # 回答の長さによる調整
        length_factor = min(answer_length / 200.0, 1.0)  # 200文字以上で最大
        
        # 総合信頼度スコア
        confidence = avg_similarity * 0.6 + source_factor * 0.25 + length_factor * 0.15
        
        return round(min(confidence, 1.0), 3)
    
    def generate_answer_stream(
        self, 
        question: str, 
        chat_history: ChatHistory
    ) -> Generator[Dict[str, Any], None, None]:
        """
        ストリーミング形式で回答を生成
        
        Args:
            question: 質問文
            chat_history: チャット履歴
            
        Yields:
            Dict[str, Any]: 回答チャンク
        """
        try:
            self.logger.info(f"ストリーミング回答生成開始: {question[:50]}...")
            
            # 関連文書検索
            sources = self.search_relevant_documents(question)
            
            # 回答をチャンクに分割して返す（実際の実装ではLLMのストリーミングを使用）
            full_answer = self._generate_llm_response(question, sources, "")
            
            # 文章を適切な区切りで分割
            sentences = re.split(r'[。！？]', full_answer)
            
            for i, sentence in enumerate(sentences):
                if sentence.strip():
                    yield {
                        "chunk": sentence + ("。" if i < len(sentences) - 1 else ""),
                        "chunk_index": i,
                        "is_final": i == len(sentences) - 1
                    }
            
            # 最終チャンクでソース情報を提供
            yield {
                "chunk": "",
                "sources": self.format_sources(sources),
                "is_final": True
            }
            
        except Exception as e:
            self.logger.error(f"ストリーミング回答生成エラー: {e}")
            yield {
                "chunk": f"エラーが発生しました: {e}",
                "error": True,
                "is_final": True
            }
    
    async def generate_answer_async(
        self, 
        question: str, 
        chat_history: ChatHistory
    ) -> Dict[str, Any]:
        """
        非同期で回答を生成
        
        Args:
            question: 質問文
            chat_history: チャット履歴
            
        Returns:
            Dict[str, Any]: 回答結果
        """
        try:
            self.logger.info(f"非同期回答生成開始: {question[:50]}...")
            
            # 非同期処理のシミュレーション
            await asyncio.sleep(0.1)
            
            # 実際の回答生成（同期版を使用）
            return self.generate_answer(question, chat_history)
            
        except Exception as e:
            self.logger.error(f"非同期回答生成エラー: {e}")
            raise QAError(f"非同期回答生成に失敗しました: {e}")
    
    def generate_answer_with_metrics(
        self, 
        question: str, 
        chat_history: ChatHistory
    ) -> Dict[str, Any]:
        """
        パフォーマンス測定付きで回答を生成
        
        Args:
            question: 質問文
            chat_history: チャット履歴
            
        Returns:
            Dict[str, Any]: 回答結果（パフォーマンス測定結果付き）
        """
        start_time = time.time()
        
        # 検索時間の測定
        search_start = time.time()
        sources = self.search_relevant_documents(question)
        search_time = time.time() - search_start
        
        # 回答生成時間の測定
        generation_start = time.time()
        answer = self._generate_llm_response(question, sources, "")
        generation_time = time.time() - generation_start
        
        # 総処理時間
        total_time = time.time() - start_time
        
        # 標準的な回答形式
        result = self.postprocess_answer(answer, sources)
        
        # パフォーマンス測定結果を追加
        result["performance_metrics"] = {
            "processing_time": round(total_time, 3),
            "search_time": round(search_time, 3),
            "generation_time": round(generation_time, 3),
            "documents_searched": len(sources)
        }
        
        return result
    
    def _generate_llm_response(
        self, 
        question: str, 
        sources: List[Dict[str, Any]], 
        context: str
    ) -> str:
        """
        LLMを使用して回答を生成（プライベートメソッド）
        
        Args:
            question: 質問文
            sources: ソース文書リスト
            context: 会話コンテキスト
            
        Returns:
            str: 生成された回答
        """
        # 実際の実装では、ここでOllama/LangChainを使用してLLMから回答を生成
        # 現在はシンプルなテンプレートベースの回答を返す
        
        if not sources:
            return "申し訳ございませんが、関連する情報が見つかりませんでした。"
        
        # ソース文書の内容を組み合わせて回答を作成
        source_contents = []
        for source in sources[:3]:  # 上位3つのソースを使用
            doc = source["document"]
            source_contents.append(doc.content[:200])  # 各ソースから200文字
        
        combined_content = " ".join(source_contents)
        
        # 簡易的な回答生成
        answer = f"ご質問について、以下の情報をお伝えします。\n\n{combined_content}\n\n以上の情報が参考になれば幸いです。"
        
        return answer[:self.max_answer_length]
    
    def __str__(self) -> str:
        """QAインターフェースの文字列表現"""
        return f"QAInterface(model={self.config.ollama_model})"
    
    def __repr__(self) -> str:
        """QAインターフェースの詳細文字列表現"""
        return (
            f"QAInterface(ollama_host='{self.config.ollama_host}', "
            f"ollama_model='{self.config.ollama_model}', "
            f"max_answer_length={self.max_answer_length})"
        )