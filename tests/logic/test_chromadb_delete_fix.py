#!/usr/bin/env python3
"""
ChromaDB インデックス削除機能の修正テスト

ISSUE-017: ChromaDB v1.0.17での空where条件削除エラーの修正確認
エラー: Expected where to have exactly one operator, got {} in delete.
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# プロジェクトルートをパスに追加
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.logic.indexing import ChromaDBIndexer
from src.exceptions.base_exceptions import IndexingError


class TestChromaDBDeleteFix(unittest.TestCase):
    """ChromaDBインデックス削除修正のテストクラス"""
    
    def setUp(self):
        """テストセットアップ"""
        with patch('src.logic.indexing.chromadb.PersistentClient'):
            with patch('src.logic.indexing.OllamaEmbeddings'):
                self.indexer = ChromaDBIndexer(
                    collection_name="test_collection",
                    db_path="./test_data/chroma_db"
                )
                # コレクションモックを設定
                self.mock_collection = Mock()
                self.indexer.collection = self.mock_collection
                self.indexer.client = Mock()
    
    def test_clear_collection_empty_collection(self):
        """空のコレクションのクリアテスト"""
        # モック設定：空のコレクション
        self.mock_collection.count.return_value = 0
        
        # テスト実行
        result = self.indexer.clear_collection()
        
        # 検証
        self.assertTrue(result)
        self.mock_collection.count.assert_called_once()
        # 空の場合は削除処理が実行されない
        self.mock_collection.delete.assert_not_called()
    
    def test_clear_collection_with_ids_success(self):
        """IDによる削除成功テスト"""
        # モック設定：3つのドキュメントが存在
        self.mock_collection.count.return_value = 3
        self.mock_collection.get.return_value = {
            'ids': ['doc1', 'doc2', 'doc3']
        }
        
        # テスト実行
        result = self.indexer.clear_collection()
        
        # 検証
        self.assertTrue(result)
        self.mock_collection.count.assert_called_once()
        self.mock_collection.get.assert_called_once()
        self.mock_collection.delete.assert_called_once_with(ids=['doc1', 'doc2', 'doc3'])
    
    def test_clear_collection_no_ids_found(self):
        """IDが見つからない場合のテスト"""
        # モック設定：ドキュメント数はあるがIDが取得できない
        self.mock_collection.count.return_value = 2
        self.mock_collection.get.return_value = {'ids': []}
        
        # テスト実行
        result = self.indexer.clear_collection()
        
        # 検証
        self.assertTrue(result)
        self.mock_collection.get.assert_called_once()
        # IDが空の場合は削除処理が実行されない
        self.mock_collection.delete.assert_not_called()
    
    def test_clear_collection_id_delete_fails_recreation_success(self):
        """ID削除失敗時のコレクション再作成テスト"""
        # モック設定
        self.mock_collection.count.return_value = 5
        self.mock_collection.get.return_value = {
            'ids': ['doc1', 'doc2', 'doc3', 'doc4', 'doc5']
        }
        # delete操作で例外を発生させる
        self.mock_collection.delete.side_effect = Exception("ID deletion failed")
        
        # クライアントモックの設定
        mock_new_collection = Mock()
        self.indexer.client.create_collection.return_value = mock_new_collection
        
        # テスト実行
        result = self.indexer.clear_collection()
        
        # 検証
        self.assertTrue(result)
        self.mock_collection.get.assert_called_once()
        self.mock_collection.delete.assert_called_once_with(ids=['doc1', 'doc2', 'doc3', 'doc4', 'doc5'])
        
        # コレクション再作成の検証
        self.indexer.client.delete_collection.assert_called_once_with(name="test_collection")
        self.indexer.client.create_collection.assert_called_once_with(
            name="test_collection",
            embedding_function=self.indexer._embedding_function,
            metadata={"hnsw:space": "cosine"}
        )
        # 新しいコレクションが設定されている
        self.assertEqual(self.indexer.collection, mock_new_collection)
    
    def test_clear_collection_complete_failure(self):
        """完全な削除失敗テスト"""
        # モック設定：count操作から失敗
        self.mock_collection.count.side_effect = Exception("Database connection failed")
        
        # テスト実行・検証
        with self.assertRaises(IndexingError) as context:
            self.indexer.clear_collection()
        
        # エラーコードの確認
        self.assertEqual(context.exception.error_code, "IDX-011")
        self.assertIn("Database connection failed", str(context.exception))
    
    def test_clear_collection_get_operation_fails(self):
        """get操作失敗時のコレクション再作成テスト"""
        # モック設定
        self.mock_collection.count.return_value = 3
        self.mock_collection.get.side_effect = Exception("Get operation failed")
        
        # クライアントモックの設定
        mock_new_collection = Mock()
        self.indexer.client.create_collection.return_value = mock_new_collection
        
        # テスト実行
        result = self.indexer.clear_collection()
        
        # 検証
        self.assertTrue(result)
        self.mock_collection.get.assert_called_once()
        
        # get操作が失敗した場合、コレクション再作成が実行される
        self.indexer.client.delete_collection.assert_called_once_with(name="test_collection")
        self.indexer.client.create_collection.assert_called_once()
    
    def test_clear_collection_recreation_fails(self):
        """コレクション再作成失敗テスト"""
        # モック設定
        self.mock_collection.count.return_value = 2
        self.mock_collection.get.return_value = {'ids': ['doc1', 'doc2']}
        self.mock_collection.delete.side_effect = Exception("ID deletion failed")
        
        # コレクション再作成も失敗
        self.indexer.client.delete_collection.side_effect = Exception("Recreation failed")
        
        # テスト実行・検証
        with self.assertRaises(IndexingError) as context:
            self.indexer.clear_collection()
        
        # エラーコードの確認
        self.assertEqual(context.exception.error_code, "IDX-011")
        self.assertIn("Recreation failed", str(context.exception))


def test_chromadb_delete_fix_comprehensive():
    """ChromaDB削除機能修正の包括的テスト"""
    print("=" * 70)
    print("ISSUE-017: ChromaDB v1.0.17 インデックス削除エラー修正テスト")
    print("=" * 70)
    
    try:
        # テストスイート実行
        suite = unittest.TestLoader().loadTestsFromTestCase(TestChromaDBDeleteFix)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        # 結果サマリー
        print(f"\n" + "=" * 70)
        print("テスト結果サマリー")
        print("=" * 70)
        print(f"実行テスト数: {result.testsRun}")
        print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
        print(f"失敗: {len(result.failures)}")
        print(f"エラー: {len(result.errors)}")
        
        if result.failures:
            print(f"\n失敗したテスト:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback}")
        
        if result.errors:
            print(f"\nエラーが発生したテスト:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback}")
        
        if result.wasSuccessful():
            print(f"\n✅ 全てのテストが成功しました！")
            print(f"   ChromaDB v1.0.17での削除機能修正が正常に動作しています。")
            return True
        else:
            print(f"\n❌ 一部のテストが失敗しました。")
            return False
            
    except Exception as e:
        print(f"❌ テスト実行中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_chromadb_delete_fix_comprehensive()
    sys.exit(0 if success else 1)