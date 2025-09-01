# LocalKnowledgeAgent インストールガイド

バージョン: 1.0.0  
更新日: 2025-01-01

## 目次

1. [システム要件](#システム要件)
2. [事前準備](#事前準備)
3. [Ollamaセットアップ](#ollamaセットアップ)
4. [プロジェクトセットアップ](#プロジェクトセットアップ)
5. [動作確認](#動作確認)
6. [トラブルシューティング](#トラブルシューティング)

## システム要件

### 最小要件

- **OS**: Windows 10/11, macOS 12+, Ubuntu 20.04+
- **Python**: 3.8以上 (3.9推奨)
- **メモリ**: 4GB以上
- **ディスク**: 5GB以上の空き容量

### 推奨要件

- **メモリ**: 8GB以上 (LLMモデル用)
- **ディスク**: 15GB以上 (複数モデル保存用)
- **CPU**: 4コア以上

## 事前準備

### Python環境確認

```bash
# Pythonバージョン確認
python --version
# または
python3 --version

# pipが利用可能か確認
pip --version
```

**注意**: Python 3.8未満の場合は、最新版をインストールしてください。

### Git (オプション)

```bash
# Gitがインストール済みか確認
git --version
```

## Ollamaセットアップ

### 1. Ollamaインストール

#### Windows

1. [Ollama公式サイト](https://ollama.com/)からWindows版をダウンロード
2. `OllamaSetup.exe`を実行してインストール
3. インストール後、自動でOllamaサービスが開始されます

#### macOS

```bash
# Homebrewを使用 (推奨)
brew install ollama

# または公式インストールスクリプト
curl -fsSL https://ollama.com/install.sh | sh
```

#### Linux (Ubuntu/Debian)

```bash
# 公式インストールスクリプト
curl -fsSL https://ollama.com/install.sh | sh

# サービス開始
sudo systemctl start ollama
sudo systemctl enable ollama
```

### 2. Ollama動作確認

```bash
# Ollamaが正常に動作しているか確認
ollama --version

# サーバー状態確認
ollama list
```

### 3. 必須モデルダウンロード

#### 埋め込みモデル (必須)

```bash
# 推奨: 高品質・軽量な埋め込みモデル
ollama pull nomic-embed-text

# その他の選択肢
ollama pull all-minilm       # 軽量版
ollama pull mxbai-embed-large # 高精度版
ollama pull snowflake-arctic-embed # 多言語対応
```

#### LLMモデル (1つ以上選択)

```bash
# 推奨: バランスの取れた高性能モデル
ollama pull llama3:8b

# 軽量版: メモリ制約がある場合
ollama pull gemma2:2b

# 高性能版: 大容量メモリがある場合
ollama pull llama3:70b

# 多言語対応
ollama pull mistral:latest

# コーディング特化
ollama pull codellama:13b
```

#### モデル容量目安

| モデル | 容量 | メモリ使用量 | 用途 |
|--------|------|--------------|------|
| **埋め込みモデル** | | | |
| nomic-embed-text | 274MB | 500MB | 推奨・高品質 |
| all-minilm | 45MB | 200MB | 軽量版 |
| mxbai-embed-large | 669MB | 1GB | 高精度版 |
| snowflake-arctic-embed | 109MB | 300MB | 多言語対応 |
| **LLMモデル** | | | |
| gemma2:2b | 1.6GB | 2GB | 軽量・高速 |
| llama3:8b | 4.7GB | 6GB | 推奨・バランス型 |
| mistral:latest | 4.1GB | 5GB | 多言語対応 |
| llama3:70b | 40GB | 48GB | 最高性能 |

## プロジェクトセットアップ

### 1. プロジェクト取得

#### Git使用の場合

```bash
# リポジトリクローン
git clone <repository-url>
cd LocalKnowledgeAgent
```

#### ZIPダウンロードの場合

1. プロジェクトZIPファイルをダウンロード
2. 適切な場所に展開
3. 展開したフォルダに移動

```bash
cd LocalKnowledgeAgent
```

### 2. Python仮想環境作成

#### Windows(条件)

```cmd
# 仮想環境作成
python -m venv .venv

# 仮想環境有効化
.venv\Scripts\activate

# 確認 (プロンプトが (.venv) で始まることを確認)
```

#### macOS/Linux(条件)

```bash
# 仮想環境作成
python3 -m venv .venv

# 仮想環境有効化
source .venv/bin/activate

# 確認 (プロンプトが (.venv) で始まることを確認)
```

### 3. 依存関係インストール

```bash
# パッケージ更新
pip install --upgrade pip

# 依存関係インストール
pip install -r requirements.txt

# インストール確認
pip list
```

### 4. 初期設定

```bash
# 必要なディレクトリ作成 (自動作成されますが、手動でも可能)
mkdir -p data/chroma_db
mkdir -p logs
mkdir -p uploads
mkdir -p temp
```

## 動作確認

### 1. Ollamaサーバー起動確認

```bash
# 別ターミナル/コマンドプロンプトで実行
ollama serve

# または、既に起動している場合
ollama ps
```

### 2. アプリケーション起動

```bash
# メインターミナルで実行 (.venv環境がアクティブな状態で)
streamlit run app.py
```

### 3. ブラウザアクセス

ブラウザで以下にアクセス:

- **URL**: <http://localhost:8501>

### 4. 機能テスト

1. **設定画面**: サイドバーの「⚙️ 設定」をクリック
2. **モデル選択**: インストールしたOllamaモデルが表示されることを確認
3. **フォルダ追加**: テスト用フォルダを追加
4. **インデックス作成**: 「インデックス作成」ボタンが正常に動作することを確認
5. **質問テスト**: メイン画面で「こんにちは」と入力して回答を確認

## トラブルシューティング

### よくあるエラーと解決方法

#### 1. `ModuleNotFoundError`

**エラー例**:

```text
ModuleNotFoundError: No module named 'streamlit'
```

**解決方法**:

```bash
# 仮想環境が有効化されているか確認
# プロンプトが (.venv) で始まっているかチェック

# 依存関係を再インストール
pip install -r requirements.txt
```

#### 2. Ollama接続エラー

**エラー例**:

```text
[QA-003] Ollama APIへの接続に失敗しました
```

**解決方法**:

```bash
# Ollamaサーバー起動
ollama serve

# 別ターミナルでモデル確認
ollama list

# ポート確認
curl http://localhost:11434/api/tags
```

#### 3. モデル不足エラー

**エラー**:

```text
🚨 必須モデルのセットアップが必要です
```

**解決方法**:

```bash
# 埋め込みモデルインストール
ollama pull nomic-embed-text

# LLMモデルインストール (1つ以上)
ollama pull llama3:8b
```

#### 4. ポート競合

**エラー例**:

```text
Port 8501 is already in use
```

**解決方法**:

```bash
# 別のポートを使用
streamlit run app.py --server.port 8502

# または、使用中のプロセスを終了
# Windows: Ctrl+C でStreamlit終了
# macOS/Linux: killall streamlit
```

#### 5. メモリ不足

**エラー**:

```text
OutOfMemoryError: Unable to allocate memory
```

**解決方法**:

1. より軽量なモデルを使用: `gemma2:2b`
2. 他のアプリケーションを終了してメモリを解放
3. 設定でファイル数を制限

### ログ確認

問題が発生した場合、以下のログを確認してください:

```bash
# アプリケーションログ
cat logs/app.log

# Ollamaログ (Linux/macOS)
journalctl -u ollama

# Streamlitログ
# 起動時のターミナル出力を確認
```

### サポート

問題が解決しない場合:

1. **GitHub Issues**: バグレポートを作成
2. **ログ提供**: エラーログとシステム情報を添付
3. **環境情報**: OS、Pythonバージョン、インストール済みモデル一覧

## 高度な設定

### カスタム設定

```bash
# 設定ファイル編集
vi data/config.json

# Streamlit設定
vi .streamlit/config.toml
```

### 開発環境セットアップ

```bash
# 開発用依存関係
pip install pytest pytest-mock flake8 mypy

# テスト実行
pytest tests/

# コード品質チェック
flake8 src/
mypy src/
```

---

**インストール完了後は、[ユーザーマニュアル](USER_MANUAL.md)をご覧ください。**
