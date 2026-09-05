# Contributing to Ariba SOC

Thank you for your interest in contributing to Ariba SOC! This document provides guidelines and information for contributors.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/ariba_soc.git`
3. Create a feature branch: `git checkout -b feature/amazing-feature`
4. Make your changes
5. Commit: `git commit -m 'feat: add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open a Pull Request

## Development Setup

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+ (for frontend assets)

### Local Development
```bash
# Clone the repo
git clone https://github.com/boniyeamincse/ariba_soc.git
cd ariba_soc

# Copy environment files
cp infrastructure/.env.example infrastructure/.env
cp ariba_soc/.env.example ariba_soc/.env

# Start the stack
cd infrastructure
./scripts/setup.sh
```

## Code Style

### Python
- Follow PEP 8
- Use Black for formatting: `black .`
- Use isort for imports: `isort .`
- Use flake8 for linting: `flake8 .`

### Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation changes
- `style:` formatting changes
- `refactor:` code refactoring
- `test:` adding tests
- `chore:` maintenance tasks

### Branch Naming

- `feature/` - new features
- `fix/` - bug fixes
- `docs/` - documentation
- `refactor/` - code refactoring
- `test/` - adding tests

## Pull Request Process

1. Update documentation if needed
2. Add tests for new functionality
3. Ensure all tests pass: `make test`
4. Update the README if needed
5. Request review from maintainers

## Code Review

All submissions require review before merging. We use GitHub pull requests for this purpose.

## Reporting Issues

Use the GitHub issue tracker to report bugs. Please include:

- OS and Python version
- Steps to reproduce
- Expected behavior
- Actual behavior
- Logs/screenshots if applicable

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
