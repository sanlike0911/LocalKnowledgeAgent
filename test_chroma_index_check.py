#!/usr/bin/env python3
"""
ChromaDBインデックス状態確認テスト
ISSUE-013: QA-001エラー「関連する文書が見つかりません」の原因調査
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.logic.indexing import ChromaDBIndexer
from src.logic.config_manager import ConfigManager

def check_chroma_index_status():
    """ChromaDBインデックス状態を詳細確認"""
    
    print("🔍 ChromaDBインデックス状態確認")
    print("=" * 50)
    
    try:
        # ConfigManager から設定を読み込み
        print("\n1. 設定読み込み...")
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        print(f"   ✅ 設定読み込み完了")
        print(f"   - ChromaDB Path: {config.chroma_db_path}")
        print(f"   - Collection Name: {config.chroma_collection_name}")
        print(f"   - Selected Folders: {config.selected_folders}")
        print(f"   - Index Status: {config.index_status}")
        
        # ChromaDBIndexer初期化
        print("\n2. ChromaDBIndexer初期化...")
        indexer = ChromaDBIndexer(
            db_path=Path(config.chroma_db_path),
            collection_name=config.chroma_collection_name
        )
        print("   ✅ ChromaDBIndexer初期化完了")
        
        # コレクション情報取得
        print("\n3. ChromaDBコレクション情報取得...")
        try:
            collection = indexer._get_or_create_collection()
            count = collection.count()
            print(f"   ✅ コレクション取得成功")
            print(f"   - Collection Name: {collection.name}")
            print(f"   - Document Count: {count}")
            
            if count > 0:
                print(f"   📄 インデックス済みドキュメント: {count}件")
                # サンプルドキュメント取得
                try:
                    results = collection.peek(limit=3)
                    if results['documents']:
                        print(f"   📋 サンプルドキュメント:")
                        for i, doc in enumerate(results['documents'][:3]):
                            print(f"      {i+1}. {doc[:100]}...")
                except Exception as e:
                    print(f"   ⚠️  サンプル取得エラー: {e}")
            else:
                print(f"   ❌ インデックス済みドキュメントなし")
                print(f"   💡 これがQA-001エラーの原因です")
                
        except Exception as e:
            print(f"   ❌ コレクション情報取得エラー: {e}")
            return False
        
        # ファイル検索テスト
        print("\n4. ドキュメント検索テスト...")
        try:
            test_query = "代表取締役の宿泊費"
            results = indexer.search_documents(test_query, top_k=5)
            print(f"   🔍 検索クエリ: \"{test_query}\"")
            print(f"   📊 検索結果: {len(results)}件")
            
            if results:
                print(f"   ✅ 検索成功")
                for i, result in enumerate(results):
                    print(f"      {i+1}. Score: {result.get('score', 'N/A'):.3f}")
                    print(f"         Content: {result.get('content', 'N/A')[:100]}...")
            else:
                print(f"   ❌ 検索結果なし - QA-001エラーの原因確認")
                
        except Exception as e:
            print(f"   ❌ 検索テストエラー: {e}")
        
        return count > 0
        
    except Exception as e:
        print(f"❌ ChromaDBインデックス確認エラー: {e}")
        return False

def check_folder_files():
    """ragDataフォルダのファイル確認"""
    
    print("\n" + "=" * 50)
    print("🔍 ragDataフォルダファイル確認")
    print("=" * 50)
    
    try:
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        for folder_path in config.selected_folders:
            folder = Path(folder_path)
            print(f"\n📁 フォルダ: {folder}")
            
            if not folder.exists():
                print(f"   ❌ フォルダが存在しません")
                continue
            
            files = list(folder.rglob("*"))
            supported_files = []
            
            for file_path in files:
                if file_path.is_file():
                    if config.is_extension_supported(file_path.suffix):
                        supported_files.append(file_path)
                        print(f"   ✅ {file_path.name} ({file_path.suffix})")
                    else:
                        print(f"   ⚠️  {file_path.name} ({file_path.suffix}) - サポート外拡張子")
            
            print(f"\n   📊 総ファイル数: {len([f for f in files if f.is_file()])}件")
            print(f"   📊 サポート対象ファイル数: {len(supported_files)}件")
            
        return True
        
    except Exception as e:
        print(f"❌ フォルダファイル確認エラー: {e}")
        return False

def main():
    """メイン実行"""
    print("🚀 ISSUE-013: QA-001エラー原因調査")
    print("=" * 60)
    
    success_count = 0
    total_tests = 2
    
    # フォルダファイル確認
    if check_folder_files():
        success_count += 1
        print("\n✅ ragDataフォルダファイル確認: 成功")
    else:
        print("\n❌ ragDataフォルダファイル確認: 失敗")
    
    # ChromaDBインデックス確認
    has_index = check_chroma_index_status()
    if has_index:
        success_count += 1
        print("\n✅ ChromaDBインデックス確認: インデックス存在")
    else:
        print("\n❌ ChromaDBインデックス確認: インデックス不足")
    
    # 診断結果
    print("\n" + "=" * 60)
    print(f"🏁 診断結果: {success_count}/{total_tests}")
    
    if not has_index:
        print("\n🔧 **問題診断**:")
        print("   - ragDataフォルダは設定済み")
        print("   - ドキュメントファイルは存在")
        print("   - しかし ChromaDB にインデックスが作成されていない")
        print("   - index_status が 'not_created' のまま")
        
        print("\n💡 **解決方法**:")
        print("   1. 設定画面でインデックス作成ボタンを押す")
        print("   2. または手動でインデックス作成処理を実行する")
        print("   3. インデックス作成後に index_status を 'created' に更新")
        
        return False
    else:
        print("🎉 ChromaDBインデックスは正常です")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)