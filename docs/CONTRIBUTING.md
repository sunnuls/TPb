# Contributing to TPb

## Getting Started

1. Fork the repository
2. Clone your fork
3. Create a feature branch
4. Make your changes
5. Submit a pull request

## Development Setup

See [SETUP.md](./SETUP.md) for installation instructions.

## Code Style

- Use TypeScript strict mode
- Follow ESLint rules
- Use Prettier for formatting (if configured)
- Write meaningful commit messages

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `style` - Code style
- `refactor` - Code refactoring
- `test` - Tests
- `chore` - Build/config

Example:
```
feat(backend): add equity calculator

Implement Monte Carlo equity calculation engine
with 100k iteration target.

Closes #42
```

## Testing

Run tests before submitting PR:

```bash
# Backend tests
cd backend
npm test

# Frontend tests
cd frontend
npm test
```

## Pull Request Process

1. Update documentation if needed
2. Add tests for new features
3. Ensure all tests pass
4. Update CHANGES.md
5. Request review from maintainers

## Code Review

All PRs require:
- At least 1 approval
- Passing CI checks
- No merge conflicts

## Questions?

Open an issue or discussion on GitHub.

