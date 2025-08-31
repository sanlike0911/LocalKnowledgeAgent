"""
Ollama モデル確認サービス

起動時にOllamaの必須モデルが利用可能かをチェックし、
不足している場合はユーザーに適切なガイダンスを提供
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import requests
import logging

from ..utils.structured_logger import get_logger
from ..exceptions.base_exceptions import LocalKnowledgeAgentError


@dataclass
class ModelInfo:
    """Ollamaモデル情報"""
    name: str
    display_name: str
    description: str
    install_command: str


@dataclass
class ModelCheckResult:
    """モデルチェック結果"""
    is_available: bool
    missing_models: List[ModelInfo]
    available_models: List[str]
    ollama_connected: bool
    error_message: Optional[str] = None


class OllamaModelChecker:
    """
    Ollama モデル確認サービス
    
    アプリケーション起動時に必須モデルの存在を確認し、
    不足している場合は適切なガイダンスを提供する
    """
    
    # 必須モデル定義
    REQUIRED_MODELS = {
        "llama3:8b": ModelInfo(
            name="llama3:8b",
            display_name="LLaMA 3 8B (回答生成用)",
            description="質問への回答生成を行う大規模言語モデル",
            install_command="ollama pull llama3:8b"
        ),
        "nomic-embed-text": ModelInfo(
            name="nomic-embed-text",
            display_name="Nomic Embed Text (埋め込みモデル)",
            description="文書のベクトル化・検索を行う埋め込みモデル",
            install_command="ollama pull nomic-embed-text"
        )
    }
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        """
        OllamaModelCheckerを初期化
        
        Args:
            base_url: OllamaサーバーのベースURL
        """
        self.base_url = base_url
        self.models_url = f"{base_url}/api/tags"
        self.logger = get_logger(__name__)
    
    def check_required_models(self) -> ModelCheckResult:
        """
        必須モデルの存在確認を実行
        
        Returns:
            ModelCheckResult: チェック結果
        """
        try:
            # Ollama接続確認
            if not self._check_ollama_connection():
                return ModelCheckResult(
                    is_available=False,
                    missing_models=list(self.REQUIRED_MODELS.values()),
                    available_models=[],
                    ollama_connected=False,
                    error_message="Ollamaサーバーに接続できません。Ollamaが起動しているか確認してください。"
                )
            
            # 利用可能モデル取得
            available_models = self._get_available_models()
            
            # 不足モデル特定
            missing_models = []
            for model_name, model_info in self.REQUIRED_MODELS.items():
                if not self._is_model_available(model_name, available_models):
                    missing_models.append(model_info)
                    self.logger.warning(f"必須モデルが不足: {model_name}")
                else:
                    self.logger.info(f"必須モデル確認済み: {model_name}")
            
            return ModelCheckResult(
                is_available=len(missing_models) == 0,
                missing_models=missing_models,
                available_models=available_models,
                ollama_connected=True,
                error_message=None
            )
            
        except Exception as e:
            self.logger.error(f"モデルチェック処理中にエラー: {e}")
            return ModelCheckResult(
                is_available=False,
                missing_models=list(self.REQUIRED_MODELS.values()),
                available_models=[],
                ollama_connected=False,
                error_message=f"モデルチェック中にエラーが発生しました: {str(e)}"
            )
    
    def _check_ollama_connection(self, timeout: float = 5.0) -> bool:
        """
        Ollamaサーバーへの接続確認
        
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
                
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Ollama接続失敗: {e}")
            return False
    
    def _get_available_models(self) -> List[str]:
        """
        利用可能なモデル一覧を取得
        
        Returns:
            List[str]: 利用可能なモデル名のリスト
        """
        try:
            response = requests.get(self.models_url, timeout=10)
            if response.status_code == 200:
                models_data = response.json()
                models = [model['name'] for model in models_data.get('models', [])]
                self.logger.info(f"利用可能モデル数: {len(models)}")
                return models
            else:
                self.logger.error(f"モデル一覧取得エラー: {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.error(f"モデル一覧取得失敗: {e}")
            return []
    
    def _is_model_available(self, model_name: str, available_models: List[str]) -> bool:
        """
        指定されたモデルが利用可能かチェック
        
        Args:
            model_name: チェック対象のモデル名
            available_models: 利用可能なモデル一覧
            
        Returns:
            bool: モデルが利用可能な場合True
        """
        # 完全一致チェック
        if model_name in available_models:
            return True
        
        # バージョン違いを考慮した部分一致チェック
        model_base = model_name.split(':')[0]
        for available in available_models:
            if available.startswith(model_base):
                self.logger.info(f"モデル部分一致: {model_name} -> {available}")
                return True
        
        return False
    
    def get_installation_guide(self, missing_models: List[ModelInfo]) -> str:
        """
        不足モデルのインストールガイドを生成
        
        Args:
            missing_models: 不足しているモデルのリスト
            
        Returns:
            str: インストールガイドのテキスト
        """
        if not missing_models:
            return "すべての必須モデルがインストール済みです。"
        
        guide_lines = [
            "🚨 **必須モデルが不足しています**",
            "",
            "アプリケーションを使用するために、以下のモデルをインストールしてください：",
            ""
        ]
        
        for i, model in enumerate(missing_models, 1):
            guide_lines.extend([
                f"**{i}. {model.display_name}**",
                f"   - 用途: {model.description}",
                f"   - インストールコマンド: `{model.install_command}`",
                ""
            ])
        
        guide_lines.extend([
            "**インストール手順:**",
            "1. コマンドプロンプトまたはターミナルを開く",
            "2. 上記のコマンドを順番に実行する",
            "3. インストール完了後、このアプリケーションを再起動する",
            "",
            "**注意:** モデルのダウンロードには時間がかかる場合があります。"
        ])
        
        return "\n".join(guide_lines)