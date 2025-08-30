"""
設定管理システムのテストスイート (TDD Red フェーズ)
config.json操作・バリデーション・バックアップ機能のテストを定義
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, mock_open
from datetime import datetime

from src.models.config import Config
from src.exceptions.base_exceptions import ConfigError
from src.logic.config_manager import ConfigManager


class TestConfigManager:
    """ConfigManager クラスのテストスイート"""
    
    def setup_method(self):
        """各テスト前の初期化処理"""
        self.test_config_dir = Path(tempfile.mkdtemp())
        self.test_config_path = self.test_config_dir / "config.json"
        self.test_backup_dir = self.test_config_dir / "backups"
        
        self.config_manager = ConfigManager(
            config_path=str(self.test_config_path),
            backup_dir=str(self.test_backup_dir)
        )
    
    def teardown_method(self):
        """各テスト後のクリーンアップ処理"""
        if self.test_config_dir.exists():
            shutil.rmtree(self.test_config_dir)
    
    # 設定ファイル読み込みテスト
    
    def test_load_config_success(self):
        """設定ファイル読み込み成功テスト (Red フェーズ)"""
        # テスト用設定データを準備
        test_config_data = {
            "document_directories": ["/test/docs1", "/test/docs2"],
            "ollama_model": "llama3.1:8b",
            "ollama_base_url": "http://localhost:11434",
            "chroma_db_path": "./data/chroma_db",
            "max_search_results": 5,
            "enable_streaming": True,
            "ui_theme": "light",
            "language": "ja"
        }
        
        # 設定ファイルを作成
        self.test_config_path.write_text(json.dumps(test_config_data, indent=2))
        
        # 設定読み込み実行
        config = self.config_manager.load_config()
        
        # 検証
        assert isinstance(config, Config)
        assert config.document_directories == ["/test/docs1", "/test/docs2"]
        assert config.ollama_model == "llama3.1:8b"
        assert config.ollama_base_url == "http://localhost:11434"
        assert config.max_search_results == 5
        assert config.enable_streaming is True
    
    def test_load_config_file_not_found(self):
        """設定ファイル未存在テスト (Red フェーズ)"""
        # 設定ファイルが存在しない場合
        result = self.config_manager.load_config()
        
        # デフォルト設定が返されることを確認
        assert isinstance(result, Config)
        assert result.document_directories == []
        assert result.ollama_model == "llama3.1:8b"  # デフォルト値
        assert result.ollama_base_url == "http://localhost:11434"
    
    def test_load_config_invalid_json(self):
        """不正JSON読み込みテスト (Red フェーズ)"""
        # 不正なJSONファイルを作成
        self.test_config_path.write_text("{invalid json content")
        
        # ConfigError が発生することを期待
        with pytest.raises(ConfigError) as exc_info:
            self.config_manager.load_config()
        
        assert exc_info.value.error_code == "CFG-001"
        assert "設定ファイル解析エラー" in str(exc_info.value)
    
    def test_load_config_validation_error(self):
        """設定バリデーションエラーテスト (Red フェーズ)"""
        # バリデーション失敗する設定データ
        invalid_config = {
            "document_directories": "invalid_type",  # リストであるべき
            "max_search_results": -1,  # 正の値であるべき
            "ollama_base_url": "invalid_url"  # 有効なURLであるべき
        }
        
        self.test_config_path.write_text(json.dumps(invalid_config))
        
        with pytest.raises(ConfigError) as exc_info:
            self.config_manager.load_config()
        
        assert exc_info.value.error_code == "CFG-002"
        assert "設定バリデーションエラー" in str(exc_info.value)
    
    # 設定ファイル保存テスト
    
    def test_save_config_success(self):
        """設定ファイル保存成功テスト (Red フェーズ)"""
        # テスト設定を作成
        test_config = Config(
            document_directories=["/test/save1", "/test/save2"],
            ollama_model="codellama:7b",
            ollama_base_url="http://192.168.1.100:11434",
            max_search_results=10,
            enable_streaming=False
        )
        
        # 設定保存実行
        result = self.config_manager.save_config(test_config)
        
        # 保存成功確認
        assert result is True
        assert self.test_config_path.exists()
        
        # ファイル内容確認
        saved_data = json.loads(self.test_config_path.read_text())
        assert saved_data["document_directories"] == ["/test/save1", "/test/save2"]
        assert saved_data["ollama_model"] == "codellama:7b"
        assert saved_data["max_search_results"] == 10
    
    def test_save_config_directory_creation(self):
        """設定ディレクトリ自動作成テスト (Red フェーズ)"""
        # 深い階層の設定パス
        deep_config_path = self.test_config_dir / "deep" / "nested" / "config.json"
        manager = ConfigManager(config_path=str(deep_config_path))
        
        test_config = Config(document_directories=["/test"])
        
        # 保存実行（ディレクトリが自動作成されるはず）
        result = manager.save_config(test_config)
        
        assert result is True
        assert deep_config_path.exists()
        assert deep_config_path.parent.exists()
    
    def test_save_config_permission_error(self):
        """設定保存権限エラーテスト (Red フェーズ)"""
        test_config = Config(document_directories=["/test"])
        
        # ファイル作成時に権限エラーが発生する場合をモック
        with patch("pathlib.Path.write_text", side_effect=PermissionError("Permission denied")):
            with pytest.raises(ConfigError) as exc_info:
                self.config_manager.save_config(test_config)
            
            assert exc_info.value.error_code == "CFG-003"
            assert "設定ファイル保存エラー" in str(exc_info.value)
    
    # 設定更新テスト
    
    def test_update_config_partial(self):
        """部分設定更新テスト (Red フェーズ)"""
        # 初期設定を保存
        initial_config = Config(
            document_directories=["/initial/path"],
            ollama_model="llama3.1:8b",
            max_search_results=5
        )
        self.config_manager.save_config(initial_config)
        
        # 部分更新実行
        updates = {
            "document_directories": ["/updated/path1", "/updated/path2"],
            "max_search_results": 10
        }
        
        result = self.config_manager.update_config(updates)
        
        # 更新成功確認
        assert result is True
        
        # 更新後設定確認
        updated_config = self.config_manager.load_config()
        assert updated_config.document_directories == ["/updated/path1", "/updated/path2"]
        assert updated_config.max_search_results == 10
        assert updated_config.ollama_model == "llama3.1:8b"  # 未更新項目は維持
    
    def test_update_config_invalid_key(self):
        """無効キー更新エラーテスト (Red フェーズ)"""
        updates = {
            "invalid_key": "some_value",
            "another_invalid_key": 123
        }
        
        with pytest.raises(ConfigError) as exc_info:
            self.config_manager.update_config(updates)
        
        assert exc_info.value.error_code == "CFG-004"
        assert "無効な設定キー" in str(exc_info.value)
    
    def test_update_config_validation_failure(self):
        """設定更新バリデーション失敗テスト (Red フェーズ)"""
        updates = {
            "max_search_results": -5,  # 無効な値
            "ollama_base_url": "not_a_valid_url"
        }
        
        with pytest.raises(ConfigError) as exc_info:
            self.config_manager.update_config(updates)
        
        assert exc_info.value.error_code == "CFG-002"
        assert "設定バリデーションエラー" in str(exc_info.value)
    
    # バックアップ機能テスト
    
    def test_create_backup_success(self):
        """設定バックアップ作成成功テスト (Red フェーズ)"""
        # 設定ファイルを準備
        test_config = Config(document_directories=["/backup/test"])
        self.config_manager.save_config(test_config)
        
        # バックアップ作成
        backup_path = self.config_manager.create_backup()
        
        # バックアップ確認
        assert backup_path is not None
        assert Path(backup_path).exists()
        assert Path(backup_path).parent == self.test_backup_dir
        
        # バックアップファイル名確認（タイムスタンプ形式）
        backup_filename = Path(backup_path).name
        assert backup_filename.startswith("config_backup_")
        assert backup_filename.endswith(".json")
    
    def test_create_backup_no_config_file(self):
        """設定ファイル未存在時のバックアップテスト (Red フェーズ)"""
        # 設定ファイルが存在しない場合
        with pytest.raises(ConfigError) as exc_info:
            self.config_manager.create_backup()
        
        assert exc_info.value.error_code == "CFG-005"
        assert "バックアップ作成エラー" in str(exc_info.value)
    
    def test_restore_from_backup_success(self):
        """バックアップからの復元成功テスト (Red フェーズ)"""
        # 元の設定を作成・保存
        original_config = Config(
            document_directories=["/original/path"],
            ollama_model="original_model"
        )
        self.config_manager.save_config(original_config)
        
        # バックアップ作成
        backup_path = self.config_manager.create_backup()
        
        # 設定を変更
        modified_config = Config(
            document_directories=["/modified/path"],
            ollama_model="modified_model"
        )
        self.config_manager.save_config(modified_config)
        
        # バックアップから復元
        result = self.config_manager.restore_from_backup(backup_path)
        
        # 復元成功確認
        assert result is True
        
        # 復元後設定確認
        restored_config = self.config_manager.load_config()
        assert restored_config.document_directories == ["/original/path"]
        assert restored_config.ollama_model == "original_model"
    
    def test_restore_from_backup_invalid_file(self):
        """無効バックアップファイル復元テスト (Red フェーズ)"""
        # 存在しないバックアップファイル
        invalid_backup_path = str(self.test_backup_dir / "nonexistent_backup.json")
        
        with pytest.raises(ConfigError) as exc_info:
            self.config_manager.restore_from_backup(invalid_backup_path)
        
        assert exc_info.value.error_code == "CFG-006"
        assert "バックアップ復元エラー" in str(exc_info.value)
    
    def test_list_backups(self):
        """バックアップ一覧取得テスト (Red フェーズ)"""
        # 複数のバックアップを作成
        test_config = Config(document_directories=["/test"])
        self.config_manager.save_config(test_config)
        
        backup1 = self.config_manager.create_backup()
        backup2 = self.config_manager.create_backup()
        
        # バックアップ一覧取得
        backup_list = self.config_manager.list_backups()
        
        # 確認
        assert len(backup_list) == 2
        assert any(backup["path"] == backup1 for backup in backup_list)
        assert any(backup["path"] == backup2 for backup in backup_list)
        
        # 各バックアップエントリの形式確認
        for backup in backup_list:
            assert "path" in backup
            assert "created_at" in backup
            assert "size" in backup
    
    def test_cleanup_old_backups(self):
        """古いバックアップクリーンアップテスト (Red フェーズ)"""
        # 設定を準備
        test_config = Config(document_directories=["/test"])
        self.config_manager.save_config(test_config)
        
        # 複数のバックアップを作成（実際にはタイムスタンプが異なるファイルをモック）
        with patch('time.time', side_effect=[1000, 2000, 3000, 4000, 5000]):
            backup1 = self.config_manager.create_backup()
            backup2 = self.config_manager.create_backup()
            backup3 = self.config_manager.create_backup()
            backup4 = self.config_manager.create_backup()
            backup5 = self.config_manager.create_backup()
        
        # 最大3個まで保持するクリーンアップ実行
        cleaned_count = self.config_manager.cleanup_old_backups(max_backups=3)
        
        # クリーンアップ確認
        assert cleaned_count == 2  # 5個から3個に減少
        
        remaining_backups = self.config_manager.list_backups()
        assert len(remaining_backups) == 3
    
    # 設定検証テスト
    
    def test_validate_config_success(self):
        """設定検証成功テスト (Red フェーズ)"""
        valid_config_data = {
            "document_directories": ["/valid/path1", "/valid/path2"],
            "ollama_model": "llama3.1:8b",
            "ollama_base_url": "http://localhost:11434",
            "max_search_results": 10,
            "enable_streaming": True
        }
        
        # 検証実行
        result = self.config_manager.validate_config_data(valid_config_data)
        
        assert result is True
    
    def test_validate_config_required_fields(self):
        """必須フィールド検証テスト (Red フェーズ)"""
        # 必須フィールドが不足している設定
        incomplete_config = {
            "document_directories": ["/test"],
            # ollama_model が不足
            "max_search_results": 5
        }
        
        with pytest.raises(ConfigError) as exc_info:
            self.config_manager.validate_config_data(incomplete_config)
        
        assert exc_info.value.error_code == "CFG-007"
        assert "必須設定項目が不足" in str(exc_info.value)
    
    def test_validate_config_type_errors(self):
        """設定型エラー検証テスト (Red フェーズ)"""
        # 型が間違っている設定
        type_error_config = {
            "document_directories": "should_be_list",  # リストであるべき
            "ollama_model": 123,  # 文字列であるべき
            "max_search_results": "should_be_int",  # 整数であるべき
            "enable_streaming": "should_be_bool"  # ブールであるべき
        }
        
        with pytest.raises(ConfigError) as exc_info:
            self.config_manager.validate_config_data(type_error_config)
        
        assert exc_info.value.error_code == "CFG-008"
        assert "設定値の型エラー" in str(exc_info.value)
    
    def test_validate_config_value_ranges(self):
        """設定値範囲検証テスト (Red フェーズ)"""
        # 値の範囲が不正な設定
        range_error_config = {
            "document_directories": [],
            "ollama_model": "llama3.1:8b",
            "max_search_results": 0,  # 1以上であるべき
            "chunk_size": -100,  # 正の値であるべき
            "temperature": 5.0  # 0-2の範囲であるべき
        }
        
        with pytest.raises(ConfigError) as exc_info:
            self.config_manager.validate_config_data(range_error_config)
        
        assert exc_info.value.error_code == "CFG-009"
        assert "設定値の範囲エラー" in str(exc_info.value)
    
    # 設定マージ機能テスト
    
    def test_merge_configs(self):
        """設定マージテスト (Red フェーズ)"""
        base_config = Config(
            document_directories=["/base/path"],
            ollama_model="base_model",
            max_search_results=5,
            enable_streaming=True
        )
        
        override_config = Config(
            document_directories=["/override/path"],
            max_search_results=10
            # enable_streaming は上書きしない
        )
        
        merged_config = self.config_manager.merge_configs(base_config, override_config)
        
        # マージ結果確認
        assert merged_config.document_directories == ["/override/path"]
        assert merged_config.max_search_results == 10
        assert merged_config.enable_streaming is True  # ベースから継承
        assert merged_config.ollama_model == "base_model"  # ベースから継承
    
    def test_get_config_template(self):
        """設定テンプレート取得テスト (Red フェーズ)"""
        template = self.config_manager.get_config_template()
        
        # テンプレート構造確認
        assert isinstance(template, dict)
        assert "document_directories" in template
        assert "ollama_model" in template
        assert "ollama_base_url" in template
        assert "max_search_results" in template
        
        # デフォルト値確認
        assert template["document_directories"] == []
        assert template["ollama_model"] == "llama3.1:8b"
        assert template["ollama_base_url"] == "http://localhost:11434"
        assert template["max_search_results"] == 5


class TestConfigManagerIntegration:
    """ConfigManager 統合テスト"""
    
    def setup_method(self):
        """統合テスト用セットアップ"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.config_path = self.test_dir / "integration_config.json"
        self.backup_dir = self.test_dir / "integration_backups"
        
        self.manager = ConfigManager(
            config_path=str(self.config_path),
            backup_dir=str(self.backup_dir)
        )
    
    def teardown_method(self):
        """統合テスト後のクリーンアップ"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_full_config_lifecycle(self):
        """設定ライフサイクル統合テスト (Red フェーズ)"""
        # 1. 初期設定作成・保存
        initial_config = Config(
            document_directories=["/initial/docs"],
            ollama_model="llama3.1:8b",
            max_search_results=5
        )
        
        save_result = self.manager.save_config(initial_config)
        assert save_result is True
        
        # 2. 設定読み込み確認
        loaded_config = self.manager.load_config()
        assert loaded_config.document_directories == ["/initial/docs"]
        assert loaded_config.ollama_model == "llama3.1:8b"
        
        # 3. バックアップ作成
        backup_path = self.manager.create_backup()
        assert backup_path is not None
        
        # 4. 設定更新
        updates = {
            "document_directories": ["/updated/docs1", "/updated/docs2"],
            "max_search_results": 10
        }
        update_result = self.manager.update_config(updates)
        assert update_result is True
        
        # 5. 更新確認
        updated_config = self.manager.load_config()
        assert updated_config.document_directories == ["/updated/docs1", "/updated/docs2"]
        assert updated_config.max_search_results == 10
        assert updated_config.ollama_model == "llama3.1:8b"  # 継承確認
        
        # 6. バックアップから復元
        restore_result = self.manager.restore_from_backup(backup_path)
        assert restore_result is True
        
        # 7. 復元確認
        restored_config = self.manager.load_config()
        assert restored_config.document_directories == ["/initial/docs"]
        assert restored_config.max_search_results == 5
    
    def test_concurrent_config_operations(self):
        """並行設定操作テスト (Red フェーズ)"""
        # 複数の操作を並行実行する想定のテスト
        base_config = Config(
            document_directories=["/concurrent/test"],
            ollama_model="test_model"
        )
        
        # 保存とバックアップを連続実行
        self.manager.save_config(base_config)
        backup1 = self.manager.create_backup()
        
        # 設定変更
        self.manager.update_config({"max_search_results": 15})
        backup2 = self.manager.create_backup()
        
        # 両方のバックアップが有効であることを確認
        backup_list = self.manager.list_backups()
        assert len(backup_list) >= 2
        
        # 各バックアップから復元可能であることを確認
        self.manager.restore_from_backup(backup1)
        config1 = self.manager.load_config()
        assert config1.max_search_results == 5  # デフォルト値
        
        self.manager.restore_from_backup(backup2)
        config2 = self.manager.load_config()
        assert config2.max_search_results == 15  # 更新後の値