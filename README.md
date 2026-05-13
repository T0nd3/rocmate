# rocmate

> Get AMD GPUs running with AI tools — without the rabbit hole.

`rocmate` is a curated compatibility index and CLI for running modern AI workloads on AMD GPUs via ROCm. It tells you what works on your specific card, what to set, and what to avoid — based on configurations that real users have tested.

## Why?

AMD GPUs offer great VRAM-per-dollar (especially the RX 7900 XTX with 24 GB), but getting Ollama, ComfyUI, faster-whisper, or axolotl to actually use the GPU still involves hunting through blog posts, GitHub issues, and Discord threads. Information is scattered, often outdated, and rarely specific to your chip generation (gfx1030 vs gfx1100 vs gfx1201).

`rocmate` consolidates this knowledge into one place — version-controlled, testable, community-maintained.

## Quickstart

```bash
# Install (Python 3.11+)
pipx install rocmate

# Check your system
rocmate doctor

# Show the tested config for a tool
rocmate show ollama
```

Example output:

```
$ rocmate doctor
✓ GPU detected: AMD Radeon RX 7900 XTX (gfx1100)
✓ ROCm 6.3.1 installed
✗ User not in 'render' group
  → sudo usermod -aG render $USER && newgrp render
⚠ HSA_OVERRIDE_GFX_VERSION not set
  → export HSA_OVERRIDE_GFX_VERSION=11.0.0
```

## Supported tools (v0.1.0)

| Tool | gfx1100 (RX 7900 XT/XTX) | gfx1030 (RX 6800/6900) | gfx1201 (RX 9070) |
|------|:-:|:-:|:-:|
| Ollama | ✅ | ✅ | 🟡 |
| faster-whisper | ✅ | 🟡 | — |
| ComfyUI | ✅ | 🟡 | — |

✅ tested · 🟡 partial / workarounds needed · ❌ not working

## Status

Early-stage. Currently maintained by [@tonde](https://github.com/tonde) on an RX 7900 XTX. Contributions for other AMD chips are very welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Roadmap

- [x] `rocmate doctor` — system diagnostic
- [x] `rocmate show <tool>` — display tested config
- [ ] Windows / HIP SDK support (`doctor` + `show`)
- [ ] `rocmate install <tool>` — automated installer with correct ENV
- [ ] `rocmate doctor --fix` — auto-setup for ROCm/HIP, groups, and ENV vars
- [ ] Web-facing compatibility matrix

## Non-goals

- Not a replacement for ROCm, Ollama, or any inference engine
- Not a fork of upstream tools — only configs and glue
- Not a benchmarking tool

## License

MIT — see [LICENSE](LICENSE).
