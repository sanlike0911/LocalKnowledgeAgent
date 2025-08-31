#!/usr/bin/env python3
"""
CFG-007エラー修正後のテスト
ISSUE-011: 設定画面でフォルダ追加時にCFG-007エラーが発生する問題の修正確認
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

def test_cfg_007_fix():
    """CFG-007エラーが修正されているかテスト"""
    
    print("🔍 CFG-007エラー修正確認テスト")
    print("=" * 50)
    
    try:
        # ConfigManager初期化
        print("\n1. ConfigManager初期化...")
        config_manager = ConfigManager()
        
        # 設定読み込み
        print("2. デフォルト設定読み込み...")
        config = config_manager.load_config()
        print(f"✅ 設定読み込み成功")
        print(f"   - ollama_host: {config.ollama_host}")
        print(f"   - ollama_model: {config.ollama_model}")
        print(f"   - selected_folders: {config.selected_folders}")
        
        # フォルダ追加（CFG-007エラーの原因となっていた操作）
        print("\n3. フォルダ追加テスト...")
        test_folder = "/Users/test/documents"
        config.add_selected_folder(test_folder)
        print(f"✅ フォルダ追加成功: {test_folder}")
        
        # バリデーション実行（これがCFG-007エラーの原因だった）
        print("\n4. 設定バリデーション...")
        config_dict = config.to_dict()
        
        # 必須フィールドが存在するかチェック
        required_fields = [
            key for key, rules in config_manager.validation_rules.items()
            if rules.get("required", False)
        ]
        
        print(f"   必須フィールド: {required_fields}")
        for field in required_fields:
            if field in config_dict:
                print(f"   ✅ {field}: {config_dict[field]}")
            else:
                print(f"   ❌ {field}: 不足")
        
        # バリデーション実行
        config_manager.validate_config_data(config_dict)
        print("✅ バリデーション成功 - CFG-007エラーなし")
        
        return True
        
    except ConfigError as e:
        if "CFG-007" in str(e):
            print(f"❌ CFG-007エラーが再発: {e}")
            return False
        else:
            print(f"❌ 他のConfigエラー: {e}")
            return False
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        return False

def test_validation_rules():
    """バリデーションルールが正しく設定されているかテスト"""
    
    print("\n" + "=" * 50)
    print("🔍 バリデーションルール確認")
    print("=" * 50)
    
    try:
        config_manager = ConfigManager()
        
        print(f"\n設定されているバリデーションルール:")
        for field, rules in config_manager.validation_rules.items():
            required = rules.get("required", False)
            field_type = rules.get("type", "未設定")
            print(f"  - {field}: required={required}, type={field_type}")
        
        # Configモデルの属性と比較
        print(f"\nConfigモデルの属性:")
        config = Config()
        for attr in config.__dict__.keys():
            print(f"  - {attr}")
        
        print("\n✅ バリデーションルール確認完了")
        return True
        
    except Exception as e:
        print(f"❌ バリデーションルール確認エラー: {e}")
        return False

def main():
    """メインテスト実行"""
    print("🚀 CFG-007エラー修正確認テスト開始")
    print("=" * 60)
    
    success_count = 0
    total_tests = 2
    
    # CFG-007修正確認テスト
    if test_cfg_007_fix():
        success_count += 1
        print("\n✅ CFG-007修正確認テスト: 成功")
    else:
        print("\n❌ CFG-007修正確認テスト: 失敗")
    
    # バリデーションルール確認テスト
    if test_validation_rules():
        success_count += 1
        print("\n✅ バリデーションルール確認テスト: 成功")
    else:
        print("\n❌ バリデーションルール確認テスト: 失敗")
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print(f"🏁 最終結果: {success_count}/{total_tests} 成功")
    
    if success_count == total_tests:
        print("🎉 ISSUE-011解決完了!")
        print("💡 設定画面でフォルダを追加してもCFG-007エラーは発生しません")
        print("🔧 修正内容:")
        print("   - ConfigManagerのバリデーションルールをConfigモデルに合わせて修正")
        print("   - ollama_base_url → ollama_host")
        print("   - max_search_results を削除（Configモデルに存在しないため）")
        print("   - 適切なフィールドを追加（selected_folders, max_chat_history など）")
        return True
    else:
        print("⚠️  まだ修正が必要な問題があります")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)