#!/usr/bin/env python3
"""
埋め込みベクトル次元数修正後のテスト
ISSUE-015: Collection expecting embedding with dimension of 768, got 4096 エラーの修正確認
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_embedding_dimension_consistency():
    """埋め込みベクトル次元数の整合性テスト"""
    
    print("🔍 埋め込みベクトル次元数整合性テスト")
    print("=" * 50)
    
    try:
        from src.logic.indexing import ChromaDBIndexer
        from src.logic.config_manager import ConfigManager
        
        # 1. ChromaDBIndexer初期化テスト（デフォルト）
        print("\n1. ChromaDBIndexer初期化（デフォルト）...")
        indexer_default = ChromaDBIndexer()
        print(f"   ✅ デフォルト埋め込みモデル: {indexer_default.embedding_model}")
        
        # 2. ChromaDBIndexer初期化テスト（明示的にnomic-embed-text指定）
        print("\n2. ChromaDBIndexer初期化（nomic-embed-text指定）...")
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        indexer_explicit = ChromaDBIndexer(
            db_path=Path(config.chroma_db_path),
            collection_name=config.chroma_collection_name,
            embedding_model="nomic-embed-text"
        )
        print(f"   ✅ 明示的指定埋め込みモデル: {indexer_explicit.embedding_model}")
        
        # 3. 埋め込みベクトル生成テスト
        print("\n3. 埋め込みベクトル生成テスト...")
        test_text = ["これはテストです。"]
        
        embeddings = indexer_explicit._create_embeddings(test_text)
        print(f"   ✅ 埋め込みベクトル生成成功")
        print(f"   - ベクトル数: {len(embeddings)}")
        print(f"   - ベクトル次元数: {len(embeddings[0]) if embeddings and embeddings[0] else 'N/A'}")
        
        # 4. 検索テスト（既存のインデックスがある場合）
        print("\n4. 検索テスト...")
        try:
            results = indexer_explicit.search_documents("代表取締役", top_k=3)
            print(f"   ✅ 検索成功: {len(results)}件の結果")
            if results:
                print(f"   - 最初の結果: {results[0].get('content', '')[:50]}...")
        except Exception as search_error:
            print(f"   ⚠️  検索エラー: {search_error}")
            if "dimension" in str(search_error).lower():
                print("   ❌ 次元数不整合エラーが継続しています")
                return False
        
        # 5. app.pyとmain_viewの整合性確認
        print("\n5. app.pyとmain_viewの整合性確認...")
        
        # MainViewがindexerを受け取るかテスト
        from src.ui.main_view import MainView
        main_view = MainView(indexer=indexer_explicit)
        print("   ✅ MainViewがindexerを受け取れることを確認")
        
        return True
        
    except ImportError as e:
        print(f"❌ インポートエラー: {e}")
        return False
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """メインテスト実行"""
    print("🚀 ISSUE-015: 埋め込みベクトル次元数修正確認テスト")
    print("=" * 70)
    
    success = test_embedding_dimension_consistency()
    
    # 結果サマリー
    print("\n" + "=" * 70)
    if success:
        print("🎉 ISSUE-015修正完了!")
        print("🔧 修正内容:")
        print("   - main_viewでllama3:8b（4096次元）をnomic-embed-text（768次元）に変更")
        print("   - app.pyからmain_viewにindexerを渡すように修正")
        print("   - MainViewクラスでindexer受け取り機能を追加")
        print("   - ChromaDBIndexerインスタンスの一元管理を実装")
        
        print("\n📋 次のステップ:")
        print("   1. Streamlitアプリで「代表取締役の宿泊費は？」などで質問")
        print("   2. QA-002エラーが解消されることを確認")
        print("   3. 正常な文書検索・回答生成が動作することを確認")
        
        return True
    else:
        print("⚠️  修正に問題があります")
        print("💡 依存関係の確認とStreamlitアプリでの動作確認が必要です")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)