# rocmate — Projektplan

> Persönliches Planungsdokument. Nicht für die Öffentlichkeit gedacht.
> Das öffentliche README liegt in `README.md`.

## TL;DR

`rocmate` ist ein **kuratierter Kompatibilitäts-Index + CLI-Tool** für AMD-GPUs und AI-Workloads. Es löst das Problem, dass Informationen darüber, was auf welcher AMD-Karte mit welcher ROCm-Version läuft, über hunderte Blogposts, GitHub-Issues und Discord-Threads verstreut sind.

**Zielnutzer:** Alle, die lokale AI auf AMD-Hardware laufen wollen — Indie-Devs, Homelabber, Datenschutz-bewusste Nutzer, Studenten, kleine Teams. Plattform: Linux primär, Windows ab v0.2.

**Mein Vorteil:** Ich bin selbst der Zielnutzer. Jede Friktion, die ich erlebe, ist ein Feature für andere.

---

## Warum dieses Projekt?

### Das Problem

AMD-GPUs sind preislich attraktiv für AI:
- RX 7900 XTX: 24 GB VRAM für deutlich weniger als eine RTX 4090
- Wachsender Markt durch Ryzen AI APUs und neue RX 9000-Serie
- Aber: 90 % der Nutzer bleiben am Setup hängen

Bestehende Quellen:
- **AMDs offizieller AI-Bundle** (Januar 2026): nur für RX 7700+ und Ryzen AI 300/400, nur paar Tools
- **Ollama-Docs**: listen nur Ollama selbst, keine anderen Tools
- **Blogposts**: veralten in 3 Monaten, oft nicht chip-spezifisch
- **GitHub-Issues**: fragmentiert, schwer durchsuchbar

→ Keine **konsolidierte, getestete, versionierte** Quelle, die sagt: "Hier ist die Config, die auf gfx1100 mit ROCm 6.3 für ComfyUI funktioniert."

### Warum gerade jetzt

- ROCm 6.x ist endlich brauchbar gereift
- PyTorch ROCm-Wheels sind offiziell und stabil
- AMD pusht massiv (Ryzen AI Max, RX 9070)
- NVIDIA-Tax wird vielen zu viel
- "Run local AI" wird Mainstream (privacy, kein Subscription)

### Warum ich

- Hab selbst RX 7900 XTX, hab den Schmerz durch
- Indie-Dev-Mindset (von Kaleo-App bis PoE-Overlay): bau funktionierende Tools
- Python-Stack passt zu meiner Komfortzone
- Neuro-sama-Projekt zwingt mich sowieso, halb diese Configs zu kuratieren

---

## Vision

### Was es ist

- Versions-kontrollierte YAML-Configs pro Tool × pro Chip
- CLI für Diagnostik (`doctor`) und Lookup (`show`)
- Community-driven: jeder PR mit getesteter Config ist Gold
- Klare Status-Labels: ✅ tested · 🟡 partial · ❌ broken

### Was es **nicht** ist

- Kein Fork von ROCm
- Kein eigener Inferenz-Server
- Kein Ersatz für Ollama/ComfyUI/etc.
- Kein Windows-first Tool (Linux primär, Windows später)
- Kein Benchmarking-Service (in v0.1 — vielleicht später als Submodul)

---

## Roadmap

### v0.1.0 — MVP (Launch-fähig)

**Status: Code steht, Configs für 3 Tools auf 4 Chips drin.**

- [x] CLI mit `doctor`, `show`, `list`
- [x] GPU-Detection via `rocminfo`
- [x] Pydantic-Validierung der YAMLs
- [x] Configs für Ollama, faster-whisper, ComfyUI
- [x] Chip-Coverage: gfx1100, gfx1030, gfx1201, gfx1034
- [x] Tests + GitHub Actions CI
- [x] MIT License + Contributing Guide
- [ ] **Auf eigenem RX 7900 XTX laufen lassen, Bugs fixen**
- [ ] **Naming final entscheiden** (rocmate vs gfx-toolkit vs rocforge)
- [ ] **PyPI-Name claimen + publishen**
- [ ] **GitHub Repo public + README mit echtem Screenshot**

**Geschätzter Aufwand:** 1 Wochenende für Finalisierung.

### v0.2.0 — Breite Tool-Coverage + Windows CLI

- [ ] Configs hinzufügen: vLLM, axolotl, Piper TTS, Coqui TTS, Stable Diffusion WebUI, llama.cpp, exllama
- [ ] Konfigs für gfx1101, gfx1102 (RX 7700/7800) inkl. Windows-Install-Hints
- [ ] Bessere `doctor`-Checks: Docker-GPU-Passthrough, Vulkan-Verfügbarkeit
- [ ] `rocmate doctor --tool <name>` — tool-spezifische Checks
- [ ] **Windows-Support für `doctor` und `show`**: GPU-Detection via `hipinfo` (primär) + WMI-Name→GFX-Lookup-Tabelle (Fallback), plattformbedingte Checks statt Linux-Gruppen

**Geschätzter Aufwand:** 2-3 Wochenenden.

### v0.3.0 — Auto-Install

- [ ] `rocmate install <tool>` — installiert Tool mit korrekten ENV-Vars und Pip-Indexen
- [ ] Dry-run-Modus (`--dry-run`)
- [ ] Docker-Compose-Snippets als Output-Option
- [ ] Rollback-Funktion (Snapshot von ENV vor Install)

**Hier wird's heikel.** Auto-Installer machen viele Annahmen. Lieber lange `--dry-run` als Default, dann erst opt-in für echte Installation.

### v0.4.0 — doctor --fix (System-Setup)

Ziel: `rocmate doctor` diagnostiziert, `rocmate doctor --fix` repariert — plattformübergreifend, chip-aware.

- [ ] `rocmate doctor --fix` — opt-in Setup-Modus, fragt vor jeder Aktion nach Bestätigung
- [ ] Stufe 1 (sicher): ENV-Vars setzen, Shell-Profile patchen
- [ ] Stufe 2 (braucht sudo/admin): Linux-Gruppen (`render`, `video`), Windows-HIP-Pfade
- [ ] Stufe 3 (riskant, explizit opt-in): ROCm/HIP SDK installieren — nur wenn Datenbasis breit und korrekt genug ist
- [ ] Plattformunabhängig: Linux (apt/pacman/dnf-Detection) + Windows (winget/manuell)
- [ ] `--dry-run` als Default für Stufe 3, `--yes` zum Übersteuern

**Voraussetzung:** Datenbasis aus v0.2/v0.3 muss solide sein, bevor hier automatisch installiert wird.

### v0.5.0 — Web Matrix

- [ ] Statische Website (Hugo/Astro) generiert aus YAMLs
- [ ] Filterbare Tabelle: "Welcher Chip × welches Tool"
- [ ] Pro-Chip-Seiten mit allen unterstützten Tools
- [ ] Pro-Tool-Seiten mit allen Chips
- [ ] Domain registrieren (.dev?)

### v1.0.0 — Stable

- [ ] Stabilisierte API
- [ ] Migration-Guide für Config-Schema-Änderungen
- [ ] Maintenance-Mode-Docs (was tun bei neuer ROCm-Version)

### Möglicherweise nie / sehr später

- Benchmarking-Submodul (siehe `rocm-bench`-Idee — eigenes Projekt wäre besser)
- Ryzen AI / NPU-Unterstützung (XDNA-Tooling zu unreif)

---

## Scope-Disziplin

**Das größte Risiko ist Feature-Creep.** Konkrete Versuchungen, denen ich widerstehen muss:

| Verlockung | Warum es schlecht ist |
|---|---|
| Sofort `install`-Befehl bauen | Datenbasis muss zuerst breit/korrekt sein, sonst installiere ich Müll |
| Eigenes Benchmark-System dranschrauben | Sprengt Scope, verdient eigenes Projekt |
| Windows-Support in v0.1 anfassen | Datenbasis und Linux-Pfad müssen zuerst stabil sein — Windows kommt in v0.2 |
| GUI bauen | Niemand braucht GUI für CLI-Tool, das man 2× pro Setup nutzt |
| Mit AMD-Hardware-Sponsoring locken lassen | Ja zu Hardware-Samples, nein zu Abhängigkeit |
| Eigene Inferenz-Engine bauen | Wir sind Klebemittel, nicht Konkurrent |

**Goldene Regel:** Wenn ein Feature die Frage "Welche Config funktioniert auf meinem Chip?" nicht direkter beantwortet, gehört es nicht in v0.x.

---

## Launch-Strategie

### Pre-Launch (vor v0.1.0 public)

1. **Eigenes Setup damit dokumentieren** — Ollama, faster-whisper, ComfyUI auf der 7900 XTX neu aufsetzen mit `rocmate show` als Guide. Findet Bugs.
2. **Screenshots** von `doctor` und `show ollama` für README
3. **Naming + Domain prüfen**
4. **PyPI-Name claimen**

### Launch-Tag

**Reihenfolge wichtig:** klein anfangen, dann größer.

1. **r/ROCm** (kleinste, freundlichste Community) — als "feedback wanted"
2. **r/Amd** (allgemein) — Fokus auf "billiger als NVIDIA für lokales AI"
3. **r/LocalLLaMA** (größte Tech-Community) — Fokus auf "Ollama-Setup auf AMD endlich nicht mehr nervig"
4. **HackerNews** — "Show HN: rocmate – Curated AMD GPU compatibility for AI tools"

**Nicht alles am selben Tag.** Reddit-Posts auf 3-4 Tage verteilen, HN am Wochenende (mehr Traffic).

### Posting-Stil

**Nicht:** "Mein neues Projekt!" 
**Sondern:** "Ich war frustriert, dass es keine konsolidierte Quelle für AMD-AI-Configs gibt, also habe ich angefangen, eine zu bauen. Hier ist v0.1.0 — ich brauche eure Configs für die Chips, die ich nicht habe."

**Klar machen:**
- Was funktioniert (3 Tools auf 4 Chips)
- Was fehlt (alles andere)
- Wie man beiträgt (PR-Template, 5-Min-Aufwand)
- Was es **nicht** ist (kein Fork, kein Installer-Magic)

### Erfolgs-Indikatoren

**Realistisch nach 2 Wochen:**
- 50-200 GitHub-Stars
- 1-3 externe PRs mit Configs
- 5-20 Issues mit "läuft nicht auf gfx10XX"
- 100-500 PyPI-Downloads

**Wenn nach 2 Wochen <20 Stars:** Naming/Positionierung überdenken, nicht aufgeben.

**Wenn nach 2 Monaten <5 externe PRs:** Contribution-Hürde senken (template-driven Issue → auto-PR?).

---

## Tech-Entscheidungen

| Entscheidung | Begründung |
|---|---|
| Python 3.11+ | Passt zu meinem Stack, einfache CLI-Sprache, alle Zielnutzer haben Python |
| Typer (statt argparse/click) | Modern, Type-Hints, schöne Auto-Help |
| Rich für Output | Tabellen + Farben kostenlos, professioneller Look |
| Pydantic für YAML-Validierung | Fehler früh fangen, Config-Schema dokumentiert sich selbst |
| YAML statt TOML/JSON für Configs | Multi-Line-Strings für Notes, Kommentare möglich, Community-freundlicher |
| Hatchling als Build-Backend | Modern, schnell, sauber mit `force-include` für YAMLs |
| MIT-Lizenz | Maximal permissive, keine Reibung für Contributors |
| uv für Dev-Setup | Schnell, modern — aber pip-fallback dokumentieren |

---

## Risiken

| Risiko | Wahrscheinlichkeit | Gegenmaßnahme |
|---|---|---|
| AMD baut selbst was Vergleichbares | Mittel | Wir bleiben das vendor-neutrale Open-Source-Tool, AMD bewirbt nur eigene Tools |
| ROCm-Versionen brechen Configs alle 6 Monate | Hoch | Configs versionieren, alte ROCm-Versionen markieren |
| Niemand contributed | Hoch | Beitragen muss trivial sein (5 Min, ein YAML-File), explizit nach gfx10XX-Chips fragen |
| Ich verliere Interesse nach 3 Monaten | Mittel | Scope eng halten, keine versprochenen Features die zur Pflicht werden |
| Naming-Konflikt mit existierender Library | Niedrig | PyPI prüfen vor Launch |
| AMD Markenrechts-Stress | Niedrig | Neutraler Name (nicht "Radeon-X"), Disclaimer im README |

---

## Persönliche Erinnerungen

- **Nicht alles selbst dokumentieren wollen.** Ein Issue-Template "Config für gfx10XX einreichen" ist mehr wert als 20 Stunden eigene Recherche zu Chips, die ich nicht besitze.
- **Code-Qualität ist Marketing.** Sauberer Code + Tests + CI signalisiert "diese Maintainerin meint es ernst" — und das zieht Contributors.
- **Antworte auf jedes Issue innerhalb 48h** in den ersten 4 Wochen. Danach kann's lockerer werden, aber der frühe Eindruck zählt.
- **Kein Burn-out.** Wenn ein Wochenende keine Lust → kein Wochenende. Open Source ist Marathon.
- **Spaß steht im Vordergrund.** Das Projekt sollte sich gut anfühlen, sonst überlebt es nicht.

---

## Offene Fragen (vor Launch klären)

- [ ] Endgültiger Name: `rocmate` / `gfx-toolkit` / `rocforge` / `amdgpu-ai` / ?
- [ ] Domain registrieren? (rocmate.dev / .io / kein Web in v0.1?)
- [ ] Eigene GitHub-Org (`rocmate-project`) oder unter persönlichem Account?
- [ ] Issue-Templates wie genau strukturieren?
- [ ] Discord/Matrix für Community oder erstmal nur GitHub Discussions?

---

*Stand: Initial. Wird mit dem Projekt mitwachsen.*
