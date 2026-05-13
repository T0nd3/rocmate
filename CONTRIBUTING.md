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
4. Open a PR with `[config]` in the title.

**Note on `install_hints`:** CI automatically scans hints for dangerous patterns (`rm -rf`, `eval`, `curl | bash`, etc.) and will reject any that match. Hints containing shell operators (`&&`, `|`) are treated as display-only and never auto-executed by `rocmate install` — so compound commands are fine to include as guidance.

**Note on reviews:** All changes to `configs/tools/` require approval from a maintainer (enforced via CODEOWNERS). This is intentional — install hints run on users' machines.

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
git clone https://github.com/T0nd3/rocmate
cd rocmate
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest

# Lint and format
ruff check src tests
ruff format src tests

# Validate tool configs (same check CI runs)
python scripts/lint_configs.py
```

## Code style

- Python 3.11+, type hints everywhere
- `ruff check` for linting, `ruff format` for formatting (replaces flake8 + black + isort)
- CI enforces both — run them locally before pushing
- Keep CLI output friendly and copy-pasteable

## Web matrix

The compatibility matrix at [t0nd3.github.io/rocmate](https://t0nd3.github.io/rocmate/) is generated automatically from the YAML configs by `scripts/build_matrix.py` and deployed via GitHub Pages on every push to `main`. No manual step needed — merging a config PR is enough.

## Code of Conduct

Be kind. Be specific. Don't gatekeep AMD hardware.
