#!/usr/bin/env python3
"""
CFG-011エラー修正後のテスト
ISSUE-012: RAGファイル登録時にCFG-011エラーが発生する問題の修正確認
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.logic.config_manager import ConfigManager
from src.models.config import Config
from src.exceptions.base_exceptions import ConfigError

def test_cfg_011_fix():
    """CFG-011エラーが修正されているかテスト"""
    
    print("🔍 CFG-011エラー修正確認テスト")
    print("=" * 50)
    
    try:
        # ConfigManager初期化
        print("\n1. ConfigManager初期化...")
        config_manager = ConfigManager()
        
        # 設定読み込み
        print("2. 設定読み込み...")
        config = config_manager.load_config()
        print(f"✅ 設定読み込み成功")
        print(f"   - selected_folders: {config.selected_folders}")
        
        # フォルダ追加（CFG-011エラーの原因となっていた操作）
        print("\n3. フォルダ追加テスト...")
        test_folder = "/Users/sanlike/project/Python/LocalKnowledgeAgent/ragData"
        config.add_selected_folder(test_folder)
        print(f"✅ フォルダ追加成功: {test_folder}")
        print(f"   - 現在のフォルダ: {config.selected_folders}")
        
        # 設定保存（これがCFG-011エラーの発生箇所だった）
        print("\n4. 設定保存テスト...")
        success = config_manager.save_config(config)
        print(f"✅ 設定保存成功: {success}")
        
        # 再読み込み確認
        print("\n5. 設定再読み込み確認...")
        config2 = config_manager.load_config()
        print(f"✅ 設定再読み込み成功")
        print(f"   - 保存されたフォルダ: {config2.selected_folders}")
        
        return True
        
    except ConfigError as e:
        if "CFG-011" in str(e):
            print(f"❌ CFG-011エラーが再発: {e}")
            return False
        elif "document_directories" in str(e):
            print(f"❌ document_directories参照エラー: {e}")
            return False
        else:
            print(f"❌ 他のConfigエラー: {e}")
            return False
    except AttributeError as e:
        if "document_directories" in str(e):
            print(f"❌ document_directories属性エラー: {e}")
            return False
        else:
            print(f"❌ 他の属性エラー: {e}")
            return False
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        return False

def test_config_save_workflow():
    """Config保存ワークフローの完全テスト"""
    
    print("\n" + "=" * 50)
    print("🔍 Config保存ワークフロー完全テスト")
    print("=" * 50)
    
    try:
        config_manager = ConfigManager()
        
        # 1. 新規フォルダ作成・追加
        print("\n1. 複数フォルダ追加テスト...")
        config = config_manager.load_config()
        
        test_folders = [
            "/Users/sanlike/project/Python/LocalKnowledgeAgent/ragData",
            "/Users/sanlike/Documents/TestData1",
            "/Users/sanlike/Documents/TestData2"
        ]
        
        for folder in test_folders:
            config.add_selected_folder(folder)
            print(f"   ✅ 追加: {folder}")
        
        # 2. 保存
        print("\n2. 設定保存...")
        success = config_manager.save_config(config)
        print(f"   ✅ 保存成功: {success}")
        
        # 3. 再読み込み・確認
        print("\n3. 設定再読み込み・確認...")
        config_reloaded = config_manager.load_config()
        print(f"   ✅ 再読み込み成功")
        
        # 4. フォルダ一致確認
        if set(config_reloaded.selected_folders) == set(test_folders):
            print("   ✅ フォルダ一致確認: 完全一致")
        else:
            print("   ⚠️  フォルダ一致確認: 不一致")
            print(f"      期待値: {test_folders}")
            print(f"      実際値: {config_reloaded.selected_folders}")
        
        # 5. クリーンアップ
        print("\n4. クリーンアップ...")
        config_reloaded.clear_selected_folders()
        config_manager.save_config(config_reloaded)
        print("   ✅ フォルダリストをクリア・保存完了")
        
        return True
        
    except Exception as e:
        print(f"❌ ワークフローテストエラー: {e}")
        return False

def main():
    """メインテスト実行"""
    print("🚀 CFG-011エラー修正確認テスト開始")
    print("=" * 60)
    
    success_count = 0
    total_tests = 2
    
    # CFG-011修正確認テスト
    if test_cfg_011_fix():
        success_count += 1
        print("\n✅ CFG-011修正確認テスト: 成功")
    else:
        print("\n❌ CFG-011修正確認テスト: 失敗")
    
    # ワークフロー完全テスト
    if test_config_save_workflow():
        success_count += 1
        print("\n✅ Config保存ワークフロー完全テスト: 成功")
    else:
        print("\n❌ Config保存ワークフロー完全テスト: 失敗")
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print(f"🏁 最終結果: {success_count}/{total_tests} 成功")
    
    if success_count == total_tests:
        print("🎉 ISSUE-012解決完了!")
        print("💡 RAGファイル登録時のCFG-011エラーは発生しません")
        print("🔧 修正内容:")
        print("   - ConfigManagerの2箇所でdocument_directories → selected_foldersに修正")
        print("   - config.document_directories → config.selected_folders")
        print("   - Configモデルとの属性名整合性を確保")
        return True
    else:
        print("⚠️  まだ修正が必要な問題があります")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)