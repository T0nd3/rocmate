# Contributing to rocmate

Thanks for your interest! `rocmate` lives or dies by community-contributed configs — every working setup on a new AMD chip helps someone else avoid a rabbit hole.

## How to contribute

### Adding a tool config (most valuable contribution)

1. Copy `configs/tools/ollama.yaml` as a template.
2. Fill in the tool name, description, and homepage.
3. For each AMD chip you've personally tested, add an entry under `chips:` with:
   - `status`: `tested`, `partial`, or `broken`
   - `notes`: what you observed (ROCm version, model sizes, quirks)
   - `env_vars`: any ENV vars needed
   - `install_hints`: a short, copy-pasteable install sequence
4. Add yourself to the contributors list in the README.
5. Open a PR with `[config]` in the title.

### Improving an existing config

If you tested a chip that's marked `partial` and it actually works fine, please update the status with notes on what changed (ROCm version, kernel, driver).

### Reporting a broken setup

Open an issue with:
- Your chip (`rocminfo | grep Name`)
- ROCm version
- The tool and its version
- The exact error
- What you tried

### Code contributions

For CLI or library changes, please open an issue first to discuss the approach. Tests required for new functionality.

## Development setup

```bash
git clone https://github.com/yourhandle/rocmate
cd rocmate
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check src tests
```

## Code style

- Python 3.11+, type hints everywhere
- `ruff` for linting
- Keep CLI output friendly and copy-pasteable

## Code of Conduct

Be kind. Be specific. Don't gatekeep AMD hardware.
