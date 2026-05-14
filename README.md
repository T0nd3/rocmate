# rocmate

[![PyPI](https://img.shields.io/pypi/v/rocmate)](https://pypi.org/project/rocmate/)
[![CI](https://github.com/T0nd3/rocmate/actions/workflows/ci.yml/badge.svg)](https://github.com/T0nd3/rocmate/actions/workflows/ci.yml)
[![Website](https://img.shields.io/badge/matrix-t0nd3.github.io%2Frocmate-blue)](https://t0nd3.github.io/rocmate/)
[![License: MIT](https://img.shields.io/github/license/T0nd3/rocmate)](LICENSE)

> Get AMD GPUs running with AI tools — without the rabbit hole.

`rocmate` is a curated compatibility index and CLI for running modern AI workloads on AMD GPUs — via ROCm or Vulkan. It tells you what works on your specific card, what to set, and what to avoid — based on configurations that real users have tested.

```
pip install rocmate
```

![rocmate doctor](https://raw.githubusercontent.com/T0nd3/rocmate/main/docs/rocmate-doctor.png)

## Why?

AMD GPUs offer great VRAM-per-dollar (especially the RX 7900 XTX with 24 GB), but getting Ollama, ComfyUI, faster-whisper, or axolotl to actually use the GPU still involves hunting through blog posts, GitHub issues, and Discord threads. Information is scattered, often outdated, and rarely specific to your chip generation (gfx1030 vs gfx1100 vs gfx1151 vs gfx1201).

`rocmate` consolidates this knowledge into one place — version-controlled, testable, community-maintained.

## Quickstart

```bash
# Install (Python 3.11+)
pip install rocmate

# Check your system
rocmate doctor

# Show the tested config for a tool (optionally filter by chip)
rocmate show ollama
rocmate show ollama --chip gfx1100

# Search tools by keyword
rocmate search llm

# Install a tool with the right ENV vars
rocmate install ollama

# Auto-fix detected issues
rocmate doctor --fix
```

## Supported tools

→ **[Live compatibility matrix](https://t0nd3.github.io/rocmate/)** — auto-updated on every commit.

| Tool | gfx1151<br>Radeon 8060S/8050S | gfx1100<br>RX 7900 XT/XTX | gfx1101<br>RX 7800/7700 XT | gfx1102<br>RX 7600 | gfx1030<br>RX 6800/6900 | gfx1201<br>RX 9070 |
|------|:-:|:-:|:-:|:-:|:-:|:-:|
| Ollama | ✅ | ✅ | ✅ | ✅ | ✅ | 🟡 |
| ComfyUI | 🟡 | ✅ | ✅ | 🟡 | 🟡 | — |
| faster-whisper | ✅ | ✅ | 🟡 | — | — | — |
| llama.cpp | ✅ | ✅ | ✅ | ✅ | ✅ | 🟡 |
| Stable Diffusion WebUI | 🟡 | ✅ | ✅ | 🟡 | 🟡 | — |
| vLLM | ✅ | ✅ | ✅ | 🟡 | 🟡 | 🟡 |
| Axolotl | 🟡 | ✅ | ✅ | 🟡 | 🟡 | — |
| ExLlamaV2 | 🟡 | ✅ | ✅ | 🟡 | 🟡 | — |

✅ tested · 🟡 partial / workarounds needed · — no data yet

Run `rocmate show <tool>` for chip-specific ENV vars, install hints, and tested ROCm versions.

## Status

Actively maintained by [@T0nd3](https://github.com/T0nd3) on an RX 7900 XTX. Contributions for other AMD chips are very welcome — one YAML file, five minutes. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Roadmap

- [x] `rocmate doctor` — system diagnostic (GPU, ROCm, groups, Docker, Vulkan)
- [x] `rocmate show <tool>` — display tested config per chip
- [x] `rocmate show <tool> --chip <gfx>` — filter to a single chip
- [x] `rocmate list` — list all supported tools
- [x] `rocmate search <keyword>` — search tools by name or description
- [x] `rocmate install <tool>` — plan and execute install with correct ENV vars
- [x] `rocmate doctor --tool <name>` — tool-specific compatibility check
- [x] `rocmate doctor --fix` — interactively apply fixes for detected issues
- [x] Windows / HIP SDK support (GPU detection via hipinfo + WMI fallback)
- [x] Web-facing compatibility matrix (auto-deployed via GitHub Pages)

## Non-goals

- Not a replacement for ROCm, Ollama, or any inference engine
- Not a fork of upstream tools — only configs and glue
- Not a benchmarking tool

## License

MIT — see [LICENSE](LICENSE).
