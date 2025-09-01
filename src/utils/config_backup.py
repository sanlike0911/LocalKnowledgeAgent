"""
設定ファイル専用のバックアップ・復元機能
config.jsonの履歴管理と設定プロファイル機能
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging


@dataclass
class ConfigSnapshot:
    """設定スナップショット"""
    snapshot_id: str
    timestamp: datetime
    config_data: Dict[str, Any]
    description: str
    version: str = "1.0"


class ConfigBackupManager:
    """
    設定ファイル専用バックアップ管理クラス
    
    機能:
    - 設定変更前の自動スナップショット
    - 手動設定保存・復元
    - 設定プロファイル管理
    - 設定変更履歴追跡
    """
    
    def __init__(self, config_file_path: str, backup_dir: str = "./data/config_backups"):
        """
        設定バックアップマネージャーを初期化
        
        Args:
            config_file_path: メイン設定ファイルパス
            backup_dir: バックアップ保存ディレクトリ
        """
        self.config_file_path = Path(config_file_path)
        self.backup_dir = Path(backup_dir)
        self.snapshots_file = self.backup_dir / "config_snapshots.json"
        self.profiles_dir = self.backup_dir / "profiles"
        
        self.logger = logging.getLogger(__name__)
        
        # ディレクトリ作成
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"設定バックアップマネージャー初期化: {config_file_path}")
    
    def create_snapshot(self, description: str = "自動スナップショット") -> ConfigSnapshot:
        """
        現在の設定のスナップショットを作成
        
        Args:
            description: スナップショット説明
            
        Returns:
            ConfigSnapshot: 作成されたスナップショット
        """
        try:
            # 現在の設定を読み込み
            current_config = self._load_config(self.config_file_path)
            
            # スナップショットID生成
            timestamp = datetime.now()
            snapshot_id = f"snapshot_{timestamp.strftime('%Y%m%d_%H%M%S')}"
            
            # スナップショット作成
            snapshot = ConfigSnapshot(
                snapshot_id=snapshot_id,
                timestamp=timestamp,
                config_data=current_config,
                description=description
            )
            
            # スナップショット保存
            self._save_snapshot(snapshot)
            
            self.logger.info(f"設定スナップショット作成: {snapshot_id}")
            return snapshot
            
        except Exception as e:
            self.logger.error(f"スナップショット作成エラー: {e}")
            raise
    
    def restore_snapshot(self, snapshot_id: str) -> bool:
        """
        スナップショットから設定を復元
        
        Args:
            snapshot_id: 復元するスナップショットID
            
        Returns:
            bool: 復元成功フラグ
        """
        try:
            # 復元前にバックアップ
            self.create_snapshot("復元前の自動バックアップ")
            
            # スナップショット取得
            snapshots = self._load_snapshots()
            target_snapshot = None
            
            for snapshot in snapshots:
                if snapshot.snapshot_id == snapshot_id:
                    target_snapshot = snapshot
                    break
            
            if not target_snapshot:
                raise ValueError(f"スナップショットが見つかりません: {snapshot_id}")
            
            # 設定ファイル復元
            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                json.dump(target_snapshot.config_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"設定復元完了: {snapshot_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"設定復元エラー: {e}")
            return False
    
    def list_snapshots(self) -> List[ConfigSnapshot]:
        """
        利用可能なスナップショット一覧を取得
        
        Returns:
            List[ConfigSnapshot]: スナップショット一覧
        """
        snapshots = self._load_snapshots()
        return sorted(snapshots, key=lambda x: x.timestamp, reverse=True)
    
    def delete_snapshot(self, snapshot_id: str) -> bool:
        """
        スナップショットを削除
        
        Args:
            snapshot_id: 削除するスナップショットID
            
        Returns:
            bool: 削除成功フラグ
        """
        try:
            snapshots = self._load_snapshots()
            updated_snapshots = [s for s in snapshots if s.snapshot_id != snapshot_id]
            
            if len(snapshots) == len(updated_snapshots):
                self.logger.warning(f"削除対象スナップショットが見つかりません: {snapshot_id}")
                return False
            
            self._save_snapshots(updated_snapshots)
            self.logger.info(f"スナップショット削除完了: {snapshot_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"スナップショット削除エラー: {e}")
            return False
    
    def create_profile(self, profile_name: str, description: str = "") -> bool:
        """
        現在の設定からプロファイルを作成
        
        Args:
            profile_name: プロファイル名
            description: プロファイル説明
            
        Returns:
            bool: 作成成功フラグ
        """
        try:
            current_config = self._load_config(self.config_file_path)
            
            profile_data = {
                "name": profile_name,
                "description": description,
                "created_at": datetime.now().isoformat(),
                "config": current_config
            }
            
            profile_file = self.profiles_dir / f"{profile_name}.json"
            with open(profile_file, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"設定プロファイル作成: {profile_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"プロファイル作成エラー: {e}")
            return False
    
    def load_profile(self, profile_name: str) -> bool:
        """
        プロファイルから設定を読み込み
        
        Args:
            profile_name: プロファイル名
            
        Returns:
            bool: 読み込み成功フラグ
        """
        try:
            # 現在設定をバックアップ
            self.create_snapshot(f"プロファイル '{profile_name}' 適用前のバックアップ")
            
            profile_file = self.profiles_dir / f"{profile_name}.json"
            if not profile_file.exists():
                raise FileNotFoundError(f"プロファイルが見つかりません: {profile_name}")
            
            with open(profile_file, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)
            
            # 設定ファイル更新
            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                json.dump(profile_data["config"], f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"プロファイル適用完了: {profile_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"プロファイル読み込みエラー: {e}")
            return False
    
    def list_profiles(self) -> List[Dict[str, Any]]:
        """
        利用可能なプロファイル一覧を取得
        
        Returns:
            List[Dict]: プロファイル一覧
        """
        profiles = []
        
        for profile_file in self.profiles_dir.glob("*.json"):
            try:
                with open(profile_file, 'r', encoding='utf-8') as f:
                    profile_data = json.load(f)
                
                profiles.append({
                    "name": profile_data["name"],
                    "description": profile_data.get("description", ""),
                    "created_at": profile_data.get("created_at", ""),
                    "file_path": str(profile_file)
                })
                
            except Exception as e:
                self.logger.warning(f"プロファイル読み込み警告 {profile_file}: {e}")
        
        return sorted(profiles, key=lambda x: x["created_at"], reverse=True)
    
    def delete_profile(self, profile_name: str) -> bool:
        """
        プロファイルを削除
        
        Args:
            profile_name: プロファイル名
            
        Returns:
            bool: 削除成功フラグ
        """
        try:
            profile_file = self.profiles_dir / f"{profile_name}.json"
            
            if not profile_file.exists():
                self.logger.warning(f"削除対象プロファイルが見つかりません: {profile_name}")
                return False
            
            profile_file.unlink()
            self.logger.info(f"プロファイル削除完了: {profile_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"プロファイル削除エラー: {e}")
            return False
    
    def compare_snapshots(self, snapshot_id1: str, snapshot_id2: str) -> Dict[str, Any]:
        """
        2つのスナップショットを比較
        
        Args:
            snapshot_id1: 比較元スナップショットID
            snapshot_id2: 比較先スナップショットID
            
        Returns:
            Dict: 比較結果
        """
        snapshots = self._load_snapshots()
        snapshot1 = None
        snapshot2 = None
        
        for snapshot in snapshots:
            if snapshot.snapshot_id == snapshot_id1:
                snapshot1 = snapshot
            elif snapshot.snapshot_id == snapshot_id2:
                snapshot2 = snapshot
        
        if not snapshot1 or not snapshot2:
            return {"error": "指定されたスナップショットが見つかりません"}
        
        # 設定の差分を検出
        differences = self._find_config_differences(
            snapshot1.config_data,
            snapshot2.config_data
        )
        
        return {
            "snapshot1": {
                "id": snapshot1.snapshot_id,
                "timestamp": snapshot1.timestamp.isoformat(),
                "description": snapshot1.description
            },
            "snapshot2": {
                "id": snapshot2.snapshot_id,
                "timestamp": snapshot2.timestamp.isoformat(),
                "description": snapshot2.description
            },
            "differences": differences
        }
    
    def cleanup_old_snapshots(self, keep_count: int = 20) -> int:
        """
        古いスナップショットを削除
        
        Args:
            keep_count: 保持するスナップショット数
            
        Returns:
            int: 削除されたスナップショット数
        """
        try:
            snapshots = self.list_snapshots()
            
            if len(snapshots) <= keep_count:
                return 0
            
            snapshots_to_delete = snapshots[keep_count:]
            deleted_count = 0
            
            for snapshot in snapshots_to_delete:
                if self.delete_snapshot(snapshot.snapshot_id):
                    deleted_count += 1
            
            self.logger.info(f"古いスナップショット削除: {deleted_count}個")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"スナップショットクリーンアップエラー: {e}")
            return 0
    
    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """設定ファイルを読み込み"""
        if not config_path.exists():
            return {}
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_snapshot(self, snapshot: ConfigSnapshot) -> None:
        """スナップショットを保存"""
        snapshots = self._load_snapshots()
        snapshots.append(snapshot)
        self._save_snapshots(snapshots)
    
    def _load_snapshots(self) -> List[ConfigSnapshot]:
        """スナップショット一覧を読み込み"""
        if not self.snapshots_file.exists():
            return []
        
        try:
            with open(self.snapshots_file, 'r', encoding='utf-8') as f:
                snapshots_data = json.load(f)
            
            snapshots = []
            for data in snapshots_data:
                snapshots.append(ConfigSnapshot(
                    snapshot_id=data["snapshot_id"],
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    config_data=data["config_data"],
                    description=data["description"],
                    version=data.get("version", "1.0")
                ))
            
            return snapshots
            
        except Exception as e:
            self.logger.warning(f"スナップショット読み込み警告: {e}")
            return []
    
    def _save_snapshots(self, snapshots: List[ConfigSnapshot]) -> None:
        """スナップショット一覧を保存"""
        snapshots_data = []
        for snapshot in snapshots:
            snapshots_data.append({
                "snapshot_id": snapshot.snapshot_id,
                "timestamp": snapshot.timestamp.isoformat(),
                "config_data": snapshot.config_data,
                "description": snapshot.description,
                "version": snapshot.version
            })
        
        with open(self.snapshots_file, 'w', encoding='utf-8') as f:
            json.dump(snapshots_data, f, indent=2, ensure_ascii=False)
    
    def _find_config_differences(self, config1: Dict, config2: Dict, path: str = "") -> List[Dict]:
        """設定の差分を検出"""
        differences = []
        
        all_keys = set(config1.keys()) | set(config2.keys())
        
        for key in all_keys:
            current_path = f"{path}.{key}" if path else key
            
            if key not in config1:
                differences.append({
                    "type": "added",
                    "path": current_path,
                    "value": config2[key]
                })
            elif key not in config2:
                differences.append({
                    "type": "removed",
                    "path": current_path,
                    "value": config1[key]
                })
            elif config1[key] != config2[key]:
                if isinstance(config1[key], dict) and isinstance(config2[key], dict):
                    # ネストした辞書の場合は再帰的に比較
                    nested_diffs = self._find_config_differences(
                        config1[key], config2[key], current_path
                    )
                    differences.extend(nested_diffs)
                else:
                    differences.append({
                        "type": "modified",
                        "path": current_path,
                        "old_value": config1[key],
                        "new_value": config2[key]
                    })
        
        return differences