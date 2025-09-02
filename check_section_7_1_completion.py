"""
セクション7.1の完了状況確認スクリプト
【△v3.1】埋め込みモデル動的フィルタリング機能の詳細チェック
"""

import sys
from pathlib import Path
import ast

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def check_7_1_embedding_filtering():
    """セクション7.1 埋め込みモデルフィルタリング機能の確認"""
    print("=== セクション7.1完了状況確認 ===")
    print("#### 7.1 埋め込みモデル動的フィルタリング機能 (【△v3.1】)")
    
    tasks = {}
    
    # **埋め込みモデルフィルタリング機能** (TDD適用)
    print("\n**埋め込みモデルフィルタリング機能** (TDD適用)")
    
    # 1. テストケース: インストール済みモデル一覧取得テスト
    test_file1 = project_root / "tests" / "logic" / "test_embedding_model_filtering.py"
    if test_file1.exists():
        content = test_file1.read_text(encoding="utf-8")
        if "test_get_available_models" in content or "インストール済みモデル" in content:
            tasks["test_installed_models"] = True
            print("✅ テストケース: インストール済みモデル一覧取得テスト")
        else:
            tasks["test_installed_models"] = False
            print("❌ テストケース: インストール済みモデル一覧取得テスト")
    else:
        tasks["test_installed_models"] = False
        print("❌ テストケース: インストール済みモデル一覧取得テスト (ファイル無し)")
    
    # 2. テストケース: サポート対象モデルリストとの積集合フィルタリングテスト
    if test_file1.exists():
        content = test_file1.read_text(encoding="utf-8")
        if "test_filter_embedding_models" in content or "積集合" in content:
            tasks["test_intersection_filtering"] = True
            print("✅ テストケース: サポート対象モデルリストとの積集合フィルタリングテスト")
        else:
            tasks["test_intersection_filtering"] = False
            print("❌ テストケース: サポート対象モデルリストとの積集合フィルタリングテスト")
    else:
        tasks["test_intersection_filtering"] = False
        print("❌ テストケース: サポート対象モデルリストとの積集合フィルタリングテスト (ファイル無し)")
    
    # 3. 最小実装: filter_embedding_modelsメソッド実装
    service_file = project_root / "src" / "logic" / "ollama_model_service.py"
    if service_file.exists():
        content = service_file.read_text(encoding="utf-8")
        if "def filter_embedding_models" in content:
            tasks["filter_method_impl"] = True
            print("✅ 最小実装: `filter_embedding_models(installed_models, supported_models)`メソッド実装")
        else:
            tasks["filter_method_impl"] = False
            print("❌ 最小実装: `filter_embedding_models`メソッド実装")
    else:
        tasks["filter_method_impl"] = False
        print("❌ 最小実装: OllamaModelServiceファイルが見つかりません")
    
    # 4. リファクタリング: エラーハンドリング・空リスト対応・ソート機能
    if service_file.exists():
        content = service_file.read_text(encoding="utf-8")
        has_error_handling = "except" in content and "filter_embedding_models" in content
        has_empty_check = "if not" in content and ("installed_models" in content or "supported_models" in content)
        has_sort = "sorted(" in content
        
        if has_error_handling and has_empty_check and has_sort:
            tasks["refactoring_complete"] = True
            print("✅ リファクタリング: エラーハンドリング・空リスト対応・ソート機能")
        else:
            tasks["refactoring_complete"] = False
            print("❌ リファクタリング: エラーハンドリング・空リスト対応・ソート機能 (一部不完全)")
    else:
        tasks["refactoring_complete"] = False
        print("❌ リファクタリング: ファイルが見つかりません")
    
    # **設定画面UI拡張** (TDD適用)
    print("\n**設定画面UI拡張** (TDD適用)")
    
    # 5. テストケース: 動的埋め込みモデル選択コンボボックステスト
    test_file2 = project_root / "tests" / "ui" / "test_embedding_model_selector.py"
    if test_file2.exists():
        content = test_file2.read_text(encoding="utf-8")
        if "test_" in content and ("selector" in content or "selectbox" in content):
            tasks["test_ui_selector"] = True
            print("✅ テストケース: 動的埋め込みモデル選択コンボボックステスト")
        else:
            tasks["test_ui_selector"] = False
            print("❌ テストケース: 動的埋め込みモデル選択コンボボックステスト")
    else:
        tasks["test_ui_selector"] = False
        print("❌ テストケース: 動的埋め込みモデル選択コンボボックステスト (ファイル無し)")
    
    # 6. 最小実装: サポート対象モデルリストの設定ファイル読み込み
    config_file = project_root / "data" / "config.json"
    if config_file.exists():
        content = config_file.read_text(encoding="utf-8")
        if "supported_embedding_models" in content:
            tasks["config_supported_models"] = True
            print("✅ 最小実装: サポート対象モデルリストの設定ファイル読み込み")
        else:
            tasks["config_supported_models"] = False
            print("❌ 最小実装: サポート対象モデルリストの設定ファイル読み込み")
    else:
        tasks["config_supported_models"] = False
        print("❌ 最小実装: 設定ファイルが見つかりません")
    
    # 7. 最小実装: フィルタリング結果のselectboxオプション設定
    settings_file = project_root / "src" / "ui" / "settings_view.py"
    if settings_file.exists():
        content = settings_file.read_text(encoding="utf-8")
        if "get_filtered_embedding_models_with_fallback" in content and "st.selectbox" in content:
            tasks["ui_selectbox_impl"] = True
            print("✅ 最小実装: フィルタリング結果のselectboxオプション設定")
        else:
            tasks["ui_selectbox_impl"] = False
            print("❌ 最小実装: フィルタリング結果のselectboxオプション設定")
    else:
        tasks["ui_selectbox_impl"] = False
        print("❌ 最小実装: SettingsViewファイルが見つかりません")
    
    # 8. リファクタリング: 選択肢が0件の場合のエラー処理・警告表示
    if settings_file.exists():
        content = settings_file.read_text(encoding="utf-8")
        if "利用可能な埋め込みモデルが見つかりません" in content or "warning" in content:
            tasks["ui_error_handling"] = True
            print("✅ リファクタリング: 選択肢が0件の場合のエラー処理・警告表示")
        else:
            tasks["ui_error_handling"] = False
            print("❌ リファクタリング: 選択肢が0件の場合のエラー処理・警告表示")
    else:
        tasks["ui_error_handling"] = False
        print("❌ リファクタリング: SettingsViewファイルが見つかりません")
    
    # 完了率計算
    completed_tasks = sum(1 for task in tasks.values() if task)
    total_tasks = len(tasks)
    completion_rate = (completed_tasks / total_tasks) * 100
    
    print(f"\n=== 完了状況サマリー ===")
    print(f"完了率: {completion_rate:.1f}% ({completed_tasks}/{total_tasks})")
    
    for task_name, completed in tasks.items():
        status = "✅" if completed else "❌"
        print(f"{status} {task_name}")
    
    return tasks, completion_rate >= 100

def verify_design_alignment():
    """設計書との整合性確認"""
    print("\n=== 設計書との整合性確認 ===")
    
    design_file = project_root / "docs" / "design-specification.md"
    if not design_file.exists():
        print("❌ 設計書が見つかりません")
        return False
    
    content = design_file.read_text(encoding="utf-8")
    
    # v3.1の動的フィルタリング機能の記述を確認
    if "v3.1" in content and "動的フィルタリング" in content:
        print("✅ 設計書にv3.1動的フィルタリング機能の記述があります")
        return True
    elif "埋め込みモデル" in content and "フィルタ" in content:
        print("✅ 設計書に埋め込みモデルフィルタリング機能の記述があります")
        return True
    else:
        print("⚠️ 設計書に明確な動的フィルタリング機能の記述が見つかりません")
        return False

if __name__ == "__main__":
    print("=== セクション7.1完了状況確認スクリプト ===")
    
    # 1. セクション7.1の各項目確認
    tasks, is_complete = check_7_1_embedding_filtering()
    
    # 2. 設計書との整合性確認
    design_aligned = verify_design_alignment()
    
    # 3. 最終判定
    print(f"\n=== 最終判定 ===")
    if is_complete:
        print("✅ セクション7.1の全項目が完了しています")
        if design_aligned:
            print("✅ 設計書との整合性も確認できました")
            print("📝 プロジェクト計画書の更新が可能です")
        else:
            print("⚠️ 設計書との整合性要確認")
    else:
        print("❌ セクション7.1に未完了項目があります")
    
    print("\n✅ 確認完了")