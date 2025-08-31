#!/usr/bin/env python3
"""
ChromaDB距離値デバッグテスト

ISSUE-018: 参考ソース表示で類似度が異常値（-20030.3%など）となる問題の調査
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from src.logic.indexing import ChromaDBIndexer
from src.logic.qa import RAGPipeline


def test_distance_values():
    """距離値の調査"""
    print("=" * 70)
    print("ISSUE-018: ChromaDB距離値デバッグテスト")
    print("=" * 70)
    
    try:
        # インデクサー初期化
        indexer = ChromaDBIndexer()
        print(f"✅ ChromaDBIndexer初期化成功")
        
        # テスト質問実行
        test_query = "代表取締役について"
        print(f"\n🔍 テスト質問: '{test_query}'")
        
        # 直接検索実行
        search_results = indexer.search_documents(test_query, top_k=3)
        print(f"\n📊 検索結果数: {len(search_results)}")
        
        # 距離値の詳細分析
        for i, result in enumerate(search_results, 1):
            distance = result.get('distance', None)
            metadata = result.get('metadata', {})
            
            print(f"\n--- 結果 {i} ---")
            print(f"メタデータ構造: {list(metadata.keys())}")
            print(f"メタデータ内容: {metadata}")
            
            # 正しいファイル名取得方法を試す
            filename = metadata.get('document_filename') or metadata.get('filename', '不明')
            
            print(f"ファイル名: {filename}")
            print(f"距離値: {distance}")
            print(f"距離値型: {type(distance)}")
            
            if distance is not None:
                # 類似度計算
                try:
                    similarity_percent = (1 - distance) * 100
                    print(f"類似度計算: (1 - {distance}) * 100 = {similarity_percent:.1f}%")
                    
                    # 距離値の範囲チェック
                    if distance < 0:
                        print(f"⚠️ 警告: 距離値が負の値です")
                    elif distance > 2:
                        print(f"⚠️ 警告: 距離値が予想範囲外です（>2）")
                    else:
                        print(f"✅ 距離値は正常範囲内です")
                        
                except Exception as e:
                    print(f"❌ 類似度計算エラー: {e}")
            
            content = result.get('content', '')[:50] + '...'
            print(f"内容プレビュー: {content}")
        
        # RAGパイプライン経由でのテスト
        print(f"\n" + "=" * 50)
        print("RAGパイプライン経由テスト")
        print("=" * 50)
        
        rag = RAGPipeline(indexer=indexer)
        qa_result = rag.answer_question(test_query)
        
        print(f"\n📋 QA結果のソース情報:")
        sources = qa_result.get('sources', [])
        for i, source in enumerate(sources, 1):
            # 修正: metadataから正しいファイル名を取得
            metadata = source.get('metadata', {})
            filename = metadata.get('document_filename') or source.get('filename', '不明')
            distance = source.get('distance', None)
            content_preview = source.get('content', '')[:50] + '...'
            
            print(f"\n--- ソース {i} ---")
            print(f"ファイル名: {filename}")
            print(f"距離値: {distance}")
            
            if distance is not None:
                similarity_percent = (1 - distance) * 100
                print(f"表示用類似度: {similarity_percent:.1f}%")
            
            print(f"内容プレビュー: {content_preview}")
        
        return True
        
    except Exception as e:
        print(f"❌ テスト中にエラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def debug_similarity_calculation():
    """類似度計算ロジックのデバッグ"""
    print(f"\n" + "=" * 50)
    print("類似度計算ロジックデバッグ")
    print("=" * 50)
    
    # 様々な距離値でのテスト
    test_distances = [0.0, 0.1, 0.5, 1.0, 1.5, 2.0, -0.1, -100.0, 200.3]
    
    for distance in test_distances:
        try:
            similarity = (1 - distance) * 100
            print(f"距離値: {distance:8.1f} → 類似度: {similarity:8.1f}%")
        except Exception as e:
            print(f"距離値: {distance:8.1f} → エラー: {e}")


if __name__ == "__main__":
    print("ChromaDB距離値・類似度表示デバッグテスト\n")
    
    # 距離値デバッグ
    debug_success = test_distance_values()
    
    # 類似度計算デバッグ
    debug_similarity_calculation()
    
    print(f"\n" + "=" * 70)
    print("テスト結果サマリー")
    print("=" * 70)
    
    if debug_success:
        print(f"✅ 距離値デバッグテスト成功")
        print(f"   距離値の異常を特定し、類似度表示問題の原因を調査しました。")
    else:
        print(f"❌ 距離値デバッグテスト失敗")
        print(f"   距離値の取得または処理でエラーが発生しました。")
    
    print(f"\n推奨対策:")
    print(f"1. 距離値の範囲チェック（0-2の範囲外を異常値として処理）")
    print(f"2. 異常値の場合のフォールバック処理実装")
    print(f"3. 距離値から類似度への変換ロジック改善")