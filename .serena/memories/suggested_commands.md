# Suggested Commands for LocalKnowledgeAgent

## Development Commands

### Application Execution
```bash
# Start the application (standard mode)
streamlit run app.py

# Development mode with auto-reload and detailed errors
streamlit run app.py --server.runOnSave=true --server.fileWatcherType=auto --global.developmentMode=true

# Production mode with optimized performance
streamlit run app.py --server.runOnSave=false --server.fileWatcherType=none --global.developmentMode=false --server.headless=true
```

### Testing
```bash
# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run specific test module
pytest tests/logic/test_qa.py

# Run tests with coverage
pytest --cov=src
```

### Environment Management
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify Python version (requires 3.9+)
python --version
```

### Ollama Management
```bash
# Check Ollama version
ollama --version

# Start Ollama server
ollama serve

# List installed models
ollama list

# Install required models
ollama pull llama3:8b
ollama pull nomic-embed-text

# Check if models are available
ollama show llama3:8b
ollama show nomic-embed-text
```

### System Commands (Windows)
```cmd
# List directory contents
dir

# Change directory
cd path\to\directory

# Find files
where filename

# Process management
tasklist
taskkill /PID process_id
```

## Configuration Files
- **Main config**: `data/config.json` (application settings)
- **Streamlit config**: `.streamlit/config.toml` (UI configuration)
- **Dependencies**: `requirements.txt` and `pyproject.toml`