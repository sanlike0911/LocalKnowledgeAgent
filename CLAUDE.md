# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LocalKnowledgeAgent is a Streamlit-based local RAG (Retrieval-Augmented Generation) system that indexes documents (PDF, TXT, DOCX, Markdown) and provides AI-powered question-answering using LangChain + ChromaDB + Ollama. The system runs entirely locally without external API dependencies.

## Architecture

The application follows a layered architecture:

```
┌─────────────────┐
│   Streamlit UI  │ ← User Interface (src/ui/)
├─────────────────┤  
│   Logic Layer   │ ← Business Logic (src/logic/)
├─────────────────┤
│   Data Layer    │ ← ChromaDB + Config (data/)
├─────────────────┤
│   LLM Layer     │ ← Ollama Integration
└─────────────────┘
```

### Key Components

- **app.py**: Main application entry point containing `LocalKnowledgeAgentApp` class
- **src/logic/qa.py**: Core RAG pipeline with `QAService`, `RAGPipeline`, `OllamaQAEngine`
- **src/logic/indexing.py**: Document indexing via `ChromaDBIndexer`
- **src/ui/**: Streamlit interface components (main_view, settings_view, navigation)
- **tests/**: Comprehensive test suite organized by module

## Common Development Commands

### Application Execution
```bash
# Standard application startup
streamlit run app.py

# Development mode (auto-reload, detailed errors)
streamlit run app.py --server.runOnSave=true --server.fileWatcherType=auto --global.developmentMode=true

# Production mode (optimized performance)  
streamlit run app.py --server.runOnSave=false --server.fileWatcherType=none --global.developmentMode=false --server.headless=true
```

### Testing
```bash
# Run all tests
pytest

# Run specific test module
pytest tests/logic/test_qa.py

# Run with verbose output
pytest -v
```

### Environment Setup
```bash
# Create and activate virtual environment (Windows)
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Ollama Management
```bash
# Check Ollama status and installed models
ollama list

# Install required models
ollama pull llama3:8b
ollama pull nomic-embed-text

# Start Ollama server (if not running)
ollama serve
```

## Development Guidelines

### Code Conventions
- **Naming**: snake_case for functions/variables, PascalCase for classes, UPPER_SNAKE_CASE for constants
- **Type Hints**: Required for all function parameters and return values
- **Docstrings**: Required for all public functions and classes (Japanese comments for complex logic)
- **Testing**: TDD approach using pytest with pytest-mock

### Task Management
- **Mandatory**: Use TodoWrite tool for all development tasks
- **Workflow**: Mark tasks "in_progress" when starting, "completed" immediately upon finishing
- **Planning**: Break complex tasks into smaller, manageable steps

### Required Dependencies
- Python 3.9+ (currently 3.11.13)
- Streamlit 1.49+
- LangChain 0.3+, ChromaDB 1.0+, Ollama 0.5+
- pytest 8.4+ for testing

### Configuration Files
- **data/config.json**: Application configuration (Ollama settings, folder paths)
- **.streamlit/config.toml**: Streamlit UI configuration (production-optimized)
- **pyproject.toml**: Project metadata and build configuration

## Task Completion Checklist

When completing development tasks:

1. **Verification**: Ensure `streamlit run app.py` starts successfully
2. **Testing**: Run `pytest` and verify all tests pass  
3. **Ollama**: Confirm `ollama list` shows required models
4. **Dependencies**: Update `requirements.txt` if new packages added
5. **Type Safety**: Verify type hints are complete and accurate

## Project Structure Notes

- The application uses a service-oriented architecture with clear separation between UI, business logic, and data layers
- ChromaDB handles vector storage and retrieval for RAG functionality
- Ollama integration provides local LLM inference without external API calls
- Security features include input validation, CORS configuration, and XSS protection
- The system is optimized for Japanese language processing and responses