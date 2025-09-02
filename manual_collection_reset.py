"""
ChromaDBコレクションの手動リセット
ファイルロック問題を回避して強制的にコレクションを初期化
"""

import sys
from pathlib import Path
import time

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.logic.indexing import ChromaDBIndexer
from src.logic.config_manager import ConfigManager
from src.utils.structured_logger import get_logger
import chromadb
from chromadb.config import Settings

def reset_collection_via_client():
    """ChromaDBクライアント経由でコレクションをリセット"""
    logger = get_logger(__name__)
    
    try:
        print("=== ChromaDBコレクションの手動リセット ===")
        
        # 設定を読み込み
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        print(f"ChromaDBパス: {config.chroma_db_path}")
        print(f"コレクション名: {config.chroma_collection_name}")
        print(f"埋め込みモデル: {config.embedding_model}")
        
        # ChromaDBクライアントを直接作成
        db_path = Path(config.chroma_db_path)
        db_path.mkdir(parents=True, exist_ok=True)
        
        client = chromadb.PersistentClient(
            path=str(db_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        print("ChromaDBクライアント接続成功")
        
        # 既存のコレクション一覧を取得
        collections = client.list_collections()
        print(f"既存コレクション数: {len(collections)}")
        
        for collection in collections:
            print(f"コレクション: {collection.name}")
            
        # 対象コレクションが存在する場合は削除
        collection_name = config.chroma_collection_name
        try:
            existing_collection = client.get_collection(collection_name)
            print(f"既存のコレクション '{collection_name}' を削除中...")
            client.delete_collection(collection_name)
            print(f"✅ コレクション '{collection_name}' 削除完了")
        except Exception:
            print(f"コレクション '{collection_name}' は存在しません")
            
        # ChromaDBクライアントを適切に終了
        client = None
        time.sleep(1)  # 少し待機
        
        print("新しいIndexerでコレクションを再作成中...")
        
        # 新しいIndexerを初期化して新しいコレクションを作成
        indexer = ChromaDBIndexer(
            db_path=config.chroma_db_path,
            collection_name=config.chroma_collection_name,
            embedding_model=config.embedding_model
        )
        
        print("✅ 新しいコレクション作成完了")
        
        # コレクション統計を確認
        stats = indexer.get_collection_stats()
        print(f"新しいコレクション統計: {stats}")
        
        # 次元数互換性チェック
        compatibility = indexer.check_embedding_dimension_compatibility()
        print("=== 新しいコレクションの互換性チェック結果 ===")
        for key, value in compatibility.items():
            print(f"{key}: {value}")
            
        if compatibility['is_compatible']:
            print("✅ 次元数互換性は正常です")
            
            # index_statusを"not_created"に更新
            config.index_status = "not_created"
            config_manager.save_config(config)
            print("✅ インデックス状態を'not_created'に更新しました")
            
            return True
        else:
            print("❌ まだ次元数互換性に問題があります")
            return False
            
    except Exception as e:
        print(f"❌ コレクションリセットエラー: {e}")
        logger.error(f"コレクションリセットエラー: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    print("=== 手動コレクションリセットスクリプト ===")
    success = reset_collection_via_client()
    
    if success:
        print("\n✅ コレクションリセット完了 - mxbai-embed-largeでのインデックス作成準備完了")
    else:
        print("\n❌ コレクションリセット失敗")