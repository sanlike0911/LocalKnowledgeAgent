"""
設定管理システム実装 (TDD Green フェーズ)
config.json操作・バックアップ・バリデーション機能を提供
"""

import json
import logging
import shutil
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from dataclasses import asdict

from src.models.config import Config
from src.exceptions.base_exceptions import ConfigError
from src.utils.structured_logger import get_logger
from src.utils.cancellation_utils import CancellableOperation


class ConfigManager(CancellableOperation):
    """
    設定管理クラス
    
    config.json の読み書き・バックアップ・バリデーション機能を提供
    """
    
    def __init__(
        self,
        config_path: str = "./data/config.json",
        backup_dir: str = "./data/backups",
        max_backups: int = 10
    ):
        """
        設定管理を初期化
        
        Args:
            config_path: 設定ファイルパス
            backup_dir: バックアップディレクトリ
            max_backups: 最大バックアップ数
        """
        super().__init__("Config Manager")
        
        self.config_path = Path(config_path)
        self.backup_dir = Path(backup_dir)
        self.max_backups = max_backups
        self.logger = get_logger(__name__)
        
        # ディレクトリを作成
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 設定テンプレート（Config モデルに合わせて修正）
        self.config_template = {
            "ollama_host": "http://localhost:11434",
            "ollama_model": "llama3:8b",
            "chroma_db_path": "./data/chroma_db",
            "chroma_collection_name": "knowledge_base",
            "max_chat_history": 50,
            "max_file_size_mb": 50,
            "supported_extensions": [".pdf", ".txt", ".docx"],
            "selected_folders": [],
            "index_status": "not_created",
            "app_debug": False,
            "log_level": "INFO",
            "upload_folder": "./uploads",
            "temp_folder": "./temp"
        }
        
        # バリデーションルール（Config モデルに合わせて修正）
        self.validation_rules = {
            "selected_folders": {"type": list, "required": False},
            "ollama_model": {"type": str, "required": True, "min_length": 1},
            "ollama_host": {"type": str, "required": True, "pattern": r"^https?://"},
            "chroma_db_path": {"type": str, "required": True, "min_length": 1},
            "chroma_collection_name": {"type": str, "required": True, "min_length": 1},
            "max_chat_history": {"type": int, "required": True, "min": 1, "max": 1000},
            "max_file_size_mb": {"type": int, "required": True, "min": 1, "max": 1000},
            "supported_extensions": {"type": list, "required": False},
            "index_status": {"type": str, "required": True, "choices": ["not_created", "creating", "created", "error"]},
            "app_debug": {"type": bool, "required": False},
            "log_level": {"type": str, "required": False, "choices": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]},
            "upload_folder": {"type": str, "required": False, "min_length": 1},
            "temp_folder": {"type": str, "required": False, "min_length": 1}
        }
        
        self.logger.info(f"ConfigManager初期化完了", extra={
            "config_path": str(self.config_path),
            "backup_dir": str(self.backup_dir),
            "max_backups": max_backups
        })
    
    def load_config(self) -> Config:
        """
        設定ファイルを読み込み
        
        Returns:
            Config: 読み込まれた設定オブジェクト
            
        Raises:
            ConfigError: 設定読み込みエラー
        """
        try:
            self.check_cancellation()
            
            if not self.config_path.exists():
                self.logger.info(f"設定ファイルが存在しません。デフォルト設定を使用: {self.config_path}")
                return Config()
            
            # 設定ファイル読み込み
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # バリデーション実行
            self.validate_config_data(config_data)
            
            # Configオブジェクトに変換
            config = Config.from_dict(config_data)
            
            self.logger.info(f"設定ファイル読み込み完了", extra={
                "config_path": str(self.config_path),
                "selected_folders_count": len(config.selected_folders)
            })
            
            return config
            
        except json.JSONDecodeError as e:
            raise ConfigError(
                f"設定ファイル解析エラー: {self.config_path} - {e}",
                error_code="CFG-001",
                details={"config_path": str(self.config_path), "json_error": str(e)}
            ) from e
        except ConfigError:
            raise
        except Exception as e:
            raise ConfigError(
                f"設定ファイル読み込みエラー: {self.config_path} - {e}",
                error_code="CFG-010",
                details={"config_path": str(self.config_path), "original_error": str(e)}
            ) from e
    
    def save_config(self, config: Config) -> bool:
        """
        設定をファイルに保存
        
        Args:
            config: 保存する設定オブジェクト
            
        Returns:
            bool: 保存成功フラグ
            
        Raises:
            ConfigError: 設定保存エラー
        """
        try:
            self.check_cancellation()
            
            # Configオブジェクトを辞書に変換
            config_data = config.to_dict()
            
            # バリデーション実行
            self.validate_config_data(config_data)
            
            # ディレクトリが存在しない場合は作成
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 一時ファイルに書き込み後、原子的に置換
            temp_path = self.config_path.with_suffix('.tmp')
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            # 原子的ファイル置換
            temp_path.replace(self.config_path)
            
            self.logger.info(f"設定ファイル保存完了", extra={
                "config_path": str(self.config_path),
                "selected_folders_count": len(config.selected_folders)
            })
            
            return True
            
        except ConfigError:
            raise
        except (OSError, PermissionError) as e:
            raise ConfigError(
                f"設定ファイル保存エラー: {self.config_path} - {e}",
                error_code="CFG-003",
                details={"config_path": str(self.config_path), "original_error": str(e)}
            ) from e
        except Exception as e:
            raise ConfigError(
                f"設定保存処理エラー: {e}",
                error_code="CFG-011",
                details={"config_path": str(self.config_path), "original_error": str(e)}
            ) from e
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """
        設定を部分的に更新
        
        Args:
            updates: 更新する設定項目の辞書
            
        Returns:
            bool: 更新成功フラグ
            
        Raises:
            ConfigError: 設定更新エラー
        """
        try:
            self.check_cancellation()
            
            # 無効なキーをチェック
            invalid_keys = set(updates.keys()) - set(self.config_template.keys())
            if invalid_keys:
                raise ConfigError(
                    f"無効な設定キー: {list(invalid_keys)}",
                    error_code="CFG-004",
                    details={"invalid_keys": list(invalid_keys), "valid_keys": list(self.config_template.keys())}
                )
            
            # 現在の設定を読み込み
            current_config = self.load_config()
            current_data = current_config.to_dict()
            
            # 更新を適用
            current_data.update(updates)
            
            # バリデーション実行
            self.validate_config_data(current_data)
            
            # 更新された設定を保存
            updated_config = Config.from_dict(current_data)
            result = self.save_config(updated_config)
            
            self.logger.info(f"設定部分更新完了", extra={
                "updated_keys": list(updates.keys()),
                "updates_count": len(updates)
            })
            
            return result
            
        except ConfigError:
            raise
        except Exception as e:
            raise ConfigError(
                f"設定更新エラー: {e}",
                error_code="CFG-012",
                details={"updates": updates, "original_error": str(e)}
            ) from e
    
    def validate_config_data(self, config_data: Dict[str, Any]) -> bool:
        """
        設定データのバリデーション
        
        Args:
            config_data: 検証する設定データ
            
        Returns:
            bool: バリデーション成功フラグ
            
        Raises:
            ConfigError: バリデーションエラー
        """
        try:
            # 必須項目チェック
            required_fields = [
                key for key, rules in self.validation_rules.items()
                if rules.get("required", False)
            ]
            
            missing_fields = set(required_fields) - set(config_data.keys())
            if missing_fields:
                raise ConfigError(
                    f"必須設定項目が不足: {list(missing_fields)}",
                    error_code="CFG-007",
                    details={"missing_fields": list(missing_fields)}
                )
            
            # 各フィールドの型・値チェック
            for key, value in config_data.items():
                if key not in self.validation_rules:
                    continue
                
                rules = self.validation_rules[key]
                
                # 型チェック
                expected_type = rules["type"]
                if not isinstance(value, expected_type):
                    raise ConfigError(
                        f"設定値の型エラー: {key}={value} (期待型: {expected_type.__name__ if hasattr(expected_type, '__name__') else str(expected_type)})",
                        error_code="CFG-008",
                        details={"field": key, "value": value, "expected_type": str(expected_type)}
                    )
                
                # 文字列の最小長チェック
                if isinstance(value, str) and "min_length" in rules:
                    if len(value) < rules["min_length"]:
                        raise ConfigError(
                            f"設定値の長さエラー: {key}の長さが{rules['min_length']}文字未満",
                            error_code="CFG-009",
                            details={"field": key, "value": value, "min_length": rules["min_length"]}
                        )
                
                # 数値の範囲チェック
                if isinstance(value, (int, float)):
                    if "min" in rules and value < rules["min"]:
                        raise ConfigError(
                            f"設定値の範囲エラー: {key}={value} (最小値: {rules['min']})",
                            error_code="CFG-009",
                            details={"field": key, "value": value, "min": rules["min"]}
                        )
                    
                    if "max" in rules and value > rules["max"]:
                        raise ConfigError(
                            f"設定値の範囲エラー: {key}={value} (最大値: {rules['max']})",
                            error_code="CFG-009",
                            details={"field": key, "value": value, "max": rules["max"]}
                        )
                
                # 選択肢チェック
                if "choices" in rules and value not in rules["choices"]:
                    raise ConfigError(
                        f"設定値の選択肢エラー: {key}={value} (選択肢: {rules['choices']})",
                        error_code="CFG-009",
                        details={"field": key, "value": value, "choices": rules["choices"]}
                    )
                
                # URLパターンチェック
                if "pattern" in rules and isinstance(value, str):
                    import re
                    if not re.match(rules["pattern"], value):
                        raise ConfigError(
                            f"設定値のパターンエラー: {key}={value}",
                            error_code="CFG-009",
                            details={"field": key, "value": value, "pattern": rules["pattern"]}
                        )
            
            return True
            
        except ConfigError:
            raise
        except Exception as e:
            raise ConfigError(
                f"設定バリデーションエラー: {e}",
                error_code="CFG-002",
                details={"config_data": config_data, "original_error": str(e)}
            ) from e
    
    def create_backup(self) -> str:
        """
        設定ファイルのバックアップを作成
        
        Returns:
            str: 作成されたバックアップファイルのパス
            
        Raises:
            ConfigError: バックアップ作成エラー
        """
        try:
            self.check_cancellation()
            
            if not self.config_path.exists():
                raise ConfigError(
                    f"バックアップ作成エラー: 設定ファイルが存在しません - {self.config_path}",
                    error_code="CFG-005",
                    details={"config_path": str(self.config_path)}
                )
            
            # バックアップファイル名を生成（タイムスタンプ付き）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"config_backup_{timestamp}.json"
            backup_path = self.backup_dir / backup_filename
            
            # バックアップディレクトリを作成
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            # ファイルをコピー
            shutil.copy2(self.config_path, backup_path)
            
            self.logger.info(f"設定バックアップ作成完了", extra={
                "backup_path": str(backup_path),
                "original_path": str(self.config_path)
            })
            
            # 古いバックアップをクリーンアップ
            self.cleanup_old_backups()
            
            return str(backup_path)
            
        except ConfigError:
            raise
        except Exception as e:
            raise ConfigError(
                f"バックアップ作成エラー: {e}",
                error_code="CFG-005",
                details={"config_path": str(self.config_path), "original_error": str(e)}
            ) from e
    
    def restore_from_backup(self, backup_path: str) -> bool:
        """
        バックアップから設定を復元
        
        Args:
            backup_path: 復元するバックアップファイルのパス
            
        Returns:
            bool: 復元成功フラグ
            
        Raises:
            ConfigError: バックアップ復元エラー
        """
        try:
            self.check_cancellation()
            
            backup_file = Path(backup_path)
            
            if not backup_file.exists():
                raise ConfigError(
                    f"バックアップ復元エラー: バックアップファイルが存在しません - {backup_path}",
                    error_code="CFG-006",
                    details={"backup_path": backup_path}
                )
            
            # バックアップファイルの妥当性を確認
            try:
                with open(backup_file, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
                self.validate_config_data(backup_data)
            except Exception as e:
                raise ConfigError(
                    f"バックアップファイルが無効です: {backup_path} - {e}",
                    error_code="CFG-006",
                    details={"backup_path": backup_path, "validation_error": str(e)}
                ) from e
            
            # 現在の設定ファイルのバックアップを作成（復元前の安全策）
            if self.config_path.exists():
                safety_backup = self.create_backup()
                self.logger.info(f"復元前の安全バックアップ作成: {safety_backup}")
            
            # バックアップファイルから復元
            shutil.copy2(backup_file, self.config_path)
            
            self.logger.info(f"設定バックアップ復元完了", extra={
                "backup_path": backup_path,
                "config_path": str(self.config_path)
            })
            
            return True
            
        except ConfigError:
            raise
        except Exception as e:
            raise ConfigError(
                f"バックアップ復元エラー: {e}",
                error_code="CFG-006",
                details={"backup_path": backup_path, "original_error": str(e)}
            ) from e
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        利用可能なバックアップ一覧を取得
        
        Returns:
            List[Dict[str, Any]]: バックアップ情報のリスト
        """
        try:
            backups = []
            
            if not self.backup_dir.exists():
                return backups
            
            # バックアップファイルを検索
            for backup_file in self.backup_dir.glob("config_backup_*.json"):
                try:
                    stat = backup_file.stat()
                    backups.append({
                        "path": str(backup_file),
                        "filename": backup_file.name,
                        "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "size": stat.st_size
                    })
                except Exception as e:
                    self.logger.warning(f"バックアップファイル情報取得エラー: {backup_file} - {e}")
                    continue
            
            # 作成日時の降順でソート
            backups.sort(key=lambda x: x["created_at"], reverse=True)
            
            return backups
            
        except Exception as e:
            self.logger.error(f"バックアップ一覧取得エラー: {e}")
            return []
    
    def cleanup_old_backups(self, max_backups: Optional[int] = None) -> int:
        """
        古いバックアップファイルをクリーンアップ
        
        Args:
            max_backups: 保持する最大バックアップ数（未指定時はデフォルト）
            
        Returns:
            int: 削除されたバックアップ数
        """
        try:
            max_count = max_backups or self.max_backups
            backups = self.list_backups()
            
            if len(backups) <= max_count:
                return 0
            
            # 古いバックアップを削除
            backups_to_delete = backups[max_count:]
            deleted_count = 0
            
            for backup in backups_to_delete:
                try:
                    Path(backup["path"]).unlink()
                    deleted_count += 1
                except Exception as e:
                    self.logger.warning(f"バックアップ削除エラー: {backup['path']} - {e}")
            
            if deleted_count > 0:
                self.logger.info(f"古いバックアップをクリーンアップ: {deleted_count}件削除")
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"バックアップクリーンアップエラー: {e}")
            return 0
    
    def merge_configs(self, base_config: Config, override_config: Config) -> Config:
        """
        2つの設定をマージ
        
        Args:
            base_config: ベース設定
            override_config: 上書き設定
            
        Returns:
            Config: マージされた設定
        """
        try:
            # 両方を辞書に変換
            base_data = base_config.to_dict()
            override_data = override_config.to_dict()
            
            # 上書き設定で更新（Noneでない値のみ）
            merged_data = base_data.copy()
            for key, value in override_data.items():
                if value is not None:
                    merged_data[key] = value
            
            # マージされた設定を返す
            return Config.from_dict(merged_data)
            
        except Exception as e:
            self.logger.error(f"設定マージエラー: {e}")
            return base_config
    
    def get_config_template(self) -> Dict[str, Any]:
        """
        設定テンプレートを取得
        
        Returns:
            Dict[str, Any]: 設定テンプレート
        """
        return self.config_template.copy()
    
    def reset_to_defaults(self) -> bool:
        """
        設定をデフォルト値にリセット
        
        Returns:
            bool: リセット成功フラグ
        """
        try:
            self.check_cancellation()
            
            # 現在の設定をバックアップ
            if self.config_path.exists():
                backup_path = self.create_backup()
                self.logger.info(f"リセット前バックアップ作成: {backup_path}")
            
            # デフォルト設定を作成・保存
            default_config = Config()
            result = self.save_config(default_config)
            
            self.logger.info("設定をデフォルト値にリセット完了")
            return result
            
        except Exception as e:
            self.logger.error(f"設定リセットエラー: {e}")
            return False
    
    def export_config(self, export_path: str) -> bool:
        """
        設定を指定パスにエクスポート
        
        Args:
            export_path: エクスポート先パス
            
        Returns:
            bool: エクスポート成功フラグ
        """
        try:
            self.check_cancellation()
            
            if not self.config_path.exists():
                return False
            
            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(self.config_path, export_file)
            
            self.logger.info(f"設定エクスポート完了: {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"設定エクスポートエラー: {e}")
            return False
    
    def import_config(self, import_path: str) -> bool:
        """
        指定パスから設定をインポート
        
        Args:
            import_path: インポート元パス
            
        Returns:
            bool: インポート成功フラグ
        """
        try:
            self.check_cancellation()
            
            import_file = Path(import_path)
            if not import_file.exists():
                return False
            
            # インポートファイルを検証
            with open(import_file, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            self.validate_config_data(import_data)
            
            # 現在の設定をバックアップ
            if self.config_path.exists():
                backup_path = self.create_backup()
                self.logger.info(f"インポート前バックアップ作成: {backup_path}")
            
            # 設定をインポート
            shutil.copy2(import_file, self.config_path)
            
            self.logger.info(f"設定インポート完了: {import_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"設定インポートエラー: {e}")
            return False
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        設定サマリ情報を取得
        
        Returns:
            Dict[str, Any]: 設定サマリ
        """
        try:
            config = self.load_config()
            backups = self.list_backups()
            
            return {
                "config_exists": self.config_path.exists(),
                "config_path": str(self.config_path),
                "last_modified": datetime.fromtimestamp(
                    self.config_path.stat().st_mtime
                ).isoformat() if self.config_path.exists() else None,
                "selected_folders_count": len(config.selected_folders),
                "ollama_model": config.ollama_model,
                "backup_count": len(backups),
                "last_backup": backups[0]["created_at"] if backups else None
            }
            
        except Exception as e:
            self.logger.error(f"設定サマリ取得エラー: {e}")
            return {
                "config_exists": False,
                "error": str(e)
            }