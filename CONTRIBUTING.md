# Contributing to Enhanced Cognee

> **Note:** Enhanced Cognee is a derivative work of [Cognee](https://github.com/topoteretes/cognee). Please ensure your contributions align with both the Enhanced Cognee goals and the original Cognee license (Apache 2.0).

Thank you for your interest in contributing to Enhanced Cognee! We welcome contributions from the community and appreciate your help in making this project better.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Ways to Contribute](#ways-to-contribute)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Submitting Changes](#submitting-changes)
- [Developer Certificate of Origin](#developer-certificate-of-origin)
- [Community Guidelines](#community-guidelines)
- [Getting Help](#getting-help)

---

## Code of Conduct

We are committed to fostering an inclusive and respectful community. Please read and follow our [Code of Conduct](https://github.com/topoteretes/cognee/blob/main/CODE_OF_CONDUCT.md).

---

## Ways to Contribute

You can contribute to Enhanced Cognee in many ways:

### 🐛 Reporting Bugs

- Check existing [GitHub Issues](https://github.com/vincentspereira/Enhanced-Cognee/issues) first
- Use the bug report template for new issues
- Include steps to reproduce, expected behavior, and environment details

### 💡 Suggesting Features

- Check existing feature requests first
- Clearly describe the use case and benefits
- Consider if it fits the Enhanced Cognee vision (enterprise-grade, production-ready)

### 📝 Improving Documentation

- Fix typos and clarify unclear sections
- Add usage examples
- Improve setup instructions
- Document new features

### 🛠️ Contributing Code

- Fix reported bugs
- Implement new features
- Improve performance
- Add tests
- Refactor code for better maintainability

### 🌍 Helping Others

- Answer questions in [GitHub Discussions](https://github.com/vincentspereira/Enhanced-Cognee/discussions)
- Help review pull requests
- Share your usage examples

---

## Getting Started

### Prerequisites

- **Python**: 3.10 or higher
- **Docker**: Latest version for running Enhanced databases
- **Git**: For version control
- **GitHub account**: For contributing via Pull Requests

### Fork and Clone

1. Fork the [Enhanced Cognee repository](https://github.com/vincentspereira/Enhanced-Cognee)
2. Clone your fork locally:

```bash
git clone https://github.com/vincentspereira/Enhanced-Cognee.git
cd enhanced-cognee
```

3. Add the original repository as upstream (to keep your fork in sync):

```bash
git remote add upstream https://github.com/vincentspereira/Enhanced-Cognee.git
```

---

## Development Setup

### 1. Create a Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate (Linux/Mac)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# Install in development mode
pip install -e ".[dev]"

# Or using uv (faster)
uv pip install -e ".[dev]"
```

### 3. Start Enhanced Databases

```bash
# Start all Enhanced databases via Docker
docker compose -f docker/docker-compose-enhanced-cognee.yml up -d

# Verify containers are running
docker ps | grep enhanced
```

### 4. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# Add your API keys and database credentials
```

### 5. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=cognee --cov-report=html

# Run specific test file
pytest tests/test_memory_integration.py
```

---

## Making Changes

### Branch Naming

Use descriptive branch names:

- `bugfix/fix-qdrant-connection`
- `feature/add-memory-cache`
- `docs/update-installation-guide`
- `refactor/optimize-vector-search`

### Code Style

Follow the project's coding standards:

```bash
# Format code with ruff
ruff format .

# Check for linting issues
ruff check

# Fix auto-fixable issues
ruff check --fix
```

### Writing Code

1. **Follow Python best practices** (PEP 8, type hints where appropriate)
2. **Add docstrings** to all functions and classes
3. **Write tests** for new functionality
4. **Use ASCII-only output** (no Unicode symbols like ✓, ✗, ⚠️)
5. **Avoid hardcoded categories** - use dynamic configuration
6. **Maintain backward compatibility** with original Cognee API where possible

### ASCII-Only Output Requirement

**CRITICAL:** All output must use ASCII characters only.

**✅ Correct:**
```python
print("OK PostgreSQL connected")
print("WARN Qdrant connection slow")
print("ERR Failed to connect to Neo4j")
```

**❌ Wrong:**
```python
print("✓ PostgreSQL connected")
print("⚠️ Qdrant connection slow")
print("✗ Failed to connect to Neo4j")
```

### Dynamic Categories

**✅ Correct:**
```python
# Load categories from config
config = EnhancedConfig()
categories = config.category_prefixes
```

**❌ Wrong:**
```python
# Hardcoded categories
class MemoryCategory(Enum):
    ATS = "ats"
    OMA = "oma"
```

### Documentation

Update documentation alongside code changes:

- Update README.md for user-facing changes
- Add docstrings to functions/classes
- Update examples if behavior changes
- Add migration notes for breaking changes

---

## Submitting Changes

### 1. Sync Your Fork

```bash
# Fetch latest changes from upstream
git fetch upstream

# Merge upstream changes into your branch
git merge upstream/main
```

### 2. Commit Your Changes

```bash
# Stage changes
git add .

# Commit with signed-off message (DCO)
git commit -s -m "feat: add Qdrant vector search optimization

- Implemented HNSW index configuration
- Added batch embedding support
- Improved query performance by 300%

Closes #123"
```

### Commit Message Format

Use conventional commit format:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

### 3. Push Your Changes

```bash
# Push to your fork
git push origin feature/your-feature-name
```

### 4. Create Pull Request

1. Go to the [Enhanced Cognee repository](https://github.com/vincentspereira/Enhanced-Cognee)
2. Click "Compare & Pull Request"
3. Fill in the PR template:
   - Describe your changes
   - Link related issues
   - Add screenshots if applicable
   - Confirm all checks pass

---

## Developer Certificate of Origin (DCO)

All contributions must be signed-off to indicate agreement with our DCO:

```bash
# Configure git to sign commits automatically
git config alias.cos "commit -s"

# Or use -s flag with each commit
git commit -s -m "Your commit message"
```

In your PR, include:

> "I affirm that all code in every commit of this pull request conforms to the terms of the Apache License 2.0 and the Developer Certificate of Origin"

---

## Community Guidelines

- **Be respectful** - Treat everyone with dignity and respect
- **Be inclusive** - Welcome diverse perspectives and backgrounds
- **Be collaborative** - Work together to solve problems
- **Be constructive** - Provide helpful feedback and suggestions
- **Follow the Code of Conduct** - We have zero tolerance for harassment

---

## Getting Help

### Resources

- **Documentation**: Check the `docs/` directory and README.md
- **Issues**: Search existing [GitHub Issues](https://github.com/vincentspereira/Enhanced-Cognee/issues)
- **Discussions**: Ask questions in [GitHub Discussions](https://github.com/vincentspereira/Enhanced-Cognee/discussions)

### Asking Questions

When asking for help:

1. **Search first** - Check if your question has been answered
2. **Be specific** - Provide details about your issue
3. **Share context** - Include error messages, environment details
4. **Be patient** - Community members volunteer their time

### Issue Labels

We use these labels to help triage issues:

- `good first issue` - Great for newcomers
- `bug` - Something isn't working
- `documentation` - Docs need improvement
- `enhancement` - New feature or improvement
- `help wanted` - Extra help needed
- `question` - Further information requested

Looking for somewhere to start? Check [good first issues](https://github.com/vincentspereira/Enhanced-Cognee/labels/good%20first%20issue)!

---

## Recognition

Contributors will be:

- Listed in the CONTRIBUTORS.md file
- Mentioned in release notes for significant contributions
- Credited in related documentation

Thank you for contributing to Enhanced Cognee! 🚀

---

## Additional Resources

- [Original Cognee Contributing Guide](https://github.com/topoteretes/cognee/blob/main/CONTRIBUTING.md)
- [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)
- [MCP Specification](https://modelcontextprotocol.io/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Neo4j Documentation](https://neo4j.com/docs/)
- [Redis Documentation](https://redis.io/docs/)
