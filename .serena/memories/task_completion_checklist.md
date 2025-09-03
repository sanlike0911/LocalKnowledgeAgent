# Task Completion Checklist

## When a Development Task is Completed

### Code Quality Checks
1. **Type Checking**: Run `mypy src/` (if configured)
2. **Code Formatting**: Ensure consistent formatting with `black` (if configured)
3. **Linting**: Run `flake8 src/` (if configured)

### Testing Requirements
1. **Unit Tests**: Run `pytest tests/` 
2. **Test Coverage**: Verify adequate test coverage
3. **Integration Tests**: Run integration test suite if applicable

### Validation Steps
1. **Manual Testing**: Test the implemented functionality manually
2. **Ollama Integration**: Verify Ollama connectivity with `ollama list`
3. **Application Startup**: Verify app starts with `streamlit run app.py`
4. **Dependencies**: Ensure all requirements are in `requirements.txt`

### Documentation Updates
1. **Code Comments**: Ensure complex logic has Japanese comments
2. **Docstrings**: All new functions/classes have proper docstrings
3. **Type Hints**: All functions have complete type annotations

### Environment Verification
1. **Virtual Environment**: Ensure `.venv` is active during development
2. **Python Version**: Verify compatibility with Python 3.9+
3. **Ollama Models**: Verify required models are installed

### Before Commit
1. **File Organization**: Ensure files are in correct directories according to project structure
2. **Configuration**: Verify configuration files are updated if needed
3. **Error Handling**: Ensure proper exception handling and logging

## Required Commands to Run After Task Completion
```bash
# Verify application starts
streamlit run app.py

# Run test suite  
pytest

# Check Ollama integration
ollama list
```