"""
ConfigInterface実装 (TDD Green フェーズ)  
設計書準拠の設定管理インターフェースクラス
"""

from typing import Dict, Any, List, Optional, Union
import logging
import json
import os
from datetime import datetime
from pathlib import Path

from src.models.config import Config, ConfigError
from src.utils.env_validator import get_app_config


class ConfigInterfaceError(Exception):
    """設定インターフェース関連のエラー"""
    pass


class ConfigInterface:
    """
    設定管理インターフェースクラス
    
    アプリケーション設定の読み込み、保存、検証、バックアップ機能を提供
    """
    
    def __init__(self):
        """ConfigInterfaceを初期化"""
        self.logger = logging.getLogger(__name__)
        self.default_config_file = "./data/config.json"
        self.backup_directory = "./backups"
        
        self.logger.info("ConfigInterface初期化完了")
    
    def load_configuration(self, file_path: str) -> Config:
        """
        設定ファイルから設定を読み込み
        
        Args:
            file_path: 設定ファイルのパス
            
        Returns:
            Config: 読み込まれた設定
            
        Raises:
            ConfigInterfaceError: 読み込みに失敗した場合
        """
        try:
            self.logger.info(f"設定読み込み開始: {file_path}")
            
            if not Path(file_path).exists():
                raise ConfigInterfaceError(f"設定ファイルが存在しません: {file_path}")
            
            config = Config.load_from_file(file_path)
            
            # 設定を検証
            validation_result = self.validate_configuration(config)
            if not validation_result["is_valid"]:
                self.logger.warning(f"設定に問題があります: {validation_result['errors']}")
            
            self.logger.info("設定読み込み完了")
            return config
            
        except ConfigError as e:
            raise ConfigInterfaceError(f"設定ファイルの読み込みに失敗しました: {e}")
        except Exception as e:
            self.logger.error(f"設定読み込みエラー: {e}")
            raise ConfigInterfaceError(f"予期しないエラーが発生しました: {e}")
    
    def save_configuration(self, config: Config, file_path: str) -> bool:
        """
        設定をファイルに保存
        
        Args:
            config: 保存する設定
            file_path: 保存先ファイルパス
            
        Returns:
            bool: 成功した場合True
            
        Raises:
            ConfigInterfaceError: 保存に失敗した場合
        """
        try:
            self.logger.info(f"設定保存開始: {file_path}")
            
            # 設定を検証
            validation_result = self.validate_configuration(config)
            if not validation_result["is_valid"]:
                raise ConfigInterfaceError(f"設定が無効です: {', '.join(validation_result['errors'])}")
            
            # ディレクトリが存在しない場合は作成
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            config.save_to_file(file_path)
            
            self.logger.info("設定保存完了")
            return True
            
        except ConfigError as e:
            raise ConfigInterfaceError(f"設定ファイルの保存に失敗しました: {e}")
        except Exception as e:
            self.logger.error(f"設定保存エラー: {e}")
            raise ConfigInterfaceError(f"予期しないエラーが発生しました: {e}")
    
    def get_default_configuration(self) -> Config:
        """
        デフォルト設定を取得
        
        Returns:
            Config: デフォルト設定
        """
        self.logger.info("デフォルト設定を取得")
        return Config()
    
    def validate_configuration(self, config: Config) -> Dict[str, Any]:
        """
        設定を検証
        
        Args:
            config: 検証する設定
            
        Returns:
            Dict[str, Any]: 検証結果
        """
        try:
            errors = []
            warnings = []
            
            # 基本的な検証はConfigクラスで行われるが、追加の検証を実行
            
            # パスの存在チェック
            path_problems = config.validate_paths()
            if path_problems:
                warnings.extend(path_problems)
            
            # Ollamaホストの接続チェック（簡易）
            if not config.ollama_host.startswith(('http://', 'https://')):
                errors.append("Ollamaホストは有効なURLである必要があります")
            
            # 拡張子の検証
            for ext in config.supported_extensions:
                if not ext.startswith('.'):
                    warnings.append(f"拡張子にドットが必要です: {ext}")
            
            return {
                "is_valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            self.logger.error(f"設定検証エラー: {e}")
            return {
                "is_valid": False,
                "errors": [f"検証中にエラーが発生しました: {e}"],
                "warnings": []
            }
    
    def merge_configurations(self, base_config: Config, update_config: Config) -> Config:
        """
        設定をマージ
        
        Args:
            base_config: ベース設定
            update_config: 更新設定
            
        Returns:
            Config: マージされた設定
        """
        self.logger.info("設定のマージを開始")
        
        # ベース設定を辞書に変換
        base_dict = base_config.to_dict()
        update_dict = update_config.to_dict()
        
        # 更新設定でベース設定を上書き（Noneや空でない値のみ）
        merged_dict = base_dict.copy()
        
        for key, value in update_dict.items():
            if value is not None:
                if isinstance(value, str) and value.strip():
                    merged_dict[key] = value
                elif isinstance(value, (int, float, bool)):
                    merged_dict[key] = value
                elif isinstance(value, list) and len(value) > 0:
                    merged_dict[key] = value
        
        # マージされた設定からConfigオブジェクトを作成
        merged_config = Config.from_dict(merged_dict)
        
        self.logger.info("設定のマージ完了")
        return merged_config
    
    def export_configuration(self, config: Config, format: str = "dict") -> Union[Dict[str, Any], str]:
        """
        設定をエクスポート
        
        Args:
            config: エクスポートする設定
            format: エクスポート形式 ("dict" or "json")
            
        Returns:
            Union[Dict[str, Any], str]: エクスポートされたデータ
            
        Raises:
            ConfigInterfaceError: 不正な形式が指定された場合
        """
        if format == "dict":
            return config.to_dict()
        elif format == "json":
            return json.dumps(config.to_dict(), indent=2, ensure_ascii=False)
        else:
            raise ConfigInterfaceError(f"不明な形式です: {format}")
    
    def import_configuration(self, data: Union[Dict[str, Any], str], format: str = "dict") -> Config:
        """
        データから設定をインポート
        
        Args:
            data: インポートするデータ
            format: データ形式 ("dict" or "json")
            
        Returns:
            Config: インポートされた設定
            
        Raises:
            ConfigInterfaceError: インポートに失敗した場合
        """
        try:
            if format == "dict":
                if not isinstance(data, dict):
                    raise ConfigInterfaceError("辞書形式のデータが必要です")
                config_dict = data
            elif format == "json":
                if not isinstance(data, str):
                    raise ConfigInterfaceError("JSON文字列が必要です")
                config_dict = json.loads(data)
            else:
                raise ConfigInterfaceError(f"不明な形式です: {format}")
            
            config = Config.from_dict(config_dict)
            return config
            
        except json.JSONDecodeError as e:
            raise ConfigInterfaceError(f"JSON解析エラー: {e}")
        except Exception as e:
            raise ConfigInterfaceError(f"インポートエラー: {e}")
    
    def backup_configuration(self, config: Config, backup_dir: str) -> Dict[str, Any]:
        """
        設定をバックアップ
        
        Args:
            config: バックアップする設定
            backup_dir: バックアップディレクトリ
            
        Returns:
            Dict[str, Any]: バックアップ結果
        """
        try:
            self.logger.info(f"設定バックアップ開始: {backup_dir}")
            
            # バックアップディレクトリを作成
            Path(backup_dir).mkdir(parents=True, exist_ok=True)
            
            # タイムスタンプ付きファイル名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = Path(backup_dir) / f"config_backup_{timestamp}.json"
            
            # バックアップデータを準備
            backup_data = config.to_dict()
            backup_data.update({
                "timestamp": datetime.now().isoformat(),
                "version": "1.0",
                "backup_type": "manual"
            })
            
            # バックアップファイルを保存
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"バックアップ完了: {backup_file}")
            
            return {
                "success": True,
                "backup_file": str(backup_file),
                "timestamp": backup_data["timestamp"]
            }
            
        except Exception as e:
            self.logger.error(f"バックアップエラー: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def restore_configuration(self, backup_file: str) -> Config:
        """
        バックアップから設定を復元
        
        Args:
            backup_file: バックアップファイルのパス
            
        Returns:
            Config: 復元された設定
            
        Raises:
            ConfigInterfaceError: 復元に失敗した場合
        """
        try:
            self.logger.info(f"設定復元開始: {backup_file}")
            
            if not Path(backup_file).exists():
                raise ConfigInterfaceError(f"バックアップファイルが存在しません: {backup_file}")
            
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # バックアップメタデータを除去
            config_data = backup_data.copy()
            for meta_key in ["timestamp", "version", "backup_type"]:
                config_data.pop(meta_key, None)
            
            config = Config.from_dict(config_data)
            
            self.logger.info("設定復元完了")
            return config
            
        except json.JSONDecodeError as e:
            raise ConfigInterfaceError(f"バックアップファイルの解析に失敗しました: {e}")
        except Exception as e:
            raise ConfigInterfaceError(f"復元エラー: {e}")
    
    def list_recent_configurations(self, backup_dir: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        最近のバックアップ設定をリスト表示
        
        Args:
            backup_dir: バックアップディレクトリ
            limit: 最大件数
            
        Returns:
            List[Dict[str, Any]]: バックアップファイルのリスト
        """
        try:
            backup_path = Path(backup_dir)
            if not backup_path.exists():
                return []
            
            backup_files = []
            
            # バックアップファイルを検索
            for file_path in backup_path.glob("config_backup_*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    backup_files.append({
                        "file_path": str(file_path),
                        "timestamp": data.get("timestamp", ""),
                        "version": data.get("version", "unknown"),
                        "size": file_path.stat().st_size
                    })
                except Exception as e:
                    self.logger.warning(f"バックアップファイル読み込みエラー: {file_path}, {e}")
            
            # タイムスタンプでソート（新しい順）
            backup_files.sort(key=lambda x: x["timestamp"], reverse=True)
            
            return backup_files[:limit]
            
        except Exception as e:
            self.logger.error(f"バックアップリスト取得エラー: {e}")
            return []
    
    def reset_to_defaults(self, current_config: Config) -> Config:
        """
        設定をデフォルトにリセット
        
        Args:
            current_config: 現在の設定（参考用）
            
        Returns:
            Config: デフォルト設定
        """
        self.logger.info("設定をデフォルトにリセット")
        
        # 現在の選択フォルダは保持するかユーザーに確認が必要
        # ここでは新しいデフォルト設定を返す
        default_config = self.get_default_configuration()
        
        return default_config
    
    def load_configuration_with_env_override(self) -> Config:
        """
        環境変数で上書き可能な設定を読み込み
        
        Returns:
            Config: 環境変数で上書きされた設定
        """
        try:
            # 環境変数から設定を読み込み
            env_config = get_app_config()
            
            # Configオブジェクトに変換
            config = Config.from_dict(env_config)
            
            self.logger.info("環境変数統合設定を読み込み完了")
            return config
            
        except Exception as e:
            self.logger.warning(f"環境変数統合エラー、デフォルト設定を使用: {e}")
            return self.get_default_configuration()
    
    def migrate_configuration(self, old_config_data: Dict[str, Any], target_version: str) -> Dict[str, Any]:
        """
        設定データをマイグレーション
        
        Args:
            old_config_data: 古い設定データ
            target_version: 対象バージョン
            
        Returns:
            Dict[str, Any]: マイグレーション済み設定データ
        """
        self.logger.info(f"設定マイグレーション開始: target_version={target_version}")
        
        migrated_data = old_config_data.copy()
        
        # バージョン別マイグレーション処理
        if target_version == "1.0":
            # 0.9 -> 1.0 のマイグレーション
            
            # フィールド名の変更
            if "ollama_url" in migrated_data:
                migrated_data["ollama_host"] = migrated_data.pop("ollama_url")
            
            if "model" in migrated_data:
                migrated_data["ollama_model"] = migrated_data.pop("model")
            
            # 新しいフィールドのデフォルト値設定
            if "chroma_collection_name" not in migrated_data:
                migrated_data["chroma_collection_name"] = "knowledge_base"
            
            if "max_chat_history" not in migrated_data:
                migrated_data["max_chat_history"] = 50
        
        # バージョン情報を更新
        migrated_data["version"] = target_version
        
        self.logger.info("設定マイグレーション完了")
        return migrated_data
    
    def __str__(self) -> str:
        """ConfigInterfaceの文字列表現"""
        return f"ConfigInterface(default_file={self.default_config_file})"
    
    def __repr__(self) -> str:
        """ConfigInterfaceの詳細文字列表現"""
        return (
            f"ConfigInterface(default_config_file='{self.default_config_file}', "
            f"backup_directory='{self.backup_directory}')"
        )