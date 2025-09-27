# Contributing to env-agents

We welcome contributions to the env-agents environmental data integration framework!

## 🚀 Quick Start

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/env-agents.git
   cd env-agents
   ```
3. **Install in development mode**:
   ```bash
   pip install -e .
   ```
4. **Run tests** to ensure everything works:
   ```bash
   python run_tests.py --capabilities
   ```

## 🔧 Development Setup

See [docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md) for detailed development environment setup.

## 📝 How to Contribute

### Adding New Environmental Data Services

The most valuable contributions are new environmental data adapters! See [docs/EXTENDING_SERVICES.md](docs/EXTENDING_SERVICES.md) for a complete guide including a working NOAA adapter example.

### Bug Reports

- Use GitHub Issues to report bugs
- Include Python version, OS, and error messages
- Provide minimal reproduction steps

### Pull Requests

1. **Create a feature branch**: `git checkout -b feature-name`
2. **Make your changes** following our patterns
3. **Add tests** if applicable
4. **Run the test suite**: `python run_tests.py`
5. **Submit pull request** with clear description

## 🧪 Testing

```bash
# Quick capabilities test
python run_tests.py --capabilities

# Full service integration tests
python run_tests.py --services

# Contract tests
python -m pytest tests/test_contract.py
```

## 📋 Code Style

- Follow existing patterns in the codebase
- Use descriptive variable names
- Add docstrings for public methods
- Follow Python PEP 8 guidelines

## 🛠️ Adding Environmental Services

Priority areas for new adapters:
- **Climate data** (additional weather services)
- **Marine data** (oceanographic, coastal)
- **Agricultural data** (crop, soil health)
- **Energy data** (renewable, consumption)

## 📄 License

By contributing, you agree that your contributions will be licensed under the same MIT License that covers the project.

## 🙏 Recognition

Contributors are acknowledged in releases and documentation. Thank you for helping make environmental data more accessible!