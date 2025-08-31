#!/usr/bin/env python3
"""
ISSUE-009具体的テスト: ドキュメント0件での「こんにちは」質問テスト
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.logic.qa import RAGPipeline, QAService
from src.logic.indexing import ChromaDBIndexer
from src.utils.structured_logger import get_logger

def test_issue_009():
    """ISSUE-009の具体的テスト: ドキュメント0件での「こんにちは」質問"""
    logger = get_logger(__name__)
    
    print("🔍 ISSUE-009 具体的テスト: ドキュメント0件での「こんにちは」質問")
    print("=" * 60)
    
    try:
        # 1. システム初期化
        print("\n1. システム初期化...")
        indexer = ChromaDBIndexer(
            db_path=Path("./data/chroma_db"),
            collection_name="test_knowledge_base"
        )
        
        qa_service = QAService(
            indexer=indexer,
            model_name="llama3:8b"
        )
        print("✅ システム初期化完了")
        
        # 2. 「こんにちは」質問テスト（修正前の問題を再現）
        print("\n2. 「こんにちは」質問テスト...")
        test_query = "こんにちは"
        
        try:
            result = qa_service.ask_question(test_query)
            
            print(f"✅ 質問応答成功!")
            print(f"質問: {result['query']}")
            print(f"回答: {result['answer'][:200]}...")
            print(f"ソース数: {len(result['sources'])}")
            print(f"処理時間: {result['processing_time']:.2f}秒")
            
            # ソース情報の詳細表示
            if result['sources']:
                print(f"📚 参考ソース: {len(result['sources'])}件")
                for i, source in enumerate(result['sources'][:3], 1):
                    print(f"  {i}. {source.get('filename', '不明')}")
            else:
                print("📝 ソース: なし（直接LLM回答モード）")
            
            return True
            
        except Exception as e:
            print(f"❌ 質問応答エラー: {e}")
            logger.error(f"質問応答エラー: {e}", exc_info=True)
            return False
        
    except Exception as e:
        print(f"❌ システム初期化エラー: {e}")
        logger.error(f"システム初期化エラー: {e}", exc_info=True)
        return False


def test_various_queries():
    """様々な質問での動作確認テスト"""
    logger = get_logger(__name__)
    
    print("\n" + "=" * 60)
    print("🔍 様々な質問での動作確認テスト")
    print("=" * 60)
    
    test_queries = [
        "こんにちは",
        "元気ですか？",
        "今日の天気はどうですか？",
        "プログラミングについて教えて",
        "ありがとうございました"
    ]
    
    try:
        # システム初期化
        indexer = ChromaDBIndexer(
            db_path=Path("./data/chroma_db"),
            collection_name="test_knowledge_base"
        )
        
        qa_service = QAService(
            indexer=indexer,
            model_name="llama3:8b"
        )
        
        success_count = 0
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n{i}. 質問: 「{query}」")
            
            try:
                result = qa_service.ask_question(query)
                print(f"   ✅ 回答: {result['answer'][:100]}...")
                print(f"   ⏱️  処理時間: {result['processing_time']:.2f}秒")
                success_count += 1
                
            except Exception as e:
                print(f"   ❌ エラー: {e}")
                logger.error(f"質問エラー ({query}): {e}", exc_info=True)
        
        print(f"\n📊 結果: {success_count}/{len(test_queries)} 成功")
        return success_count == len(test_queries)
        
    except Exception as e:
        print(f"❌ テスト初期化エラー: {e}")
        logger.error(f"テスト初期化エラー: {e}", exc_info=True)
        return False


def main():
    """メインテスト実行"""
    # ログレベルをINFOに設定
    import logging
    logging.getLogger().setLevel(logging.INFO)
    
    success_count = 0
    total_tests = 2
    
    # ISSUE-009具体的テスト
    if test_issue_009():
        success_count += 1
        print("\n✅ ISSUE-009具体的テスト: 成功")
    else:
        print("\n❌ ISSUE-009具体的テスト: 失敗")
    
    # 様々な質問テスト
    if test_various_queries():
        success_count += 1
        print("\n✅ 様々な質問テスト: 成功")
    else:
        print("\n❌ 様々な質問テスト: 失敗")
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print(f"🏁 最終結果: {success_count}/{total_tests} 成功")
    
    if success_count == total_tests:
        print("🎉 ISSUE-009 完全解決 - ドキュメント0件でも正常に動作します！")
        return True
    else:
        print("⚠️  ISSUE-009 部分的解決 - 一部問題が残っています")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)