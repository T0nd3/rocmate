#!/usr/bin/env python3
"""Build the static compatibility matrix HTML page from YAML tool configs."""

from __future__ import annotations

import html as html_mod
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
CONFIG_DIR = ROOT / "configs" / "tools"
OUT_DIR = ROOT / "site"

CHIPS: list[tuple[str, str]] = [
    ("gfx1100", "RX 7900 XT/XTX"),
    ("gfx1101", "RX 7800/7700 XT"),
    ("gfx1102", "RX 7600"),
    ("gfx1030", "RX 6800/6900"),
    ("gfx1201", "RX 9070"),
]

STATUS_ICON = {"tested": "✅", "partial": "🟡", "broken": "❌"}
STATUS_CLASS = {"tested": "tested", "partial": "partial", "broken": "broken"}


def load_configs() -> list[dict]:
    configs = []
    for path in sorted(CONFIG_DIR.glob("*.yaml")):
        with open(path) as f:
            data = yaml.safe_load(f)
        data["_slug"] = path.stem
        configs.append(data)
    return configs


def cell_html(chip_data: dict | None) -> str:
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


def build_html(configs: list[dict]) -> str:
    today = date.today().isoformat()
    github_url = "https://github.com/T0nd3/rocmate"

    header_chips = "".join(
        f'<th><span class="chip-id">{cid}</span>'
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
            if homepage
            else name
        )
        cells = "".join(cell_html(chips_data.get(cid)) for cid, _ in CHIPS)
        rows.append(
            f'<tr><td class="tool-name" title="{desc}">{name_link}</td>{cells}</tr>'
        )

    rows_html = "\n          ".join(rows)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>rocmate — AMD GPU Compatibility Matrix</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
      background: #f8fafc;
      color: #0f172a;
      min-height: 100vh;
    }}
    header {{
      background: #18181b;
      color: #fafafa;
      padding: 2rem 1.5rem;
      border-bottom: 3px solid #ED1C24;
    }}
    header h1 {{ font-size: 2rem; font-weight: 700; letter-spacing: -0.5px; }}
    header p {{ color: #a1a1aa; margin-top: 0.4rem; }}
    .install {{
      display: inline-block;
      margin-top: 1rem;
      background: #27272a;
      border: 1px solid #3f3f46;
      border-radius: 6px;
      padding: 0.35rem 0.8rem;
      font-family: monospace;
      font-size: 0.9rem;
      color: #86efac;
    }}
    main {{ max-width: 1100px; margin: 2rem auto; padding: 0 1rem; }}
    h2 {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 1rem; color: #374151; }}
    .table-wrap {{
      overflow-x: auto;
      border-radius: 10px;
      box-shadow: 0 1px 4px rgba(0,0,0,.08);
    }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; font-size: 0.92rem; }}
    th, td {{
      padding: 0.65rem 1rem;
      border-bottom: 1px solid #f1f5f9;
      text-align: center;
      white-space: nowrap;
    }}
    th {{ background: #f8fafc; font-weight: 600; border-bottom: 2px solid #e2e8f0; }}
    td.tool-name {{
      text-align: left;
      font-weight: 500;
      position: sticky;
      left: 0;
      background: #fff;
      border-right: 1px solid #e2e8f0;
      min-width: 170px;
    }}
    td.tool-name a {{ color: #0f172a; text-decoration: none; }}
    td.tool-name a:hover {{ text-decoration: underline; color: #ED1C24; }}
    .chip-id {{ font-family: monospace; font-size: 0.85rem; }}
    .gpu-name {{ font-size: 0.72rem; color: #64748b; font-weight: 400; margin-top: 2px; }}
    .chip-cell {{ font-size: 1.05rem; }}
    .chip-cell .rocm {{
      display: block;
      font-size: 0.68rem;
      color: #64748b;
      margin-top: 1px;
    }}
    .chip-cell.tested {{ background: #f0fdf4; }}
    .chip-cell.partial {{ background: #fffbeb; }}
    .chip-cell.broken {{ background: #fef2f2; }}
    .no-data {{ color: #cbd5e1; }}
    tr:last-child td {{ border-bottom: none; }}
    tr:hover td {{ filter: brightness(0.97); }}
    .legend {{
      display: flex;
      gap: 1.5rem;
      margin: 1.2rem 0 2rem;
      font-size: 0.88rem;
      color: #475569;
      flex-wrap: wrap;
    }}
    .cli-block {{
      background: #18181b;
      border-radius: 10px;
      padding: 1.2rem 1.5rem;
      font-family: monospace;
      font-size: 0.88rem;
      color: #e4e4e7;
      line-height: 1.8;
    }}
    .comment {{ color: #71717a; }}
    .cmd {{ color: #86efac; }}
    footer {{
      text-align: center;
      padding: 2.5rem 1rem 2rem;
      font-size: 0.82rem;
      color: #94a3b8;
    }}
    footer a {{ color: #94a3b8; text-decoration: none; }}
    footer a:hover {{ color: #ED1C24; }}
  </style>
</head>
<body>
  <header>
    <h1>rocmate</h1>
    <p>AMD GPU compatibility index for AI workloads</p>
    <code class="install">pip install rocmate</code>
  </header>

  <main>
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
  </main>

  <footer>
    Generated from
    <a href="{github_url}/tree/main/configs/tools" target="_blank" rel="noopener">YAML configs</a>
    · Updated {today}
    · <a href="{github_url}" target="_blank" rel="noopener">GitHub</a>
    · <a href="https://pypi.org/project/rocmate/" target="_blank" rel="noopener">PyPI</a>
  </footer>
</body>
</html>"""


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    configs = load_configs()
    page = build_html(configs)
    out = OUT_DIR / "index.html"
    out.write_text(page, encoding="utf-8")
    print(f"Built {out} ({len(configs)} tools, {len(page)} bytes)")


if __name__ == "__main__":
    main()
