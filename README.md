# TexCol

TexCol is a desktop app built with Python + Tkinter to convert LaTeX formulas into clean SVG files.

It is designed for a fast workflow: write a formula, generate, preview, then export or drag the SVG where you need it.

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Project Structure](#project-structure)
4. [Requirements](#requirements)
5. [Installation](#installation)
6. [Run](#run)
7. [Usage](#usage)
8. [Preamble Configuration](#preamble-configuration)
9. [Install as an Ubuntu App](#install-as-an-ubuntu-app)
10. [Troubleshooting](#troubleshooting)
11. [Known Limitations](#known-limitations)
12. [Roadmap](#roadmap)
13. [License](#license)

## Overview

TexCol compiles your LaTeX formula with `pdflatex`, converts the result to SVG with `dvisvgm`, and renders a preview in the GUI.

The main goal is high quality vector math output with a simple desktop interface.

## Features

- Preamble editor (`preamble.tex`) with persistent save
- Formula editor with LaTeX input
- One-click SVG generation
- Live preview in the app
- Drag and drop support for generated SVG
- Download/export SVG to any location
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
└── README.md
```

## Requirements

### System

- Linux desktop (Ubuntu/Debian recommended)
- Python 3.10+
- LaTeX tools in PATH:
  - `pdflatex`
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

## Run

From the project root:

```bash
python3 TexCol.py
```

At first run, TexCol creates `TexCol_DnD_tmp/` inside the project folder and uses it for temporary runtime artifacts.

## Usage

1. Open TexCol.
2. Edit the **Preamble** section (or keep defaults).
3. Type your formula in **Formula**.
4. Click **Generate**.
5. Check the **Preview**.
6. Click **Download** to save SVG, or drag and drop directly into supported apps.

## Preamble Configuration

TexCol loads `preamble.tex` at startup and saves it with the **Save** button.

Default example:

```tex
\usepackage{amsmath,amssymb,mathtools}
\usepackage{physics}
\usepackage{braket}
\usepackage{slashed}
```

You can add custom packages/macros based on your use case.

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
