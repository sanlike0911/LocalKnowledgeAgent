# LocalKnowledgeAgent Architecture

## Application Architecture
```
┌─────────────────┐
│   Streamlit UI  │ ← User Interface Layer
├─────────────────┤
│   Logic Layer   │ ← QAService, ChromaDBIndexer
├─────────────────┤
│   Data Layer    │ ← ChromaDB, Config.json  
├─────────────────┤
│   LLM Layer     │ ← Ollama (Local LLM)
└─────────────────┘
```

## Project Structure
```
LocalKnowledgeAgent/
├── app.py                    # Main entry point (LocalKnowledgeAgentApp class)
├── src/
│   ├── ui/                   # Streamlit UI components
│   │   ├── main_view.py      # Main chat interface
│   │   ├── settings_view.py  # Configuration interface  
│   │   └── navigation.py     # Navigation logic
│   ├── logic/                # Core business logic
│   │   ├── qa.py            # QAService, RAGPipeline, OllamaQAEngine
│   │   ├── indexing.py      # ChromaDBIndexer
│   │   ├── config_manager.py # Configuration management
│   │   ├── ollama_checker.py # Ollama connectivity
│   │   └── ollama_model_service.py # Model management
│   ├── models/              # Data models
│   ├── utils/               # Utilities
│   ├── security/            # Security components
│   ├── interfaces/          # Interface definitions
│   └── exceptions/          # Custom exceptions
├── tests/                   # Comprehensive test suite
├── data/                    # Data storage (config.json, chroma_db)
└── .streamlit/              # Streamlit configuration
```

## Core Components
- **LocalKnowledgeAgentApp**: Main application controller in app.py
- **QAService**: Question-answering orchestration (src/logic/qa.py)  
- **ChromaDBIndexer**: Document indexing and retrieval (src/logic/indexing.py)
- **RAGPipeline**: RAG workflow implementation
- **OllamaQAEngine**: Ollama integration for LLM inference