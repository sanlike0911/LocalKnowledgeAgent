# LocalKnowledgeAgent

ローカル実行対応のAI知識管理システム

## 概要

LocalKnowledgeAgentは、**Streamlit**ベースのデスクトップWebアプリケーションです。  
PDF・TXT・DOCX・Markdownファイルを自動インデックス化し、**LangChain + ChromaDB + Ollama**によるRAGシステムで質問応答を提供します。

### 主な特徴

- 🖥️ **完全ローカル実行**: 外部APIなし、データはローカル保存
- 📚 **多形式対応**: PDF, TXT, DOCX, Markdown ファイル
- 🤖 **LLMモデル選択**: Ollama経由で複数モデル対応
- ⚡ **高速検索**: ChromaDBによるベクトル検索
- 🎯 **日本語最適化**: 日本語回答強制機能
- 📊 **進捗表示**: 長時間処理の可視化
- 🔒 **セキュリティ**: ファイル検証・XSS対策

## システム要件

### 必須ソフトウェア

- **Python**: 3.8以上
- **Ollama**: ローカルLLMサーバー

### 推奨環境

- メモリ: 8GB以上 (LLMモデル実行用)
- ディスク: 10GB以上 (モデル保存用)

## インストール手順

### 1. Ollamaのインストール

```bash
# macOS/Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows
# https://ollama.com/ から Windows版をダウンロード・インストール
```

### 2. 必須モデルのダウンロード

```bash
# LLMモデル (選択してインストール)
ollama pull llama3:8b       # 推奨: 高品質・高速
ollama pull gemma2:9b       # 軽量版
ollama pull mistral:latest  # 多言語対応

# 埋め込みモデル (必須)
ollama pull nomic-embed-text
```

### 3. プロジェクトのセットアップ

```bash
# リポジトリをクローン
git clone <repository-url>
cd LocalKnowledgeAgent

# 仮想環境作成
python -m venv .venv

# 仮想環境有効化
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt
```

### 4. アプリケーション起動

```bash
# Ollamaサーバー起動 (別ターミナル)
ollama serve

# アプリケーション起動
streamlit run app.py
```

ブラウザで **http://localhost:8501** にアクセスしてください。

## 使用方法

### 1. 初回設定

1. **設定画面** (サイドバーから選択)
2. **フォルダパス設定**: 知識ベースにしたいフォルダを追加
3. **LLMモデル選択**: 使用するOllamaモデルを選択
4. **インデックス作成**: 「インデックス作成」ボタンを実行

### 2. 質問・回答

1. **メイン画面**に移動
2. チャット欄に質問を入力
3. AI回答と参考ソースを確認

### 3. ファイル管理

- 対応形式: `.pdf`, `.txt`, `.docx`, `.md`
- 最大ファイルサイズ: 50MB
- 自動インデックス更新

## 技術構成

### アーキテクチャ

```
┌─────────────────┐
│   Streamlit UI  │ ← ユーザーインターフェース
├─────────────────┤
│   Logic Layer   │ ← QAService, ChromaDBIndexer
├─────────────────┤
│   Data Layer    │ ← ChromaDB, Config.json
├─────────────────┤
│   LLM Layer     │ ← Ollama (ローカルLLM)
└─────────────────┘
```

### 主要技術

- **UI**: Streamlit 1.49+
- **RAG**: LangChain 0.3+
- **ベクトルDB**: ChromaDB 1.0+
- **LLM**: Ollama 0.5+
- **テスト**: pytest 8.4+

## 設定ファイル

### data/config.json

```json
{
  "ollama_host": "http://localhost:11434",
  "ollama_model": "llama3:8b",
  "embedding_model": "nomic-embed-text",
  "chroma_db_path": "./data/chroma_db",
  "selected_folders": ["C:\\workspace\\documents"],
  "force_japanese_response": true
}
```

### .streamlit/config.toml

プロダクション設定済み (自動最適化)

## トラブルシューティング

### よくある問題

#### 1. Ollama接続エラー

**エラー**: `Connection refused`

**解決策**:
```bash
# Ollamaサーバー状態確認
ollama list

# Ollamaサービス再起動
ollama serve
```

#### 2. モデル不足エラー

**エラー**: `Model not found`

**解決策**:
```bash
# 必要なモデルをインストール
ollama pull llama3:8b
ollama pull nomic-embed-text
```

#### 3. メモリ不足

**エラー**: `OutOfMemoryError`

**解決策**:
- より軽量なモデルを使用: `gemma2:2b`
- 同時処理を制限

#### 4. インデックス作成失敗

**エラー**: `[IDX-001] インデックス作成エラー`

**解決策**:
1. 設定画面でフォルダパスを確認
2. ファイルアクセス権限を確認
3. インデックス削除→再作成

## パフォーマンス

### 処理時間目安

- **インデックス作成**: 100ファイル/5分
- **質問回答**: 平均5-15秒
- **文書検索**: 0.1-0.5秒

### リソース使用量

- **メモリ**: 2-6GB (モデルサイズ依存)
- **CPU**: 中程度 (推論時のみ)
- **ディスク**: 5-20GB (モデル保存)

## 開発・貢献

### 開発環境

```bash
# 開発用依存関係
pip install pytest pytest-mock

# テスト実行
pytest tests/

# コード品質チェック
flake8 src/
mypy src/
```

### プロジェクト構造

```
LocalKnowledgeAgent/
├── app.py                    # エントリーポイント
├── src/
│   ├── ui/                   # Streamlit UI
│   ├── logic/                # ビジネスロジック
│   ├── models/               # データモデル
│   └── utils/                # ユーティリティ
├── tests/                    # テストスイート
├── data/                     # データ・設定
└── docs/                     # ドキュメント
```

## ライセンス

MIT License

## サポート

- **Issues**: GitHub Issues
- **Wiki**: プロジェクトWiki
- **Discussions**: GitHub Discussions

---

**バージョン**: 1.0.0  
**最終更新**: 2025-01-01  
**開発**: LocalKnowledgeAgent Team