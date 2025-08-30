"""
テスト用共通設定 (pytest conftest)
全テストで使用される外部依存関係のモック設定
"""

import sys
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))


def mock_all_external_dependencies():
    """すべての外部依存関係をモック"""
    
    # ChromaDB関連のモック
    chromadb_mock = MagicMock()
    chromadb_mock.config = MagicMock()
    chromadb_mock.config.Settings = MagicMock()
    chromadb_mock.Client = MagicMock()
    chromadb_mock.PersistentClient = MagicMock()
    sys.modules['chromadb'] = chromadb_mock
    sys.modules['chromadb.config'] = chromadb_mock.config
    
    # PyPDF2のモック
    pypdf2_mock = MagicMock()
    pypdf2_mock.PdfReader = MagicMock()
    sys.modules['PyPDF2'] = pypdf2_mock
    
    # LangChain関連のモック
    langchain_mocks = {
        'langchain': MagicMock(),
        'langchain_community': MagicMock(),
        'langchain_ollama': MagicMock(),
        'langchain.text_splitter': MagicMock(),
        'langchain_community.embeddings': MagicMock(),
    }
    
    for name, mock in langchain_mocks.items():
        sys.modules[name] = mock
        if '.' in name:
            parent = name.split('.')[0]
            if parent not in sys.modules:
                sys.modules[parent] = MagicMock()
    
    # LangChain具体的クラスのモック
    sys.modules['langchain'].text_splitter = MagicMock()
    sys.modules['langchain'].text_splitter.RecursiveCharacterTextSplitter = MagicMock()
    sys.modules['langchain_community'].embeddings = MagicMock()
    sys.modules['langchain_community'].embeddings.OllamaEmbeddings = MagicMock()
    
    # Ollama関連のモック
    ollama_mock = MagicMock()
    sys.modules['ollama'] = ollama_mock
    
    # Requests関連のモック
    requests_mock = MagicMock()
    sys.modules['requests'] = requests_mock
    
    # Streamlit関連のモック
    streamlit_mock = MagicMock()
    
    # SessionState のモック
    class MockSessionState(dict):
        def __getattr__(self, name):
            return self.get(name)
        
        def __setattr__(self, name, value):
            self[name] = value
    
    streamlit_mock.session_state = MockSessionState()
    sys.modules['streamlit'] = streamlit_mock
    
    # その他の依存関係
    other_mocks = {
        'pandas': MagicMock(),
        'numpy': MagicMock(),
        'dotenv': MagicMock(),
        'pathlib': MagicMock(),
    }
    
    for name, mock in other_mocks.items():
        if name not in sys.modules:
            sys.modules[name] = mock


# プラグイン読み込み時点で依存関係をモック
mock_all_external_dependencies()


@pytest.fixture(autouse=True)
def setup_test_environment():
    """各テスト実行前の環境セットアップ"""
    # Streamlit session_stateをクリーンな状態に初期化
    if 'streamlit' in sys.modules:
        sys.modules['streamlit'].session_state.clear()
    
    yield
    
    # テスト後のクリーンアップ
    if 'streamlit' in sys.modules:
        sys.modules['streamlit'].session_state.clear()


@pytest.fixture
def mock_config():
    """モック設定オブジェクト"""
    from src.models.config import Config
    return Config(
        ollama_host="http://localhost:11434",
        ollama_model="llama3.1:8b",
        chroma_db_path="./test_data/chroma_db",
        chroma_collection_name="test_knowledge_base",
        max_chat_history=10
    )


@pytest.fixture
def mock_chromadb_indexer():
    """モックChromaDBIndexer"""
    with patch('src.logic.indexing.ChromaDBIndexer') as mock:
        indexer = MagicMock()
        indexer.collection_name = "test_collection"
        indexer.get_collection_stats.return_value = {
            "collection_name": "test_collection",
            "document_count": 5,
            "db_path": "./test_data/chroma_db",
            "embedding_model": "nomic-embed-text"
        }
        mock.return_value = indexer
        yield indexer


@pytest.fixture
def mock_rag_pipeline():
    """モックRAGPipeline"""
    with patch('src.logic.qa.RAGPipeline') as mock:
        pipeline = MagicMock()
        pipeline.answer_question.return_value = {
            'query': 'テストクエリ',
            'answer': 'テスト回答',
            'sources': [{'filename': 'test.txt', 'distance': 0.1}],
            'context': 'テストコンテキスト',
            'processing_time': 1.0
        }
        mock.return_value = pipeline
        yield pipeline


@pytest.fixture
def mock_qa_service():
    """モックQAService"""
    with patch('src.logic.qa.QAService') as mock:
        service = MagicMock()
        service.ask_question.return_value = {
            'query': 'テストクエリ',
            'answer': 'テスト回答',
            'sources': [{'filename': 'test.txt'}],
            'context': 'テストコンテキスト'
        }
        mock.return_value = service
        yield service


@pytest.fixture
def mock_config_manager():
    """モックConfigManager"""
    with patch('src.logic.config_manager.ConfigManager') as mock:
        manager = MagicMock()
        from src.models.config import Config
        manager.load_config.return_value = Config()
        manager.save_config.return_value = True
        mock.return_value = manager
        yield manager


@pytest.fixture
def clean_test_environment():
    """テスト環境のクリーンアップ"""
    # テストデータディレクトリをクリーンアップ
    import shutil
    test_data_path = Path("./test_data")
    if test_data_path.exists():
        shutil.rmtree(test_data_path)
    
    yield
    
    # テスト後のクリーンアップ
    if test_data_path.exists():
        shutil.rmtree(test_data_path)


# pytest設定
def pytest_configure(config):
    """pytest設定"""
    # 警告を抑制
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", message=".*ScriptRunContext.*")
    warnings.filterwarnings("ignore", message=".*Session state.*")