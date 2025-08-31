#!/usr/bin/env python3
"""
起動時モデルチェック機能の統合テスト

ISSUE-016: 起動時にOllamaの必須モデル（llama3:8b、nomic-embed-text）が
インストールされているかチェックし、不足している場合はユーザーに
適切なガイダンスを表示する機能の動作確認
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from src.logic.ollama_checker import OllamaModelChecker, ModelCheckResult


def test_startup_model_check():
    """起動時モデルチェック機能のテスト"""
    print("=" * 60)
    print("ISSUE-016: 起動時モデルチェック機能テスト")
    print("=" * 60)
    
    try:
        # OllamaModelCheckerインスタンス作成
        checker = OllamaModelChecker()
        print(f"✅ OllamaModelChecker初期化成功")
        
        # 必須モデル確認
        print(f"\n📋 必須モデル設定確認:")
        for model_name, model_info in checker.REQUIRED_MODELS.items():
            print(f"   - {model_info.display_name}")
            print(f"     名前: {model_info.name}")
            print(f"     用途: {model_info.description}")
            print(f"     インストールコマンド: {model_info.install_command}")
        
        # モデルチェック実行
        print(f"\n🔍 Ollamaモデルチェック実行中...")
        check_result = checker.check_required_models()
        
        print(f"\n📊 チェック結果:")
        print(f"   - Ollama接続: {'✅ 成功' if check_result.ollama_connected else '❌ 失敗'}")
        print(f"   - 必須モデル完備: {'✅ はい' if check_result.is_available else '❌ いいえ'}")
        
        if check_result.available_models:
            print(f"   - 利用可能モデル数: {len(check_result.available_models)}")
            for model in check_result.available_models:
                print(f"     ✅ {model}")
        
        if check_result.missing_models:
            print(f"   - 不足モデル数: {len(check_result.missing_models)}")
            for model in check_result.missing_models:
                print(f"     ❌ {model.display_name} ({model.name})")
        
        if check_result.error_message:
            print(f"   - エラー: {check_result.error_message}")
        
        # インストールガイド生成テスト
        if check_result.missing_models:
            print(f"\n📖 インストールガイド:")
            guide = checker.get_installation_guide(check_result.missing_models)
            print("─" * 60)
            print(guide)
            print("─" * 60)
        
        # 結果判定
        if check_result.is_available:
            print(f"\n🎉 すべての必須モデルが利用可能です！アプリケーションを起動できます。")
            return True
        else:
            print(f"\n⚠️  不足しているモデルがあります。上記のインストールガイドに従ってください。")
            return False
            
    except Exception as e:
        print(f"❌ テスト中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()
        return False


def simulate_app_startup():
    """アプリケーション起動シミュレーション"""
    print(f"\n" + "=" * 60)
    print("アプリケーション起動シミュレーション")
    print("=" * 60)
    
    try:
        # OllamaModelCheckerでチェック
        checker = OllamaModelChecker()
        check_result = checker.check_required_models()
        
        print(f"🚀 LocalKnowledgeAgent起動中...")
        
        if not check_result.ollama_connected:
            print(f"❌ Ollamaサーバーに接続できません")
            print(f"   解決方法:")
            print(f"   1. Ollamaがインストールされているか確認")
            print(f"   2. 'ollama serve' コマンドでサーバーを起動")
            return False
        
        if not check_result.is_available:
            print(f"❌ 必須モデルが不足しています")
            print(f"   不足モデル: {', '.join([m.name for m in check_result.missing_models])}")
            print(f"   インストール後、アプリケーションを再起動してください")
            return False
        
        print(f"✅ モデルチェック完了 - すべての必須モデルが利用可能")
        print(f"✅ アプリケーション起動可能")
        return True
        
    except Exception as e:
        print(f"❌ 起動チェック中にエラー: {e}")
        return False


if __name__ == "__main__":
    print("LocalKnowledgeAgent 起動時モデルチェック機能テスト\n")
    
    # 基本テスト実行
    basic_test_success = test_startup_model_check()
    
    # 起動シミュレーション実行
    startup_simulation_success = simulate_app_startup()
    
    # 総合結果
    print(f"\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)
    print(f"基本機能テスト: {'✅ 成功' if basic_test_success else '❌ 失敗'}")
    print(f"起動シミュレーション: {'✅ 成功' if startup_simulation_success else '❌ 失敗'}")
    
    if basic_test_success and startup_simulation_success:
        print(f"\n🎉 すべてのテストが成功しました！")
        print(f"   起動時モデルチェック機能は正常に動作しています。")
        sys.exit(0)
    else:
        print(f"\n⚠️  一部のテストが失敗しました。")
        print(f"   必要に応じてモデルをインストールしてください。")
        sys.exit(1)