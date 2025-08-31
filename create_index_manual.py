#!/usr/bin/env python3
"""
手動インデックス作成スクリプト
ISSUE-013: QA-001エラー解決のため、ragDataフォルダのドキュメントをChromaDBにインデックス
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def create_index_manually():
    """手動でインデックスを作成"""
    
    print("🚀 手動インデックス作成開始")
    print("=" * 50)
    
    try:
        from src.logic.config_manager import ConfigManager
        from src.logic.indexing import ChromaDBIndexer
        
        # 1. 設定読み込み
        print("\n1. 設定読み込み...")
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        print(f"   ✅ 設定読み込み完了")
        print(f"   - Selected Folders: {config.selected_folders}")
        print(f"   - Index Status: {config.index_status}")
        
        # 2. ChromaDBIndexer初期化
        print("\n2. ChromaDBIndexer初期化...")
        indexer = ChromaDBIndexer(
            db_path=Path(config.chroma_db_path),
            collection_name=config.chroma_collection_name
        )
        print("   ✅ ChromaDBIndexer初期化完了")
        
        # 3. ファイル確認
        print("\n3. インデックス対象ファイル確認...")
        all_files = []
        for folder_path in config.selected_folders:
            folder = Path(folder_path)
            if folder.exists():
                files = list(folder.rglob("*"))
                for file_path in files:
                    if file_path.is_file() and config.is_extension_supported(file_path.suffix):
                        all_files.append(file_path)
                        print(f"   📄 {file_path.name} ({file_path.suffix})")
        
        print(f"\n   📊 インデックス対象ファイル数: {len(all_files)}件")
        
        if not all_files:
            print("   ⚠️  インデックス対象ファイルがありません")
            return False
        
        # 4. インデックス作成
        print("\n4. インデックス作成実行...")
        
        # index_status を creating に更新
        config.index_status = "creating"
        config_manager.save_config(config)
        print("   📝 インデックス状態を 'creating' に更新")
        
        try:
            # フォルダをインデックス作成
            for folder_path in config.selected_folders:
                print(f"   🗂️  フォルダ処理中: {folder_path}")
                indexer.index_folder(Path(folder_path))
            
            # インデックス作成完了
            config.index_status = "created"
            config_manager.save_config(config)
            print("   ✅ インデックス作成完了")
            print("   📝 インデックス状態を 'created' に更新")
            
        except Exception as e:
            # インデックス作成失敗
            config.index_status = "error"
            config_manager.save_config(config)
            print(f"   ❌ インデックス作成エラー: {e}")
            print("   📝 インデックス状態を 'error' に更新")
            return False
        
        # 5. 動作確認テスト
        print("\n5. インデックス動作確認テスト...")
        try:
            test_query = "代表取締役の宿泊費"
            results = indexer.search_documents(test_query, top_k=3)
            print(f"   🔍 テストクエリ: \"{test_query}\"")
            print(f"   📊 検索結果: {len(results)}件")
            
            if results:
                print("   ✅ 検索テスト成功")
                for i, result in enumerate(results[:2]):
                    print(f"      {i+1}. Content: {result.get('content', '')[:80]}...")
                return True
            else:
                print("   ❌ 検索結果なし")
                return False
                
        except Exception as e:
            print(f"   ❌ 検索テストエラー: {e}")
            return False
        
    except ImportError as e:
        print(f"❌ モジュールインポートエラー: {e}")
        print("💡 依存関係が不足している可能性があります")
        print("   以下のコマンドで依存関係をインストールしてください:")
        print("   pip3 install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ インデックス作成エラー: {e}")
        return False

def main():
    """メイン実行"""
    print("🔧 ISSUE-013解決: 手動インデックス作成")
    print("=" * 60)
    
    if create_index_manually():
        print("\n🎉 インデックス作成完了!")
        print("💡 これで QA-001 エラーは解決されるはずです")
        print("📝 チャットで「代表取締役の宿泊費を教えて」と質問してテストしてください")
        return True
    else:
        print("\n❌ インデックス作成失敗")
        print("⚠️  依存関係の問題またはファイルアクセス問題が原因の可能性があります")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)