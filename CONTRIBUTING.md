# Contributing to FastService

Thank you for your interest in contributing to FastService! This document provides guidelines and instructions for contributing to our open source FastAPI project.

## How to Contribute

We welcome contributions in many forms:

- **Code**: Bug fixes, new features, and improvements
- **Documentation**: Fixes, enhancements, and clarifications
- **Tests**: Additional test coverage for existing or new functionality
- **Issues**: Bug reports and feature requests

## Development Setup

### Prerequisites

- Python 3.9 or higher
- [uv](https://docs.astral.sh/uv/) for package management

### Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/iAmLakshya/fastService.git
   cd fastService
   ```

2. Install dependencies and set up the development environment:
   ```bash
   uv sync
   ```

3. Verify your setup by running the test suite:
   ```bash
   make test
   ```

## Code Style

We maintain consistent code quality through automated tooling.

### Formatting and Linting

We use [ruff](https://docs.astral.sh/ruff/) for both linting and code formatting. Run the formatter and linter:

```bash
make format    # Format code with ruff
make lint      # Check code with ruff
```

### Type Checking

We use [mypy](https://www.mypy-lang.org/) for static type checking. Ensure your code passes type checks:

```bash
make type-check
```

### Make Commands

Common development tasks are available through `make`:

```bash
make help          # View all available commands
make format        # Format code
make lint          # Lint code
make type-check    # Run type checker
make test          # Run tests
```

## Pull Request Process

1. **Create a branch**: Use a descriptive branch name
   ```bash
   git checkout -b feature/description-of-feature
   ```

2. **Make your changes**: Implement your feature or fix

3. **Run checks**: Ensure all code quality checks pass
   ```bash
   make format lint type-check test
   ```

4. **Commit your changes**: Follow the commit message conventions (see below)

5. **Push to your fork** and submit a pull request to the `main` branch

6. **PR Description**: Clearly describe what your changes do, why they're needed, and any relevant issue numbers

### PR Guidelines

- Keep PRs focused on a single feature or bug fix
- Include tests for new functionality
- Update documentation if needed
- Ensure all checks pass before requesting review
- Be responsive to feedback and review comments

## Commit Message Conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/) for clear, semantic commit messages.

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring without feature changes
- `perf`: Performance improvements
- `test`: Test additions or modifications
- `chore`: Build process, dependencies, tooling changes

### Examples

```
feat(auth): add JWT token refresh endpoint

fix(api): handle null values in request validation

docs: update installation instructions

test(users): add coverage for user creation endpoint
```

## Running Tests

Run the test suite:

```bash
make test
```

For test coverage:

```bash
make test-coverage
```

Tests are required for all new features and bug fixes. Please ensure:

- All new code has corresponding tests
- Existing tests still pass
- Test coverage doesn't decrease

## Reporting Bugs

When reporting a bug, please include:

1. **Clear title**: A brief summary of the issue
2. **Description**: Detailed explanation of the problem
3. **Steps to reproduce**: Clear, numbered steps to reproduce the issue
4. **Expected behavior**: What should happen
5. **Actual behavior**: What actually happens
6. **Environment**:
   - Python version
   - OS and version
   - FastService version
7. **Logs or error messages**: Any relevant error output or logs
8. **Screenshots**: If applicable

## Code of Conduct

Please note that this project is released with a Contributor Code of Conduct. By participating in this project you agree to abide by its terms.

## Questions?

Feel free to open an issue for questions or discussion. We're here to help!

---

Thank you for contributing to FastService!
