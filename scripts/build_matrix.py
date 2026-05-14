#!/usr/bin/env python3
"""Build the static compatibility matrix and per-chip pages from YAML tool configs."""

from __future__ import annotations

import html as html_mod
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
CONFIG_DIR = ROOT / "configs" / "tools"
OUT_DIR = ROOT / "site"

CHIPS: list[tuple[str, str]] = [
    ("gfx1151", "Radeon 8060S / 8050S (Strix Halo)"),
    ("gfx1100", "RX 7900 XT/XTX"),
    ("gfx1101", "RX 7800/7700 XT"),
    ("gfx1102", "RX 7600"),
    ("gfx1030", "RX 6800/6900"),
    ("gfx1201", "RX 9070"),
]

STATUS_ICON = {"tested": "✅", "partial": "🟡", "broken": "❌"}
STATUS_CLASS = {"tested": "tested", "partial": "partial", "broken": "broken"}
STATUS_LABEL = {"tested": "tested", "partial": "partial", "broken": "broken"}

GITHUB_URL = "https://github.com/T0nd3/rocmate"

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_SHARED_CSS = """
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
      background: #f8fafc;
      color: #0f172a;
      min-height: 100vh;
    }
    header {
      background: #18181b;
      color: #fafafa;
      padding: 2rem 1.5rem;
      border-bottom: 3px solid #ED1C24;
    }
    header h1 { font-size: 2rem; font-weight: 700; letter-spacing: -0.5px; }
    header h1 a { color: inherit; text-decoration: none; }
    header h1 a:hover { color: #ED1C24; }
    header p { color: #a1a1aa; margin-top: 0.4rem; }
    .install {
      display: inline-block; margin-top: 1rem;
      background: #27272a; border: 1px solid #3f3f46; border-radius: 6px;
      padding: 0.35rem 0.8rem; font-family: monospace; font-size: 0.9rem; color: #86efac;
    }
    main { max-width: 1100px; margin: 2rem auto; padding: 0 1rem; }
    h2 { font-size: 1.1rem; font-weight: 600; margin-bottom: 1rem; color: #374151; }
    .back { display: inline-block; margin-bottom: 1.5rem; font-size: 0.88rem;
      color: #64748b; text-decoration: none; }
    .back:hover { color: #ED1C24; }
    .badge {
      display: inline-block; font-size: 0.78rem; font-weight: 600;
      padding: 0.15rem 0.55rem; border-radius: 99px;
    }
    .badge.tested  { background: #dcfce7; color: #15803d; }
    .badge.partial { background: #fef9c3; color: #a16207; }
    .badge.broken  { background: #fee2e2; color: #b91c1c; }
    .cli-block {
      background: #18181b; border-radius: 10px; padding: 1.2rem 1.5rem;
      font-family: monospace; font-size: 0.88rem; color: #e4e4e7; line-height: 1.8;
    }
    .comment { color: #71717a; }
    .cmd { color: #86efac; }
    footer {
      text-align: center; padding: 2.5rem 1rem 2rem;
      font-size: 0.82rem; color: #94a3b8;
    }
    footer a { color: #94a3b8; text-decoration: none; }
    footer a:hover { color: #ED1C24; }
"""


def _header(title: str, subtitle: str, show_install: bool = True) -> str:
    install = '<code class="install">pip install rocmate</code>' if show_install else ""
    return f"""  <header>
    <h1><a href="/">{html_mod.escape(title)}</a></h1>
    <p>{html_mod.escape(subtitle)}</p>
    {install}
  </header>"""


def _footer(today: str) -> str:
    return f"""  <footer>
    Generated from
    <a href="{GITHUB_URL}/tree/main/configs/tools" target="_blank" rel="noopener">YAML configs</a>
    · Updated {today}
    · <a href="{GITHUB_URL}" target="_blank" rel="noopener">GitHub</a>
    · <a href="https://pypi.org/project/rocmate/" target="_blank" rel="noopener">PyPI</a>
  </footer>"""


def _page(title: str, css_extra: str, header: str, body: str, footer: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html_mod.escape(title)}</title>
  <style>{_SHARED_CSS}{css_extra}</style>
</head>
<body>
{header}
{body}
{footer}
</body>
</html>"""


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_configs() -> list[dict]:
    configs = []
    for path in sorted(CONFIG_DIR.glob("*.yaml")):
        with open(path) as f:
            data = yaml.safe_load(f)
        data["_slug"] = path.stem
        configs.append(data)
    return configs


# ---------------------------------------------------------------------------
# Matrix page (index.html)
# ---------------------------------------------------------------------------

def _cell_html(chip_data: dict | None) -> str:
    if chip_data is None:
        return '<td class="no-data">—</td>'

    status = chip_data.get("status", "")
    icon = STATUS_ICON.get(status, "?")
    css = STATUS_CLASS.get(status, "")
    rocm = chip_data.get("tested_on_rocm", "")
    notes = (chip_data.get("notes") or "").strip()

    parts = [p for p in [f"ROCm {rocm}" if rocm else "", notes] if p]
    title = f' title="{html_mod.escape(chr(10).join(parts))}"' if parts else ""
    rocm_label = (
        f'<span class="rocm">{html_mod.escape(str(rocm))}</span>' if rocm else ""
    )
    return f'<td class="chip-cell {css}"{title}>{icon}{rocm_label}</td>'


def build_matrix_html(configs: list[dict], today: str) -> str:
    css_extra = """
    .table-wrap { overflow-x: auto; border-radius: 10px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
    table { width: 100%; border-collapse: collapse; background: #fff; font-size: 0.92rem; }
    th, td { padding: 0.65rem 1rem; border-bottom: 1px solid #f1f5f9;
      text-align: center; white-space: nowrap; }
    th { background: #f8fafc; font-weight: 600; border-bottom: 2px solid #e2e8f0; }
    th a { color: #0f172a; text-decoration: none; font-family: monospace; font-size: 0.85rem; }
    th a:hover { color: #ED1C24; }
    td.tool-name {
      text-align: left; font-weight: 500; position: sticky; left: 0;
      background: #fff; border-right: 1px solid #e2e8f0; min-width: 170px;
    }
    td.tool-name a { color: #0f172a; text-decoration: none; }
    td.tool-name a:hover { text-decoration: underline; color: #ED1C24; }
    .gpu-name { font-size: 0.72rem; color: #64748b; font-weight: 400; margin-top: 2px; }
    .chip-cell { font-size: 1.05rem; }
    .chip-cell .rocm { display: block; font-size: 0.68rem; color: #64748b; margin-top: 1px; }
    .chip-cell.tested { background: #f0fdf4; }
    .chip-cell.partial { background: #fffbeb; }
    .chip-cell.broken { background: #fef2f2; }
    .no-data { color: #cbd5e1; }
    tr:last-child td { border-bottom: none; }
    tr:hover td { filter: brightness(0.97); }
    .legend { display: flex; gap: 1.5rem; margin: 1.2rem 0 2rem;
      font-size: 0.88rem; color: #475569; flex-wrap: wrap; }
"""

    header_chips = "".join(
        f'<th><a href="{cid}/" title="All tools on {cid}">{cid}</a>'
        f'<br><span class="gpu-name">{gname}</span></th>'
        for cid, gname in CHIPS
    )

    rows = []
    for cfg in configs:
        name = html_mod.escape(cfg.get("name", cfg["_slug"]))
        homepage = html_mod.escape(cfg.get("homepage", ""))
        desc = html_mod.escape(cfg.get("description", ""))
        chips_data = cfg.get("chips", {})

        name_link = (
            f'<a href="{homepage}" target="_blank" rel="noopener">{name}</a>'
            if homepage else name
        )
        cells = "".join(_cell_html(chips_data.get(cid)) for cid, _ in CHIPS)
        rows.append(
            f'<tr><td class="tool-name" title="{desc}">{name_link}</td>{cells}</tr>'
        )

    rows_html = "\n          ".join(rows)

    body = f"""  <main>
    <h2>Compatibility Matrix</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th style="text-align:left">Tool</th>
            {header_chips}
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </div>

    <div class="legend">
      <span>✅ Tested — works out of the box</span>
      <span>🟡 Partial — workarounds needed</span>
      <span>— No data yet</span>
    </div>

    <h2>Use the CLI</h2>
    <div class="cli-block">
      <span class="comment"># Check your system</span><br>
      <span class="cmd">rocmate doctor</span><br><br>
      <span class="comment"># Show chip-specific config for a tool</span><br>
      <span class="cmd">rocmate show ollama --chip gfx1100</span><br><br>
      <span class="comment"># Install with the correct ENV vars</span><br>
      <span class="cmd">rocmate install ollama</span><br><br>
      <span class="comment"># Search tools by keyword</span><br>
      <span class="cmd">rocmate search llm</span>
    </div>
  </main>"""

    return _page(
        "rocmate — AMD GPU Compatibility Matrix",
        css_extra,
        _header("rocmate", "AMD GPU compatibility index for AI workloads"),
        body,
        _footer(today),
    )


# ---------------------------------------------------------------------------
# Per-chip page (gfx1100/index.html)
# ---------------------------------------------------------------------------

def _tool_card(cfg: dict, chip_data: dict) -> str:
    name = html_mod.escape(cfg.get("name", cfg["_slug"]))
    homepage = html_mod.escape(cfg.get("homepage", ""))
    status = chip_data.get("status", "")
    icon = STATUS_ICON.get(status, "")
    css = STATUS_CLASS.get(status, "")
    label = STATUS_LABEL.get(status, status)
    rocm = chip_data.get("tested_on_rocm", "")
    notes = (chip_data.get("notes") or "").strip()
    env_vars: dict = chip_data.get("env_vars") or {}
    hints: list = chip_data.get("install_hints") or []

    name_html = (
        f'<a href="{homepage}" target="_blank" rel="noopener">{name}</a>'
        if homepage else name
    )

    rocm_html = (
        f'<span class="rocm-tag">ROCm {html_mod.escape(str(rocm))}</span>'
        if rocm else ""
    )

    notes_html = (
        f'<p class="notes">{html_mod.escape(notes)}</p>' if notes else ""
    )

    env_html = ""
    if env_vars:
        lines = "".join(
            f'<li><code>export {html_mod.escape(k)}={html_mod.escape(v)}</code></li>'
            for k, v in env_vars.items()
        )
        env_html = f'<div class="section"><h4>ENV vars</h4><ul class="code-list">{lines}</ul></div>'

    hints_html = ""
    if hints:
        items = "".join(f'<li>{html_mod.escape(h)}</li>' for h in hints)
        hints_html = f'<div class="section"><h4>Install hints</h4><ul class="hints-list">{items}</ul></div>'

    return f"""<div class="card">
      <div class="card-header">
        <span class="tool-title">{name_html}</span>
        <span class="badge {css}">{icon} {label}</span>
        {rocm_html}
      </div>
      {notes_html}
      {env_html}
      {hints_html}
    </div>"""


def build_chip_html(chip_id: str, gpu_name: str, configs: list[dict], today: str) -> str:
    css_extra = """
    .back::before { content: "← "; }
    .card {
      background: #fff; border-radius: 10px; padding: 1.25rem 1.5rem;
      margin-bottom: 1rem; box-shadow: 0 1px 4px rgba(0,0,0,.07);
    }
    .card-header {
      display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;
      margin-bottom: 0.6rem;
    }
    .tool-title { font-size: 1.05rem; font-weight: 600; }
    .tool-title a { color: #0f172a; text-decoration: none; }
    .tool-title a:hover { color: #ED1C24; }
    .rocm-tag {
      font-size: 0.75rem; color: #64748b;
      background: #f1f5f9; padding: 0.15rem 0.5rem; border-radius: 99px;
    }
    .notes { font-size: 0.9rem; color: #475569; margin-bottom: 0.75rem; line-height: 1.6; }
    .section { margin-top: 0.75rem; }
    .section h4 { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em;
      color: #94a3b8; margin-bottom: 0.4rem; }
    .code-list, .hints-list { list-style: none; display: flex; flex-direction: column; gap: 0.25rem; }
    .code-list code {
      font-family: monospace; font-size: 0.85rem; background: #f8fafc;
      padding: 0.2rem 0.5rem; border-radius: 4px; color: #0f172a;
    }
    .hints-list li { font-size: 0.88rem; color: #374151; padding-left: 1rem;
      position: relative; line-height: 1.5; }
    .hints-list li::before { content: "›"; position: absolute; left: 0; color: #94a3b8; }
    .chip-meta { font-size: 0.88rem; color: #64748b; margin-bottom: 1.5rem; }
    .chip-meta code { font-family: monospace; background: #f1f5f9;
      padding: 0.1rem 0.4rem; border-radius: 4px; }
"""

    supported = [
        cfg for cfg in configs if chip_id in (cfg.get("chips") or {})
    ]

    cards = "\n    ".join(
        _tool_card(cfg, cfg["chips"][chip_id]) for cfg in supported
    )

    no_data = [cfg for cfg in configs if chip_id not in (cfg.get("chips") or {})]
    no_data_items = "".join(
        f'<li>{html_mod.escape(cfg.get("name", cfg["_slug"]))}</li>'
        for cfg in no_data
    )
    no_data_html = (
        f'<p style="margin-top:2rem;font-size:.88rem;color:#94a3b8">'
        f'No data yet for: {", ".join(cfg.get("name", cfg["_slug"]) for cfg in no_data)}</p>'
        if no_data else ""
    )

    body = f"""  <main>
    <a href="../" class="back">Back to matrix</a>
    <p class="chip-meta">Chip: <code>{html_mod.escape(chip_id)}</code> &nbsp;·&nbsp; {len(supported)} tool(s) with data</p>
    {cards}
    {no_data_html}
  </main>"""

    return _page(
        f"rocmate — {chip_id} ({gpu_name})",
        css_extra,
        _header("rocmate", f"{chip_id} — {gpu_name}", show_install=False),
        body,
        _footer(today),
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    configs = load_configs()
    today = date.today().isoformat()

    # Matrix
    matrix = build_matrix_html(configs, today)
    (OUT_DIR / "index.html").write_text(matrix, encoding="utf-8")
    print(f"  index.html ({len(configs)} tools)")

    # Per-chip pages
    for chip_id, gpu_name in CHIPS:
        chip_dir = OUT_DIR / chip_id
        chip_dir.mkdir(exist_ok=True)
        page = build_chip_html(chip_id, gpu_name, configs, today)
        (chip_dir / "index.html").write_text(page, encoding="utf-8")
        n = sum(1 for cfg in configs if chip_id in (cfg.get("chips") or {}))
        print(f"  {chip_id}/index.html ({n} tools)")

    print(f"Done — {1 + len(CHIPS)} pages built")


if __name__ == "__main__":
    main()
