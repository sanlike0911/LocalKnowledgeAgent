"""
ISSUE-022: LLM モデル動的選択機能
PHASE 6.2: モデル情報表示機能拡張

Ollama API との通信を行い、利用可能なモデル一覧を取得する機能を提供
設計書仕様に基づいた実装
"""

import requests
from requests.exceptions import ConnectionError, Timeout, HTTPError
from typing import List, Optional, Dict, Any
from datetime import datetime
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

    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        指定されたモデルの詳細情報を取得
        
        Args:
            model_name: 情報を取得するモデル名
            
        Returns:
            Optional[Dict[str, Any]]: モデル情報の辞書、存在しない場合はNone
        """
        try:
            response = requests.get(
                f"{self.host}/api/tags",
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            models = data.get("models", [])
            
            for model in models:
                if model.get("name") == model_name:
                    return dict(model)
                    
            return None
            
        except Exception:
            # 任意のエラーでNoneを返す
            return None

    def get_all_models_info(self) -> List[Dict[str, Any]]:
        """
        全ての利用可能なモデルの詳細情報を取得
        
        Returns:
            List[Dict[str, Any]]: モデル情報の辞書のリスト
        """
        try:
            response = requests.get(
                f"{self.host}/api/tags",
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            return list(data.get("models", []))
            
        except Exception:
            # 任意のエラーで空リストを返す
            return []

    def format_model_size(self, size_bytes: int) -> str:
        """
        バイト数を人間が読みやすい形式に変換
        
        Args:
            size_bytes: バイト単位のサイズ
            
        Returns:
            str: 人間が読みやすい形式のサイズ文字列
        """
        if size_bytes == 0:
            return "0 B"
        
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
            
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.1f} {units[unit_index]}"

    def format_datetime(self, iso_datetime: Optional[str]) -> str:
        """
        ISO形式の日時を日本語フォーマットに変換
        
        Args:
            iso_datetime: ISO形式の日時文字列
            
        Returns:
            str: 日本語フォーマットの日時文字列
        """
        if not iso_datetime:
            return "不明"
            
        try:
            # ISO形式のパース（Zタイムゾーン対応）
            dt = datetime.fromisoformat(iso_datetime.replace('Z', '+00:00'))
            return dt.strftime("%Y年%m月%d日 %H:%M")
        except (ValueError, AttributeError):
            return "不明"

    def is_large_model(self, size_bytes: int, threshold_gb: int = 7) -> bool:
        """
        モデルが大容量かどうかを判定
        
        Args:
            size_bytes: モデルのバイトサイズ
            threshold_gb: 大容量と判定するしきい値（GB）
            
        Returns:
            bool: 大容量モデルの場合True
        """
        threshold_bytes = threshold_gb * 1024 * 1024 * 1024
        return size_bytes > threshold_bytes

    def estimate_memory_usage(self, model_size: int) -> int:
        """
        モデルサイズからメモリ使用量を推定
        
        Args:
            model_size: モデルのバイトサイズ
            
        Returns:
            int: 推定メモリ使用量（バイト）
        """
        # 一般的にモデルサイズの1.3倍のメモリが必要
        return int(model_size * 1.3)

    def filter_embedding_models(self, installed_models: List[Dict[str, Any]], supported_models: List[str]) -> List[str]:
        """
        インストール済みモデルリストを、サポート対象モデルリストでフィルタリングする
        
        バージョンタグ（:latest, :1.0等）を自動除去して一致判定を行う
        
        Args:
            installed_models: Ollamaにインストール済みのモデル情報辞書のリスト
            supported_models: サポート対象の埋め込みモデル名のリスト
            
        Returns:
            List[str]: 両方のリストに存在するモデル名のソート済みリスト（バージョンタグ除去済み）
        """
        if not installed_models:
            return []
        
        if not supported_models:
            return []
        
        # インストール済みモデルから名前を抽出（バージョンタグを除去）
        installed_model_names = set()
        for model in installed_models:
            if isinstance(model, dict) and model.get("name"):
                name = model["name"]
                # バージョンタグを除去（:以降を削除）
                base_name = name.split(':')[0] if ':' in name else name
                if base_name:  # 空文字列でない場合のみ追加
                    installed_model_names.add(base_name)
        
        # サポート対象モデルをセットに変換
        supported_model_set = set(supported_models)
        
        # 両方のリストに存在するモデルのみを抽出（積集合）
        filtered_models = list(installed_model_names.intersection(supported_model_set))
        
        # ソートして返す
        return sorted(filtered_models)
    
    def get_filtered_embedding_models_with_fallback(self, supported_models: List[str]) -> List[str]:
        """
        フィルタリング済み埋め込みモデル一覧をフォールバック機能付きで取得
        
        API接続に失敗した場合は、サポート対象モデルリストをそのまま返す
        
        Args:
            supported_models: サポート対象の埋め込みモデル名のリスト
            
        Returns:
            List[str]: フィルタリング済みモデル名のリスト（API成功時）またはサポートモデル一覧
        """
        try:
            installed_models = self.get_all_models_info()
            return self.filter_embedding_models(installed_models, supported_models)
        except OllamaConnectionError:
            # API接続失敗時はサポートモデル一覧をそのまま返す
            return supported_models.copy()