# Contributing Guidelines

Welcome to the Stock Alerts project! This guide will help you contribute effectively to the codebase while maintaining code quality and consistency.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+ with pip and venv
- PostgreSQL database (local or remote)
- Git for version control
- Code editor with Python support

### Development Setup

1. **Fork and Clone**
   ```bash
   # Fork the repository on GitHub, then clone your fork
   git clone https://github.com/your-username/stock-alerts.git
   cd stock-alerts
   
   # Add upstream remote
   git remote add upstream https://github.com/original-owner/stock-alerts.git
   ```

2. **Environment Setup**
   ```bash
   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # venv\Scripts\activate     # Windows
   
   # Install dependencies
   pip install -r requirements.txt
   pip install -e ".[dev]"  # Development tools
   ```

3. **Configuration**
   ```bash
   # Create development environment file
   cp .env.example .env
   # Edit .env with your development credentials
   ```

4. **Database Setup**
   ```bash
   # Create development database
   createdb stockalerts_dev
   
   # Run the application to auto-create schema
   python app.py
   ```

5. **Verify Setup**
   ```bash
   # Test application starts
   curl http://localhost:5001/health
   # Expected: {"status": "healthy"}
   
   # Test API endpoint
   curl http://localhost:5001/data/AAPL/1y
   ```

---

## 🔄 Development Workflow

### Branch Strategy

```bash
# Create feature branch from main
git checkout main
git pull upstream main
git checkout -b feature/your-feature-name

# Work on your changes...

# Keep branch updated
git fetch upstream
git rebase upstream/main
```

### Commit Guidelines

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Format: type(scope): description
git commit -m "feat(api): add trading stats endpoint"
git commit -m "fix(webhook): handle malformed telegram updates"
git commit -m "docs: update API documentation with new endpoints"
git commit -m "refactor(db): optimize stock cache queries"
```

**Commit Types:**
- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Test additions/modifications
- `chore`: Maintenance tasks

### Pull Request Process

1. **Before Submitting**
   ```bash
   # Run code quality checks
   black .                    # Format code
   isort .                   # Sort imports
   flake8 .                  # Lint code
   mypy .                    # Type checking
   
   # Run tests (if available)
   pytest
   
   # Test application manually
   python app.py
   ```

2. **Create Pull Request**
   - Use descriptive title following conventional commits format
   - Fill out the PR template completely
   - Link related issues with `Closes #123`
   - Add screenshots for UI changes
   - Ensure all CI checks pass

3. **PR Requirements**
   - ✅ All tests pass
   - ✅ Code coverage maintained
   - ✅ Documentation updated
   - ✅ No merge conflicts
   - ✅ Approved by maintainer

---

## 📝 Code Standards

### Python Style Guide

**Configuration:** [`pyproject.toml`](../pyproject.toml) and [`setup.cfg`](../setup.cfg)

```python
# Good: Clear function with type hints and docstring
def validate_ticker_symbol(ticker: str) -> Tuple[bool, str]:
    """
    Validate stock ticker symbol format.
    
    Args:
        ticker: Stock symbol to validate
        
    Returns:
        Tuple of (is_valid, validated_ticker_or_error)
    """
    if not ticker or len(ticker) > 5:
        return False, "Ticker must be 1-5 characters"
    
    return True, ticker.upper()

# Bad: No types, unclear function
def check_ticker(t):
    if t and len(t) <= 5:
        return True, t.upper()
    return False, "Bad ticker"
```

### Code Quality Tools

**Black (Code Formatting):**
```bash
# Format all Python files
black .

# Check formatting without changes
black --check .
```

**isort (Import Sorting):**
```bash
# Sort imports
isort .

# Configuration in pyproject.toml
[tool.isort]
profile = "black"
known_first_party = ["stock_alerts", "services", "routes", "utils"]
```

**MyPy (Type Checking):**
```bash
# Type check all files
mypy .

# Configuration in pyproject.toml enables strict checking
```

**Flake8 (Linting):**
```bash
# Lint code
flake8 .

# Configuration in setup.cfg
```

### Logging Standards

**Good Logging Practices:**

```python
import logging

logger = logging.getLogger("StockAlerts.ComponentName")

# Good: Structured logging with context
logger.info(f"Fetching stock data for {symbol} ({period})")
logger.warning(f"Cache miss for {symbol}, fetching from API")
logger.error(f"Failed to fetch {symbol}: {e}", exc_info=True)

# Bad: Print statements
print(f"Getting data for {symbol}")  # ❌ Never use print()

# Bad: No context
logger.info("Data fetched")  # ❌ Too vague
```

**Log Levels:**
- `DEBUG`: Detailed debugging information
- `INFO`: General application flow
- `WARNING`: Recoverable issues
- `ERROR`: Serious problems with exception details
- `CRITICAL`: Application failure scenarios

### Security Guidelines

**Environment Variables:**
```python
# Good: Use centralized config
from utils.config import config
api_token = config.TIINGO_API_TOKEN

# Bad: Direct environment access
import os
api_token = os.getenv("TIINGO_API_TOKEN")  # ❌ Use config.py
```

**Input Validation:**
```python
# Good: Use validators module
from utils.validators import validate_ticker_symbol

is_valid, ticker = validate_ticker_symbol(user_input)
if not is_valid:
    return jsonify({"error": ticker}), 400

# Bad: No validation
symbol = request.args.get("ticker").upper()  # ❌ Dangerous
```

**Database Queries:**
```python
# Good: Parameterized queries
cursor.execute(
    "SELECT * FROM users WHERE id = %s",
    (user_id,)
)

# Bad: String interpolation
cursor.execute(f"SELECT * FROM users WHERE id = '{user_id}'")  # ❌ SQL injection risk
```

---

## 🗄️ Database Changes

### Migration System

**Create New Migration:**
```bash
# Create migration file with sequential numbering
# Format: NNN_description.sql

# Example: migrations/003_add_user_timezone.sql
```

**Migration File Template:**
```sql
-- Migration: Add user timezone preference
-- Description: Allow users to set their timezone for alert scheduling

-- Add new column with default value
ALTER TABLE users ADD COLUMN timezone TEXT DEFAULT 'UTC';

-- Add constraint for valid timezones
ALTER TABLE users ADD CONSTRAINT valid_timezone 
  CHECK (timezone IN ('UTC', 'US/Eastern', 'US/Central', 'US/Mountain', 'US/Pacific', 'Europe/London'));

-- Create index for timezone queries
CREATE INDEX idx_users_timezone ON users(timezone);

-- Insert comment for documentation
COMMENT ON COLUMN users.timezone IS 'User timezone for alert scheduling (default UTC)';
```

**Migration Best Practices:**
- **Backward Compatible**: Don't break existing functionality
- **Idempotent**: Safe to run multiple times
- **Tested**: Verify on development database first
- **Documented**: Include clear comments and descriptions

### Database Testing

```bash
# Test migration on development database
psql stockalerts_dev < migrations/003_add_user_timezone.sql

# Verify schema changes
psql stockalerts_dev -c "\d users"

# Test application still works
python app.py
curl http://localhost:5001/health
```

---

## 📚 Documentation Requirements

### Documentation is Mandatory

Every code change **must** include corresponding documentation updates. This ensures the documentation remains accurate and helpful.

### Code Reference Standards

**All technical claims must include direct code references:**

```markdown
<!-- Good: Specific file and function references -->
The webhook validation is performed by [`webhook_handler.py:validate_webhook()`](../webhook_handler.py) 
using HMAC-SHA256 timing-safe comparison.

Stock data caching is handled by [`db_manager.py:get_fresh_cache()`](../db_manager.py) 
with a default TTL of 1 hour (configurable via `CACHE_HOURS`).

<!-- Bad: Vague references without specific locations -->
The system validates webhooks securely.
Stock data is cached for performance.
```

### Files to Update

**Always check these files when making changes:**

| File | Update When |
|------|-------------|
| [README.md](../README.md) | Major features, architecture changes |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System design, component changes |
| [API.md](./API.md) | New endpoints, parameter changes |
| [SETUP.md](./SETUP.md) | Dependencies, environment variables |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Deployment process changes |
| [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) | New common issues |

### Documentation Format

**Use consistent markdown formatting:**

```markdown
## 📊 Section Title

### Subsection

**Implementation:** [`file.py:function()`](../file.py)  
**Dependencies:** External libraries or services  

#### Code Example

```python
# Good: Complete, working example
from utils.config import config

def example_function():
    return config.DATABASE_URL
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ticker` | string | ✅ | Stock symbol (e.g., AAPL) |
| `period` | string | ✅ | Time period: 1y, 3y, 5y, max |
```

---

## 🧪 Testing Guidelines

### Test Structure

```python
# tests/test_validators.py
import pytest
from utils.validators import validate_ticker_symbol

class TestTickerValidation:
    """Test ticker symbol validation logic."""
    
    def test_valid_ticker_symbols(self):
        """Test that valid symbols are accepted."""
        valid_symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "A"]
        
        for symbol in valid_symbols:
            is_valid, result = validate_ticker_symbol(symbol)
            assert is_valid, f"Symbol {symbol} should be valid"
            assert result == symbol.upper()
    
    def test_invalid_ticker_symbols(self):
        """Test that invalid symbols are rejected."""
        invalid_symbols = ["", "TOOLONG", "123", "AA-BB"]
        
        for symbol in invalid_symbols:
            is_valid, error = validate_ticker_symbol(symbol)
            assert not is_valid, f"Symbol {symbol} should be invalid"
            assert isinstance(error, str)
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_validators.py

# Run tests matching pattern
pytest -k "test_ticker"
```

### Test Database

```bash
# Create test database
createdb stockalerts_test

# Set test environment
export DATABASE_URL=postgresql://localhost/stockalerts_test

# Run tests with test database
pytest
```

---

## 🔧 Development Tools

### IDE Configuration

**VS Code Settings (`.vscode/settings.json`):**
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "python.sortImports.args": ["--profile", "black"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

**Pre-commit Configuration (`.pre-commit-config.yaml`):**
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
  
  - repo: https://github.com/pycqa/isort
    rev: 5.10.1
    hooks:
      - id: isort
  
  - repo: https://github.com/pycqa/flake8
    rev: 4.0.1
    hooks:
      - id: flake8
```

### Debugging

**Local Development:**
```python
# Add debugging breakpoints
import pdb; pdb.set_trace()

# Or use ipdb for better interface
import ipdb; ipdb.set_trace()

# Enable debug mode
export DEBUG=True
python app.py
```

**Production Debugging:**
```bash
# Check application logs
tail -f logs/stock_alerts.log

# Check specific component logs
grep -i "webhook\|scheduler\|database" logs/stock_alerts.log

# Test specific endpoints
curl -v http://localhost:5001/health
curl -v http://localhost:5001/data/AAPL/1y
```

---

## 🐛 Issue Guidelines

### Bug Reports

**Use this template for bug reports:**

```markdown
## Bug Description
Clear description of the issue

## Steps to Reproduce
1. Step one
2. Step two
3. Expected vs actual result

## Environment
- Python version: 
- Operating system:
- Database: PostgreSQL version
- Platform: Local/Railway/Heroku/etc.

## Logs
```
Relevant log entries from logs/stock_alerts.log
```

## Additional Context
Screenshots, error messages, etc.
```

### Feature Requests

**Use this template for feature requests:**

```markdown
## Feature Description
What functionality would you like to see?

## Use Case
Why is this feature needed?

## Proposed Implementation
High-level approach (optional)

## Additional Context
Mockups, examples, related issues
```

---

## 💬 Community Guidelines

### Code Review Process

**For Reviewers:**
- ✅ Check code quality and standards
- ✅ Verify tests pass and coverage maintained
- ✅ Ensure documentation is updated
- ✅ Test functionality manually if possible
- ✅ Provide constructive feedback

**For Contributors:**
- ✅ Respond to feedback promptly
- ✅ Make requested changes
- ✅ Keep PR scope focused
- ✅ Update tests and docs as needed

### Communication

- **Be respectful** and constructive in all interactions
- **Ask questions** if anything is unclear
- **Provide context** in issues and PRs
- **Follow up** on discussions and reviews

---

## 🎯 Contribution Areas

### Good First Issues

Perfect for new contributors:
- Documentation improvements
- Adding input validation
- Writing tests for existing code
- Fixing typos and formatting
- Adding logging to functions

### Advanced Contributions

For experienced developers:
- New API endpoints
- Database optimization
- Background job improvements
- Security enhancements
- Performance optimizations

### Documentation Contributions

Always welcome:
- Improving existing documentation
- Adding code examples
- Creating tutorials
- Updating architecture diagrams

---

## 📞 Getting Help

### Resources

- **Setup Issues**: [SETUP.md](./SETUP.md)
- **Deployment Problems**: [DEPLOYMENT.md](./DEPLOYMENT.md)
- **Common Issues**: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- **System Understanding**: [ARCHITECTURE.md](./ARCHITECTURE.md)

### Contact

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Code Review**: Submit PRs for review and feedback

---

**Thank you for contributing to Stock Alerts! 🚀**

Your contributions help make this project better for everyone. Whether you're fixing a bug, adding a feature, or improving documentation, every contribution is valuable and appreciated.