"""
ConfigInterfaceのテストケース (TDD Red フェーズ)
CLAUDE.md準拠のTDD実装手順に従う
"""

import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch


class TestConfigInterface:
    """ConfigInterfaceのテストクラス"""
    
    def test_config_interface_load_configuration(self) -> None:
        """設定読み込み機能のテストケース"""
        from src.interfaces.config_interface import ConfigInterface
        from src.models.config import Config
        
        # テスト用設定ファイルを作成
        config_data = {
            "ollama_host": "http://test:11434",
            "ollama_model": "test-model",
            "selected_folders": ["/test/path"]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            import json
            json.dump(config_data, f)
            temp_file = f.name
        
        try:
            config_interface = ConfigInterface()
            loaded_config = config_interface.load_configuration(temp_file)
            
            assert isinstance(loaded_config, Config)
            assert loaded_config.ollama_host == "http://test:11434"
            assert loaded_config.ollama_model == "test-model"
            assert loaded_config.selected_folders == ["/test/path"]
            
        finally:
            Path(temp_file).unlink(missing_ok=True)
    
    def test_config_interface_save_configuration(self) -> None:
        """設定保存機能のテストケース"""
        from src.interfaces.config_interface import ConfigInterface
        from src.models.config import Config
        
        config_interface = ConfigInterface()
        
        # テスト用設定を作成
        config = Config(
            ollama_host="http://save-test:11434",
            ollama_model="save-model",
            selected_folders=["/save/test/path"]
        )
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            # 設定を保存
            result = config_interface.save_configuration(config, temp_file)
            assert result is True
            
            # ファイルが作成されたことを確認
            assert Path(temp_file).exists()
            
            # 保存された内容を確認
            import json
            with open(temp_file, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
            
            assert saved_data["ollama_host"] == "http://save-test:11434"
            assert saved_data["ollama_model"] == "save-model"
            assert saved_data["selected_folders"] == ["/save/test/path"]
            
        finally:
            Path(temp_file).unlink(missing_ok=True)
    
    def test_config_interface_get_default_configuration(self) -> None:
        """デフォルト設定取得のテストケース"""
        from src.interfaces.config_interface import ConfigInterface
        from src.models.config import Config
        
        config_interface = ConfigInterface()
        default_config = config_interface.get_default_configuration()
        
        assert isinstance(default_config, Config)
        assert default_config.ollama_host == "http://localhost:11434"
        assert default_config.ollama_model == "llama3:8b"
        assert default_config.chroma_collection_name == "knowledge_base"
        assert default_config.max_chat_history == 50
    
    def test_config_interface_validate_configuration(self) -> None:
        """設定検証機能のテストケース"""
        from src.interfaces.config_interface import ConfigInterface
        from src.models.config import Config
        
        config_interface = ConfigInterface()
        
        # 有効な設定
        valid_config = Config(
            ollama_host="http://valid:11434",
            ollama_model="valid-model",
            chroma_collection_name="valid_collection"
        )
        
        validation_result = config_interface.validate_configuration(valid_config)
        assert validation_result["is_valid"] is True
        assert len(validation_result["errors"]) == 0
        
        # 無効な設定
        invalid_config = Config(
            ollama_host="",  # 空のホスト
            ollama_model="valid-model",
            chroma_collection_name="valid_collection"
        )
        
        # 検証エラーが発生することを期待
        with pytest.raises(Exception):  # ConfigValidationErrorが発生
            config_interface.validate_configuration(invalid_config)
    
    def test_config_interface_merge_configurations(self) -> None:
        """設定マージ機能のテストケース"""
        from src.interfaces.config_interface import ConfigInterface
        from src.models.config import Config
        
        config_interface = ConfigInterface()
        
        # ベース設定
        base_config = Config(
            ollama_host="http://base:11434",
            ollama_model="base-model",
            max_chat_history=50
        )
        
        # 更新設定
        update_config = Config(
            ollama_host="http://updated:11434",
            # ollama_modelは更新しない
            max_chat_history=100
        )
        
        # 設定をマージ
        merged_config = config_interface.merge_configurations(base_config, update_config)
        
        assert merged_config.ollama_host == "http://updated:11434"  # 更新された
        assert merged_config.ollama_model == "base-model"  # ベース設定が保持
        assert merged_config.max_chat_history == 100  # 更新された
    
    def test_config_interface_export_configuration(self) -> None:
        """設定エクスポート機能のテストケース"""
        from src.interfaces.config_interface import ConfigInterface
        from src.models.config import Config
        
        config_interface = ConfigInterface()
        
        config = Config(
            ollama_host="http://export:11434",
            selected_folders=["/export/path1", "/export/path2"]
        )
        
        # 設定をエクスポート（辞書形式）
        exported_data = config_interface.export_configuration(config, format="dict")
        
        assert isinstance(exported_data, dict)
        assert exported_data["ollama_host"] == "http://export:11434"
        assert exported_data["selected_folders"] == ["/export/path1", "/export/path2"]
        
        # JSON形式でエクスポート
        json_data = config_interface.export_configuration(config, format="json")
        
        assert isinstance(json_data, str)
        
        # JSONをパース可能か確認
        import json
        parsed_data = json.loads(json_data)
        assert parsed_data["ollama_host"] == "http://export:11434"
    
    def test_config_interface_import_configuration(self) -> None:
        """設定インポート機能のテストケース"""
        from src.interfaces.config_interface import ConfigInterface
        from src.models.config import Config
        
        config_interface = ConfigInterface()
        
        # 辞書形式からインポート
        config_dict = {
            "ollama_host": "http://import:11434",
            "ollama_model": "import-model",
            "selected_folders": ["/import/path"]
        }
        
        imported_config = config_interface.import_configuration(config_dict, format="dict")
        
        assert isinstance(imported_config, Config)
        assert imported_config.ollama_host == "http://import:11434"
        assert imported_config.ollama_model == "import-model"
        assert imported_config.selected_folders == ["/import/path"]
        
        # JSON文字列からインポート
        import json
        json_string = json.dumps(config_dict)
        
        imported_from_json = config_interface.import_configuration(json_string, format="json")
        
        assert isinstance(imported_from_json, Config)
        assert imported_from_json.ollama_host == "http://import:11434"
    
    def test_config_interface_backup_configuration(self) -> None:
        """設定バックアップ機能のテストケース"""
        from src.interfaces.config_interface import ConfigInterface
        from src.models.config import Config
        
        config_interface = ConfigInterface()
        
        config = Config(
            ollama_host="http://backup:11434",
            selected_folders=["/backup/path"]
        )
        
        # バックアップディレクトリを作成
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_result = config_interface.backup_configuration(config, temp_dir)
            
            assert backup_result["success"] is True
            assert "backup_file" in backup_result
            assert Path(backup_result["backup_file"]).exists()
            
            # バックアップファイルの内容を確認
            import json
            with open(backup_result["backup_file"], 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            assert backup_data["ollama_host"] == "http://backup:11434"
            assert "timestamp" in backup_data
            assert "version" in backup_data
    
    def test_config_interface_restore_configuration(self) -> None:
        """設定復元機能のテストケース"""
        from src.interfaces.config_interface import ConfigInterface
        from src.models.config import Config
        
        config_interface = ConfigInterface()
        
        # バックアップファイルを作成
        backup_data = {
            "ollama_host": "http://restore:11434",
            "ollama_model": "restore-model",
            "selected_folders": ["/restore/path"],
            "timestamp": "2024-01-01T12:00:00",
            "version": "1.0"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            import json
            json.dump(backup_data, f)
            backup_file = f.name
        
        try:
            restored_config = config_interface.restore_configuration(backup_file)
            
            assert isinstance(restored_config, Config)
            assert restored_config.ollama_host == "http://restore:11434"
            assert restored_config.ollama_model == "restore-model"
            assert restored_config.selected_folders == ["/restore/path"]
            
        finally:
            Path(backup_file).unlink(missing_ok=True)
    
    def test_config_interface_list_recent_configurations(self) -> None:
        """最近の設定リスト取得のテストケース"""
        from src.interfaces.config_interface import ConfigInterface
        
        config_interface = ConfigInterface()
        
        # 複数のバックアップファイルを作成
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_files = []
            
            for i in range(3):
                backup_data = {
                    "ollama_host": f"http://recent{i}:11434",
                    "timestamp": f"2024-01-0{i+1}T12:00:00",
                    "version": "1.0"
                }
                
                backup_file = Path(temp_dir) / f"config_backup_{i}.json"
                with open(backup_file, 'w', encoding='utf-8') as f:
                    import json
                    json.dump(backup_data, f)
                backup_files.append(str(backup_file))
            
            # 最近の設定リストを取得
            recent_configs = config_interface.list_recent_configurations(temp_dir, limit=3)
            
            assert isinstance(recent_configs, list)
            assert len(recent_configs) <= 3
            assert all("file_path" in config for config in recent_configs)
            assert all("timestamp" in config for config in recent_configs)
    
    def test_config_interface_reset_to_defaults(self) -> None:
        """デフォルト設定リセット機能のテストケース"""
        from src.interfaces.config_interface import ConfigInterface
        from src.models.config import Config
        
        config_interface = ConfigInterface()
        
        # カスタム設定を作成
        custom_config = Config(
            ollama_host="http://custom:11434",
            ollama_model="custom-model",
            max_chat_history=200
        )
        
        # デフォルトにリセット
        reset_config = config_interface.reset_to_defaults(custom_config)
        
        assert isinstance(reset_config, Config)
        assert reset_config.ollama_host == "http://localhost:11434"  # デフォルト値
        assert reset_config.ollama_model == "llama3:8b"  # デフォルト値
        assert reset_config.max_chat_history == 50  # デフォルト値
    
    def test_config_interface_error_handling(self) -> None:
        """エラーハンドリングのテストケース"""
        from src.interfaces.config_interface import ConfigInterface, ConfigInterfaceError
        
        config_interface = ConfigInterface()
        
        # 存在しないファイルの読み込み
        with pytest.raises(ConfigInterfaceError, match="設定ファイルの読み込みに失敗しました"):
            config_interface.load_configuration("/nonexistent/path/config.json")
        
        # 不正なフォーマットでのインポート
        with pytest.raises(ConfigInterfaceError, match="不明な形式です"):
            config_interface.import_configuration({}, format="invalid_format")
    
    def test_config_interface_environment_integration(self) -> None:
        """環境変数統合のテストケース"""
        from src.interfaces.config_interface import ConfigInterface
        from src.models.config import Config
        
        config_interface = ConfigInterface()
        
        # 環境変数をモック
        env_vars = {
            "OLLAMA_HOST": "http://env:11434",
            "OLLAMA_MODEL": "env-model"
        }
        
        with patch.dict('os.environ', env_vars):
            config = config_interface.load_configuration_with_env_override()
            
            assert config.ollama_host == "http://env:11434"
            assert config.ollama_model == "env-model"
    
    def test_config_interface_configuration_migration(self) -> None:
        """設定マイグレーション機能のテストケース"""
        from src.interfaces.config_interface import ConfigInterface
        
        config_interface = ConfigInterface()
        
        # 古いバージョンの設定データ
        old_config_data = {
            "ollama_url": "http://old:11434",  # 古いフィールド名
            "model": "old-model",  # 古いフィールド名
            "version": "0.9"
        }
        
        # 設定をマイグレーション
        migrated_config = config_interface.migrate_configuration(old_config_data, "1.0")
        
        assert isinstance(migrated_config, dict)
        assert "ollama_host" in migrated_config  # 新しいフィールド名
        assert "ollama_model" in migrated_config  # 新しいフィールド名
        assert migrated_config["version"] == "1.0"