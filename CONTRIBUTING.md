# Contributing

## Setup

```bash
git clone https://github.com/hermes-93/python-automation.git
cd python-automation
pip install -r requirements-dev.txt
```

## Adding a New Script

1. Create `scripts/my_script.py` with a `main()` click command
2. Add tests in `tests/test_my_script.py`
3. Update `README.md` with usage examples

## Code Style

- Max line length: 120 characters
- Use `click` for CLI argument parsing
- Use `rich` for terminal output
- Type hints required for public functions

## Running Tests

```bash
make test
# or
python -m pytest tests/ -v --cov=scripts
```

## Commit Convention

- `feat:` new script or feature
- `fix:` bug fix
- `test:` test additions/changes
- `docs:` documentation only
- `ci:` CI/CD changes
- `chore:` maintenance (deps, config)
