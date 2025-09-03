# Development Guidelines for LocalKnowledgeAgent

## Code Style and Conventions
- **Function/Variable naming**: snake_case (e.g., `calculate_string_length`)
- **Class naming**: PascalCase (e.g., `StringLengthCalculator`)  
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_STRING_LENGTH`)
- **Type hints**: Required for all function arguments and return values
- **Docstrings**: Required for all functions and classes
- **Comments**: Complex logic should have Japanese comments

## Development Workflow
1. **TDD Implementation** (Required):
   - Red: Write failing test
   - Green: Implement minimal code to pass
   - Refactor: Clean up implementation
   
2. **Testing Framework**: pytest with pytest-mock
3. **Code Quality**: Static analysis expected
4. **Error Handling**: Structured logging (JSON format), appropriate exception classes

## Task Management Rules
- **All tasks must be managed with TodoWrite tool**
- **Start task**: Change status to "in_progress"  
- **Complete task**: Change status to "completed" immediately
- **No development without TodoWrite usage**

## Security Requirements
- Input validation and sanitization for all user inputs
- CORS configuration with appropriate origin restrictions
- XSS protection enabled
- Rate limiting for API calls
- Security headers configured

## Performance Considerations  
- Database indexing properly configured
- Caching strategy implemented (Redis if needed)
- Async processing for I/O intensive operations
- Progress indicators for operations taking >3 seconds

## User Experience Standards
- All user actions must show processing results (success/failure)
- Error messages in Japanese with clear resolution steps
- Immediate visual feedback for user interactions
- Operation guidance for complex workflows