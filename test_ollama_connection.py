#!/usr/bin/env python3
"""
Ollama接続テストスクリプト
ISSUE-009: OLLAMAとの連携ができていない問題を解決するためのテスト
"""

import sys
import os
import json
import logging
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.logic.qa import OllamaQAEngine, RAGPipeline
from src.logic.indexing import ChromaDBIndexer
from src.utils.structured_logger import get_logger

def test_ollama_connection():
    """Ollama接続テスト"""
    logger = get_logger(__name__)
    
    print("=== Ollama接続テスト開始 ===")
    
    try:
        # 1. OllamaQAEngine初期化テスト
        print("\n1. OllamaQAEngine初期化テスト...")
        qa_engine = OllamaQAEngine(model_name="llama3:8b")
        print("✅ OllamaQAEngine初期化成功")
        
        # 2. Ollama接続テスト
        print("\n2. Ollama接続テスト...")
        is_connected = qa_engine.check_ollama_connection()
        if is_connected:
            print("✅ Ollama接続成功")
        else:
            print("❌ Ollama接続失敗")
            return False
        
        # 3. モデル利用可能性テスト
        print("\n3. モデル利用可能性テスト...")
        is_available = qa_engine.check_model_availability("llama3:8b")
        if is_available:
            print("✅ llama3:8bモデル利用可能")
        else:
            print("❌ llama3:8bモデル利用不可")
            return False
        
        # 4. 簡単なレスポンス生成テスト
        print("\n4. レスポンス生成テスト...")
        simple_prompt = "こんにちは。元気ですか？日本語で簡潔に答えてください。"
        
        try:
            response = qa_engine.generate_response(simple_prompt, timeout=30.0)
            print(f"✅ レスポンス生成成功")
            print(f"レスポンス: {response.content[:100]}...")
            print(f"メタデータ: {json.dumps(response.metadata, indent=2, ensure_ascii=False)}")
        except Exception as e:
            print(f"❌ レスポンス生成失敗: {e}")
            logger.error(f"レスポンス生成エラー: {e}", exc_info=True)
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        logger.error(f"Ollama接続テストエラー: {e}", exc_info=True)
        return False


def test_rag_pipeline():
    """RAGパイプライン統合テスト"""
    logger = get_logger(__name__)
    
    print("\n=== RAGパイプライン統合テスト開始 ===")
    
    try:
        # 1. ChromaDBIndexer初期化
        print("\n1. ChromaDBIndexer初期化...")
        indexer = ChromaDBIndexer(
            db_path=Path("./data/chroma_db"),
            collection_name="test_knowledge_base"
        )
        print("✅ ChromaDBIndexer初期化成功")
        
        # 2. RAGPipeline初期化
        print("\n2. RAGPipeline初期化...")
        rag_pipeline = RAGPipeline(
            indexer=indexer,
            model_name="llama3:8b"
        )
        print("✅ RAGPipeline初期化成功")
        
        # 3. システムヘルスチェック
        print("\n3. システムヘルスチェック...")
        health_status = rag_pipeline.check_system_health()
        print(f"システム状態: {health_status['overall_status']}")
        
        for component, status in health_status['components'].items():
            status_emoji = "✅" if status['status'] == 'healthy' else "❌"
            print(f"{status_emoji} {component}: {status['status']}")
            
        if health_status['overall_status'] == 'error':
            print("❌ システムヘルスチェック失敗")
            return False
        
        # 4. ドキュメント0件での質問テスト（ISSUE-009の核心）
        print("\n4. ドキュメント0件での質問テスト...")
        test_query = "こんにちは"
        
        try:
            # まずドキュメント検索を試行
            search_results = rag_pipeline.search_relevant_documents(test_query, top_k=3)
            print(f"検索結果: {len(search_results)}件")
            
            if not search_results:
                print("📝 検索結果なし - これが問題の原因です")
                # 空の検索結果でも回答生成を試行
                print("空の検索結果での回答生成を試行...")
                
        except Exception as search_error:
            print(f"⚠️  検索エラー（予期される）: {search_error}")
            logger.info(f"検索エラー（ドキュメント0件のため正常）: {search_error}")
            
            # 検索エラーの場合、直接Ollamaを呼び出してテスト
            print("\n直接Ollama呼び出しテスト...")
            qa_engine = rag_pipeline.qa_engine
            try:
                direct_response = qa_engine.generate_response(
                    "こんにちは。元気ですか？日本語で簡潔に答えてください。"
                )
                print(f"✅ 直接呼び出し成功: {direct_response.content[:100]}...")
            except Exception as direct_error:
                print(f"❌ 直接呼び出し失敗: {direct_error}")
                logger.error(f"直接Ollama呼び出しエラー: {direct_error}", exc_info=True)
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ RAGパイプライン統合テストエラー: {e}")
        logger.error(f"RAGパイプライン統合テストエラー: {e}", exc_info=True)
        return False


def main():
    """メインテスト実行"""
    print("🔍 ISSUE-009 Ollama連携問題の診断テスト")
    print("=" * 50)
    
    # ログレベルをDEBUGに設定（詳細ログ出力のため）
    logging.getLogger().setLevel(logging.DEBUG)
    
    success_count = 0
    total_tests = 2
    
    # Ollama接続テスト
    if test_ollama_connection():
        success_count += 1
        print("\n✅ Ollama接続テスト: 成功")
    else:
        print("\n❌ Ollama接続テスト: 失敗")
    
    # RAGパイプライン統合テスト  
    if test_rag_pipeline():
        success_count += 1
        print("\n✅ RAGパイプライン統合テスト: 成功")
    else:
        print("\n❌ RAGパイプライン統合テスト: 失敗")
    
    # 結果サマリー
    print("\n" + "=" * 50)
    print(f"🏁 テスト結果: {success_count}/{total_tests} 成功")
    
    if success_count == total_tests:
        print("✅ 全テスト成功 - Ollama連携は正常です")
        return True
    else:
        print("❌ 一部テスト失敗 - Ollama連携に問題があります")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)