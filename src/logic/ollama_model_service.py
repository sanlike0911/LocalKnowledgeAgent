"""
ISSUE-022: LLM モデル動的選択機能

Ollama API との通信を行い、利用可能なモデル一覧を取得する機能を提供
設計書仕様に基づいた実装
"""

import requests
from requests.exceptions import ConnectionError, Timeout, HTTPError
from typing import List, Optional
from src.exceptions.base_exceptions import LocalKnowledgeAgentError


class OllamaConnectionError(LocalKnowledgeAgentError):
    """Ollama接続関連のエラー"""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


class OllamaModelService:
    """
    Ollama API との通信を管理するサービスクラス
    
    モデル一覧の取得、モデル利用可能性の確認、
    エラーハンドリングとフォールバック機能を提供
    """
    
    def __init__(self, host: str = "http://localhost:11434", timeout: int = 5):
        """
        OllamaModelService を初期化
        
        Args:
            host: Ollama サーバーのホストURL
            timeout: API リクエストのタイムアウト（秒）
        """
        self.host = host.rstrip('/')  # 末尾のスラッシュを削除
        self.timeout = timeout
        
    def get_available_models(self) -> List[str]:
        """
        Ollama API から利用可能なモデル一覧を取得
        
        Returns:
            List[str]: 利用可能なモデル名のリスト
            
        Raises:
            OllamaConnectionError: API 接続またはレスポンス処理でエラーが発生した場合
        """
        try:
            response = requests.get(
                f"{self.host}/api/tags",
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # JSONレスポンスからモデル一覧を抽出
            data = response.json()
            models = data.get("models", [])
            
            # モデル名のみを抽出
            model_names = [model.get("name", "") for model in models if model.get("name")]
            return model_names
            
        except ConnectionError as e:
            raise OllamaConnectionError(
                "Ollamaサーバーへの接続に失敗しました。Ollamaが起動しているか確認してください。",
                e
            )
            
        except Timeout as e:
            raise OllamaConnectionError(
                f"Ollamaサーバーへの接続がタイムアウトしました（{self.timeout}秒）。",
                e
            )
            
        except HTTPError as e:
            raise OllamaConnectionError(
                f"Ollama APIでエラーが発生しました: {e}",
                e
            )
            
        except ValueError as e:
            # JSON デコードエラー
            raise OllamaConnectionError(
                "Ollama APIからの応答が不正です。",
                e
            )
            
        except Exception as e:
            raise OllamaConnectionError(
                f"予期しないエラーが発生しました: {e}",
                e
            )
    
    def get_available_models_with_fallback(self, fallback_models: List[str]) -> List[str]:
        """
        フォールバック機能付きでモデル一覧を取得
        
        API 接続に失敗した場合は、提供されたフォールバックモデル一覧を返す
        
        Args:
            fallback_models: API 接続失敗時に使用するデフォルトモデル一覧
            
        Returns:
            List[str]: 利用可能なモデル名のリスト（API成功時）またはフォールバックモデル一覧
        """
        try:
            return self.get_available_models()
        except OllamaConnectionError:
            # API 接続失敗時はフォールバックモデルを返す
            return fallback_models.copy()
    
    def is_model_available(self, model_name: str) -> bool:
        """
        指定されたモデルが利用可能かチェック
        
        Args:
            model_name: チェックするモデル名
            
        Returns:
            bool: モデルが利用可能な場合 True、そうでなければ False
        """
        try:
            available_models = self.get_available_models()
            return model_name in available_models
        except OllamaConnectionError:
            # API接続失敗時は False を返す
            return False