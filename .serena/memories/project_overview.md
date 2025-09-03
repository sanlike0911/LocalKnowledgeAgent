# LocalKnowledgeAgent Project Overview

## Purpose
LocalKnowledgeAgent is a Streamlit-based desktop web application that provides a local RAG (Retrieval-Augmented Generation) system. It automatically indexes PDF, TXT, DOCX, and Markdown files, and offers question-answering functionality using LangChain + ChromaDB + Ollama.

## Tech Stack
- **UI Framework**: Streamlit 1.49+
- **RAG Pipeline**: LangChain 0.3+
- **Vector Database**: ChromaDB 1.0+
- **LLM Integration**: Ollama 0.5+
- **Document Processing**: PyPDF2, python-docx, markdown, unstructured
- **Testing**: pytest 8.4+
- **Python**: 3.9+ (currently running on 3.11.13)

## Key Features
- Complete local execution (no external APIs)
- Multi-format document support (PDF, TXT, DOCX, Markdown)
- Multiple LLM model support via Ollama
- Vector search with ChromaDB
- Japanese language optimization
- Progress visualization for long-running processes
- Security features (file validation, XSS protection)