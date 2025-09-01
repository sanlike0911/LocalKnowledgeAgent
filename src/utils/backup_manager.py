"""
ChromaDBバックアップ管理ユーティリティ
データベースと設定ファイルの定期的なバックアップを提供
"""

import os
import json
import shutil
import zipfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging


@dataclass
class BackupInfo:
    """バックアップ情報"""
    backup_path: str
    timestamp: datetime
    backup_type: str  # 'full', 'incremental'
    file_count: int
    size_bytes: int
    status: str  # 'success', 'partial', 'failed'
    error_message: Optional[str] = None


class BackupManager:
    """
    ChromaDBと設定ファイルのバックアップ管理クラス
    
    機能:
    - ChromaDBデータベース全体のバックアップ
    - 設定ファイルのバックアップ
    - 世代管理（古いバックアップの自動削除）
    - 増分バックアップサポート
    """
    
    def __init__(
        self,
        backup_dir: str = "./backups",
        max_backups: int = 10,
        retention_days: int = 30
    ):
        """
        バックアップマネージャーを初期化
        
        Args:
            backup_dir: バックアップ保存ディレクトリ
            max_backups: 保持する最大バックアップ数
            retention_days: バックアップ保持日数
        """
        self.backup_dir = Path(backup_dir)
        self.max_backups = max_backups
        self.retention_days = retention_days
        self.logger = logging.getLogger(__name__)
        
        # バックアップディレクトリ作成
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # バックアップ情報ファイル
        self.backup_info_file = self.backup_dir / "backup_info.json"
        
        self.logger.info(f"バックアップマネージャー初期化完了: {backup_dir}")
    
    def create_backup(
        self,
        chroma_db_path: str,
        config_file_path: str,
        backup_type: str = "full"
    ) -> BackupInfo:
        """
        バックアップを作成
        
        Args:
            chroma_db_path: ChromaDBデータベースパス
            config_file_path: 設定ファイルパス
            backup_type: バックアップタイプ ('full' または 'incremental')
            
        Returns:
            BackupInfo: バックアップ情報
        """
        timestamp = datetime.now()
        backup_name = f"backup_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        backup_path = self.backup_dir / f"{backup_name}.zip"
        
        try:
            self.logger.info(f"バックアップ作成開始: {backup_name}")
            
            file_count = 0
            size_bytes = 0
            
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # ChromaDBバックアップ
                if Path(chroma_db_path).exists():
                    db_files = self._get_database_files(chroma_db_path)
                    for file_path in db_files:
                        if Path(file_path).exists():
                            arcname = f"chroma_db/{Path(file_path).relative_to(chroma_db_path)}"
                            zipf.write(file_path, arcname)
                            file_count += 1
                            size_bytes += Path(file_path).stat().st_size
                
                # 設定ファイルバックアップ
                if Path(config_file_path).exists():
                    zipf.write(config_file_path, "config.json")
                    file_count += 1
                    size_bytes += Path(config_file_path).stat().st_size
                
                # メタデータ追加
                metadata = {
                    "backup_type": backup_type,
                    "timestamp": timestamp.isoformat(),
                    "chroma_db_path": chroma_db_path,
                    "config_file_path": config_file_path,
                    "file_count": file_count,
                    "size_bytes": size_bytes
                }
                
                zipf.writestr("backup_metadata.json", json.dumps(metadata, indent=2))
            
            backup_info = BackupInfo(
                backup_path=str(backup_path),
                timestamp=timestamp,
                backup_type=backup_type,
                file_count=file_count,
                size_bytes=size_bytes,
                status="success"
            )
            
            # バックアップ情報を記録
            self._save_backup_info(backup_info)
            
            # 古いバックアップをクリーンアップ
            self._cleanup_old_backups()
            
            self.logger.info(f"バックアップ作成成功: {backup_name} ({file_count}ファイル, {size_bytes}バイト)")
            return backup_info
            
        except Exception as e:
            error_msg = f"バックアップ作成エラー: {e}"
            self.logger.error(error_msg)
            
            # 失敗した場合は部分的なバックアップファイルを削除
            if backup_path.exists():
                backup_path.unlink()
            
            return BackupInfo(
                backup_path=str(backup_path),
                timestamp=timestamp,
                backup_type=backup_type,
                file_count=0,
                size_bytes=0,
                status="failed",
                error_message=error_msg
            )
    
    def restore_backup(
        self,
        backup_path: str,
        target_chroma_db_path: str,
        target_config_path: str
    ) -> bool:
        """
        バックアップから復元
        
        Args:
            backup_path: バックアップファイルパス
            target_chroma_db_path: 復元先ChromaDBパス
            target_config_path: 復元先設定ファイルパス
            
        Returns:
            bool: 復元成功フラグ
        """
        try:
            self.logger.info(f"バックアップ復元開始: {backup_path}")
            
            backup_path = Path(backup_path)
            if not backup_path.exists():
                raise FileNotFoundError(f"バックアップファイルが見つかりません: {backup_path}")
            
            # 既存データをバックアップ
            self._backup_existing_data(target_chroma_db_path, target_config_path)
            
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                # メタデータ確認
                if "backup_metadata.json" in zipf.namelist():
                    metadata_content = zipf.read("backup_metadata.json")
                    metadata = json.loads(metadata_content.decode())
                    self.logger.info(f"復元対象: {metadata.get('backup_type')} バックアップ")
                
                # ChromaDB復元
                target_db_dir = Path(target_chroma_db_path)
                if target_db_dir.exists():
                    shutil.rmtree(target_db_dir)
                target_db_dir.mkdir(parents=True, exist_ok=True)
                
                for file_path in zipf.namelist():
                    if file_path.startswith("chroma_db/"):
                        extract_path = target_db_dir / Path(file_path).relative_to("chroma_db")
                        extract_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        with zipf.open(file_path) as source, open(extract_path, 'wb') as target:
                            shutil.copyfileobj(source, target)
                
                # 設定ファイル復元
                if "config.json" in zipf.namelist():
                    config_content = zipf.read("config.json")
                    target_config = Path(target_config_path)
                    target_config.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(target_config, 'wb') as f:
                        f.write(config_content)
            
            self.logger.info(f"バックアップ復元成功: {backup_path}")
            return True
            
        except Exception as e:
            error_msg = f"バックアップ復元エラー: {e}"
            self.logger.error(error_msg)
            return False
    
    def list_backups(self) -> List[BackupInfo]:
        """
        利用可能なバックアップ一覧を取得
        
        Returns:
            List[BackupInfo]: バックアップ情報リスト
        """
        backup_info = self._load_backup_info()
        return sorted(backup_info, key=lambda x: x.timestamp, reverse=True)
    
    def get_backup_status(self) -> Dict:
        """
        バックアップシステムの状態を取得
        
        Returns:
            Dict: バックアップ状態情報
        """
        backups = self.list_backups()
        
        total_size = sum(backup.size_bytes for backup in backups)
        successful_backups = [b for b in backups if b.status == "success"]
        failed_backups = [b for b in backups if b.status == "failed"]
        
        latest_backup = backups[0] if backups else None
        
        return {
            "total_backups": len(backups),
            "successful_backups": len(successful_backups),
            "failed_backups": len(failed_backups),
            "total_size_bytes": total_size,
            "total_size_human": self._format_size(total_size),
            "latest_backup": {
                "timestamp": latest_backup.timestamp.isoformat() if latest_backup else None,
                "status": latest_backup.status if latest_backup else None,
                "size": self._format_size(latest_backup.size_bytes) if latest_backup else None
            } if latest_backup else None,
            "backup_dir": str(self.backup_dir),
            "max_backups": self.max_backups,
            "retention_days": self.retention_days
        }
    
    def _get_database_files(self, db_path: str) -> List[str]:
        """データベースファイル一覧を取得"""
        db_path = Path(db_path)
        if not db_path.exists():
            return []
        
        db_files = []
        for root, dirs, files in os.walk(db_path):
            for file in files:
                file_path = Path(root) / file
                db_files.append(str(file_path))
        
        return db_files
    
    def _save_backup_info(self, backup_info: BackupInfo) -> None:
        """バックアップ情報を保存"""
        existing_info = self._load_backup_info()
        existing_info.append(backup_info)
        
        # JSON形式で保存
        backup_data = []
        for info in existing_info:
            backup_data.append({
                "backup_path": info.backup_path,
                "timestamp": info.timestamp.isoformat(),
                "backup_type": info.backup_type,
                "file_count": info.file_count,
                "size_bytes": info.size_bytes,
                "status": info.status,
                "error_message": info.error_message
            })
        
        with open(self.backup_info_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
    
    def _load_backup_info(self) -> List[BackupInfo]:
        """バックアップ情報を読み込み"""
        if not self.backup_info_file.exists():
            return []
        
        try:
            with open(self.backup_info_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            backup_info = []
            for data in backup_data:
                backup_info.append(BackupInfo(
                    backup_path=data["backup_path"],
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    backup_type=data["backup_type"],
                    file_count=data["file_count"],
                    size_bytes=data["size_bytes"],
                    status=data["status"],
                    error_message=data.get("error_message")
                ))
            
            return backup_info
            
        except Exception as e:
            self.logger.warning(f"バックアップ情報読み込みエラー: {e}")
            return []
    
    def _cleanup_old_backups(self) -> None:
        """古いバックアップを削除"""
        backups = self.list_backups()
        
        # 最大数制限
        if len(backups) > self.max_backups:
            old_backups = backups[self.max_backups:]
            for backup in old_backups:
                self._delete_backup(backup)
        
        # 保持期間制限
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        expired_backups = [b for b in backups if b.timestamp < cutoff_date]
        
        for backup in expired_backups:
            self._delete_backup(backup)
    
    def _delete_backup(self, backup_info: BackupInfo) -> None:
        """バックアップを削除"""
        try:
            backup_path = Path(backup_info.backup_path)
            if backup_path.exists():
                backup_path.unlink()
                self.logger.info(f"古いバックアップを削除: {backup_path.name}")
                
                # バックアップ情報からも削除
                existing_info = self._load_backup_info()
                existing_info = [b for b in existing_info if b.backup_path != backup_info.backup_path]
                
                # 更新されたリストを保存
                backup_data = []
                for info in existing_info:
                    backup_data.append({
                        "backup_path": info.backup_path,
                        "timestamp": info.timestamp.isoformat(),
                        "backup_type": info.backup_type,
                        "file_count": info.file_count,
                        "size_bytes": info.size_bytes,
                        "status": info.status,
                        "error_message": info.error_message
                    })
                
                with open(self.backup_info_file, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, indent=2, ensure_ascii=False)
                    
        except Exception as e:
            self.logger.error(f"バックアップ削除エラー: {e}")
    
    def _backup_existing_data(self, chroma_db_path: str, config_path: str) -> None:
        """復元前に既存データをバックアップ"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            temp_backup_name = f"temp_backup_before_restore_{timestamp}.zip"
            temp_backup_path = self.backup_dir / temp_backup_name
            
            with zipfile.ZipFile(temp_backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 既存ChromaDBバックアップ
                if Path(chroma_db_path).exists():
                    db_files = self._get_database_files(chroma_db_path)
                    for file_path in db_files:
                        if Path(file_path).exists():
                            arcname = f"chroma_db/{Path(file_path).relative_to(chroma_db_path)}"
                            zipf.write(file_path, arcname)
                
                # 既存設定ファイルバックアップ
                if Path(config_path).exists():
                    zipf.write(config_path, "config.json")
                
            self.logger.info(f"復元前バックアップ作成: {temp_backup_name}")
            
        except Exception as e:
            self.logger.warning(f"復元前バックアップ作成エラー: {e}")
    
    def _format_size(self, size_bytes: int) -> str:
        """バイト数を人間が読みやすい形式に変換"""
        if size_bytes == 0:
            return "0 B"
        
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(size_bytes)
        unit_index = 0
        
        while size >= 1024.0 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1
        
        return f"{size:.1f} {units[unit_index]}"


def create_scheduled_backup(
    chroma_db_path: str,
    config_file_path: str,
    backup_dir: str = "./backups"
) -> BackupInfo:
    """
    定期バックアップの便利関数
    
    Args:
        chroma_db_path: ChromaDBパス
        config_file_path: 設定ファイルパス
        backup_dir: バックアップディレクトリ
        
    Returns:
        BackupInfo: バックアップ結果
    """
    backup_manager = BackupManager(backup_dir=backup_dir)
    return backup_manager.create_backup(
        chroma_db_path=chroma_db_path,
        config_file_path=config_file_path,
        backup_type="full"
    )


def get_backup_recommendations(backup_status: Dict) -> List[str]:
    """
    バックアップ状況に基づく推奨事項を生成
    
    Args:
        backup_status: バックアップ状態情報
        
    Returns:
        List[str]: 推奨事項リスト
    """
    recommendations = []
    
    if backup_status["total_backups"] == 0:
        recommendations.append("⚠️ バックアップが作成されていません。定期バックアップを設定してください。")
    
    if backup_status["failed_backups"] > 0:
        recommendations.append(f"❌ {backup_status['failed_backups']}個の失敗したバックアップがあります。")
    
    if backup_status["latest_backup"] and backup_status["latest_backup"]["timestamp"]:
        latest_time = datetime.fromisoformat(backup_status["latest_backup"]["timestamp"])
        days_ago = (datetime.now() - latest_time).days
        
        if days_ago > 7:
            recommendations.append(f"⏰ 最新のバックアップが{days_ago}日前です。バックアップを実行してください。")
        elif days_ago > 3:
            recommendations.append(f"📅 最新のバックアップが{days_ago}日前です。近日中にバックアップを実行することを推奨します。")
    
    if backup_status["total_size_bytes"] > 5 * 1024 * 1024 * 1024:  # 5GB
        recommendations.append("💾 バックアップサイズが大きくなっています。古いバックアップの削除を検討してください。")
    
    if not recommendations:
        recommendations.append("✅ バックアップシステムは正常に動作しています。")
    
    return recommendations