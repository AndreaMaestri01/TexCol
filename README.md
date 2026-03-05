# TexCol

TexCol is a desktop app built with Python + Tkinter to convert LaTeX formulas into clean SVG files.

It is designed for a fast workflow: write a formula, generate, preview, then export or drag the SVG where you need it.

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Project Structure](#project-structure)
4. [Requirements](#requirements)
5. [Installation](#installation)
6. [Quick Start](#quick-start)
7. [Run](#run)
8. [Usage](#usage)
9. [TikZ Mode](#tikz-mode)
10. [Compiler Selection](#compiler-selection)
11. [Preamble Configuration](#preamble-configuration)
12. [Export and Clipboard](#export-and-clipboard)
13. [Install as an Ubuntu App](#install-as-an-ubuntu-app)
14. [Troubleshooting](#troubleshooting)
15. [Known Limitations](#known-limitations)
16. [Roadmap](#roadmap)
17. [License](#license)

## Overview

TexCol compiles your LaTeX formula with the selected compiler (`pdflatex`, `lualatex`, or `xelatex`), converts the result to SVG with `dvisvgm`, and renders a preview in the GUI.

The main goal is high quality vector math output with a simple desktop interface.

## Features

- Preamble editor (`preamble.tex`) with persistent save
- Formula editor with LaTeX input
- Input mode toggle: `Formula` or `TikZ`
- Compiler selector: `pdflatex`, `lualatex`, `xelatex`
- One-click SVG generation
- Render cache for repeated formulas/preambles (faster regeneration)
- Live preview in the app
- Drag and drop support for generated SVG
- Download/export SVG to any location
- Modern in-app dialogs for info/warning/error output
- Enhanced compile-error dialog with short summary + expandable full log
- Rounded custom scrollbars for a cleaner UI
- Lightweight LaTeX syntax highlighting in both editors
- Runtime cleanup button for temporary files
- Tight bounding-box handling for many display-math cases

## Project Structure

```text
<repo-root>/
├── TexCol.py              # Main desktop app
├── preamble.tex           # Persistent LaTeX preamble
├── texcol.png             # App icon
├── icons/                 # Button icons
│   ├── clear.png
│   ├── download.png
│   ├── generate.png
│   └── save.png
├── TexCol_DnD_tmp/        # Runtime folder (auto-created, gitignored)
│   └── cache/             # Render cache (auto-managed)
└── README.md
```

## Requirements

### System

- Linux desktop (Ubuntu/Debian recommended)
- Python 3.10+
- LaTeX tools in PATH:
  - `pdflatex`
  - Optional: `lualatex`, `xelatex` (if you want to use them from the compiler selector)
  - `dvisvgm`

### Python packages

- `Pillow`
- `cairosvg`
- `tkinterdnd2`

Also install Tk bindings (`python3-tk` on Ubuntu/Debian).

## Installation

1. Clone the repository.

```bash
git clone https://github.com/<YOUR_USERNAME>/<YOUR_REPO>.git
cd <YOUR_REPO>
```

2. Create and activate a virtual environment.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install Python dependencies.

```bash
pip install --upgrade pip
pip install pillow cairosvg tkinterdnd2
```

4. Install required system packages (Ubuntu/Debian).

```bash
sudo apt update
sudo apt install -y python3-tk texlive-latex-base dvisvgm
```

If your formulas require additional LaTeX packages, install the matching TeX packages on your system.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip pillow cairosvg tkinterdnd2
sudo apt install -y python3-tk texlive-latex-base dvisvgm
python3 TexCol.py
```

## Run

From the project root:

```bash
python3 TexCol.py
```

At first run, TexCol creates `TexCol_DnD_tmp/` inside the project folder and uses it for temporary runtime artifacts and render cache data.

## Usage

1. Open TexCol.
2. Edit the **Preamble** section (or keep defaults).
3. Choose the input mode:
   - **Formula** for math expressions/equations
   - **TikZ** for diagrams and drawings
4. Type your content in the editor.
5. Choose the compiler from the top-right dropdown (`pdflatex`, `lualatex`, `xelatex`).
6. Click **Generate**.
7. Check the **Preview**.
8. Click **Download** to save SVG, or drag and drop directly into supported apps.

## TikZ Mode

Use **TikZ** mode when you want to render diagrams instead of plain math formulas.

- If your input already contains a `tikzpicture` environment, TexCol uses it as-is.
- If not, TexCol automatically wraps your input in:

```tex
\begin{tikzpicture}
...
\end{tikzpicture}
```

- Rendering is done with the `standalone` class in TikZ mode, so output is tightly cropped and ready for SVG export.
- Keep required TikZ packages/libraries in your preamble (for example `\usepackage{tikz}` and `\usetikzlibrary{positioning}`).

## Compiler Selection

TexCol supports three LaTeX compilers from the UI dropdown:

- `pdflatex` (default, fastest for common workflows)
- `lualatex` (useful for modern font/unicode workflows)
- `xelatex` (useful for system font workflows)

The selected compiler is part of the render cache key, so switching compiler forces a correct re-render.

## Preamble Configuration

TexCol loads `preamble.tex` at startup and saves it with the **Save** button.

Default example:

```tex
\usepackage{amsmath,amssymb,mathtools}
\usepackage{braket}
\usepackage{slashed}
\usepackage{tikz}
\usetikzlibrary{positioning,matrix,fit,decorations.markings}
\usepackage{graphicx}
\newcommand{\scalemath}[2]{\scalebox{#1}{$#2$}}
```

You can add custom packages/macros based on your use case.

## Export and Clipboard

- **Download** saves the current SVG to a path you choose.
- **Drag and drop** uses a runtime SVG file in `TexCol_DnD_tmp/` for quick transfer to compatible apps.
- **Copy SVG** tries Wayland (`wl-copy`) first, then X11 (`xclip`), using URI/file and `image/svg+xml` fallback modes.

## Install as an Ubuntu App

This creates a launcher in the Ubuntu applications menu.

### 1. Create launcher script

Set your project folder first (absolute path of your local clone):

```bash
PROJECT_DIR="$HOME/path/to/<YOUR_REPO>"
```

Create the launcher script:

```bash
mkdir -p "$HOME/bin"
cat > "$HOME/bin/texcol-launcher.sh" <<EOF
#!/usr/bin/env bash
cd "$PROJECT_DIR" || exit 1
source .venv/bin/activate
exec python3 TexCol.py
EOF
chmod +x "$HOME/bin/texcol-launcher.sh"
```

### 2. Create desktop entry

```bash
mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/texcol.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=TexCol
Comment=LaTeX to SVG formula tool
Exec=$HOME/bin/texcol-launcher.sh
Icon=$PROJECT_DIR/texcol.png
Terminal=false
Categories=Education;Utility;
StartupNotify=true
EOF
chmod +x "$HOME/.local/share/applications/texcol.desktop"
```

### 3. Refresh desktop database (optional)

```bash
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
```

### 4. Launch

- Open Ubuntu app menu
- Search for `TexCol`
- Optional: pin it to the dock

## Troubleshooting

### `Command not found: pdflatex` or `dvisvgm`

Install missing LaTeX tools:

```bash
sudo apt install texlive-latex-base dvisvgm
```

If you selected `lualatex` or `xelatex`, ensure those binaries are installed too (typically via `texlive-luatex` and `texlive-xetex` on Ubuntu/Debian).

### `Command not found: lualatex` or `xelatex`

Install optional engines:

```bash
sudo apt install texlive-luatex texlive-xetex
```

Or switch compiler back to `pdflatex` from the dropdown.

### `tkinter` import error

```bash
sudo apt install python3-tk
```

### `PIL` / `cairosvg` / `tkinterdnd2` import error

Make sure your virtual environment is active, then run:

```bash
pip install pillow cairosvg tkinterdnd2
```

### Formula appears clipped

TexCol applies tight bounding-box logic for many common environments. Some complex display environments may still require manual adjustments (for example using `aligned`/`gathered` variants).

## Known Limitations

- Linux-first desktop workflow
- No packaged installer yet (`.deb`, AppImage, etc.)
- Dependency management is currently documented in README (no lockfile-based packaging yet)

## Roadmap

- Add `requirements.txt` / `pyproject.toml`
- Add packaging and distribution workflow
- Add automated tests for the render pipeline
- Add screenshots/GIF examples to README

## License

No license is specified yet.
