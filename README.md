# TexCol

TexCol is a Python + Tkinter desktop app that converts LaTeX formulas and TikZ snippets into clean SVG files.

The workflow is: write LaTeX, generate, preview, then export the SVG or drag it into another app.

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Project Structure](#project-structure)
4. [Requirements](#requirements)
5. [Windows Installation Tutorial](#windows-installation-tutorial)
6. [Linux Installation](#linux-installation)
7. [macOS Notes](#macos-notes)
8. [Run](#run)
9. [Usage](#usage)
10. [TikZ Mode](#tikz-mode)
11. [Compiler Selection](#compiler-selection)
12. [Preamble Configuration](#preamble-configuration)
13. [Export, Drag and Clipboard](#export-drag-and-clipboard)
14. [Optional Linux Desktop Launcher](#optional-linux-desktop-launcher)
15. [Troubleshooting](#troubleshooting)
16. [Known Limitations](#known-limitations)
17. [Roadmap](#roadmap)
18. [License](#license)

## Overview

TexCol compiles your LaTeX input with `latex`, `pdflatex`, `lualatex`, or `xelatex`, converts the result to SVG with `dvisvgm`, and renders a preview in the GUI.

The app stores temporary files in `TexCol_DnD_tmp/` inside the project folder, so it works with normal Windows, Linux, and macOS paths.

## Features

- Preamble editor (`preamble.tex`) with persistent save
- Formula editor with LaTeX input
- Input mode toggle: `Formula` or `TikZ`
- Compiler selector: `pdflatex`, `lualatex`, `xelatex`
- One-click SVG generation
- Render cache for repeated formulas and preambles
- Live preview in the app
- Drag and drop support for generated SVG files
- Download/export SVG to any location
- Modern in-app dialogs for info, warning, and error output
- Enhanced compile-error dialog with short summary and expandable full log
- Lightweight LaTeX syntax highlighting in both editors
- Runtime cleanup button for temporary files
- Tight bounding-box handling for many display-math cases

## Project Structure

```text
<repo-root>/
|-- TexCol.py              # Main desktop app
|-- preamble.tex           # Persistent LaTeX preamble
|-- requirements.txt       # Python dependencies
|-- texcol.png             # App icon
|-- icons/                 # Button icons
|   |-- clear.png
|   |-- download.png
|   |-- generate.png
|   `-- save.png
|-- TexCol_DnD_tmp/        # Runtime folder, auto-created and gitignored
`-- README.md
```

## Requirements

### System

- Windows 10/11, Linux, or macOS
- Python 3.10+
- LaTeX tools available in `PATH`:
  - `latex`
  - `pdflatex`
  - `dvisvgm`
  - Optional: `lualatex`, `xelatex`

### Python Packages

Install the Python packages from `requirements.txt`:

```bash
pip install -r requirements.txt
```

The file currently installs:

- `Pillow`
- `cairosvg`
- `tkinterdnd2`

## Windows Installation Tutorial

These steps use PowerShell from the project folder.

### 1. Install Python

Install Python 3.10 or newer from the official Python installer or with `winget`.

Check that Python is available:

```powershell
py --version
```

If `py` is not found, reinstall Python and enable the option that adds Python to `PATH`.

### 2. Install LaTeX

Install one LaTeX distribution for Windows:

- MiKTeX, recommended for most users
- TeX Live, also supported

During installation, allow PATH integration if the installer offers it. After installation, close and reopen PowerShell, then verify the commands:

```powershell
where latex
where pdflatex
where dvisvgm
```

If you want to use the `lualatex` or `xelatex` compiler options, verify those too:

```powershell
where lualatex
where xelatex
```

If any command is missing, add your LaTeX distribution's `bin` folder to the Windows `PATH`, then reopen PowerShell.

### 3. Clone or Open the Project

If you use Git:

```powershell
git clone https://github.com/<YOUR_USERNAME>/<YOUR_REPO>.git
cd <YOUR_REPO>
```

If you downloaded a ZIP, extract it and open PowerShell inside the extracted folder.

### 4. Create the Virtual Environment

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script activation, run this once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate again:

```powershell
.\.venv\Scripts\Activate.ps1
```

Command Prompt alternative:

```bat
.venv\Scripts\activate.bat
```

### 5. Install Python Dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 6. Start TexCol

```powershell
python TexCol.py
```

At first run, TexCol creates `TexCol_DnD_tmp/` in the project folder for temporary files, drag-and-drop output, and cache data.

### 7. Optional Windows Launcher

Create a file named `texcol.bat` in the project folder:

```bat
@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python TexCol.py
```

After that, double-click `texcol.bat` to start the app.

## Linux Installation

On Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-tk texlive-latex-base dvisvgm
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python TexCol.py
```

Optional engines:

```bash
sudo apt install -y texlive-luatex texlive-xetex
```

If your formulas require additional LaTeX packages, install the matching TeX packages on your system.

## macOS Notes

Install Python 3.10+ and a LaTeX distribution such as MacTeX or BasicTeX. Then use the same virtual-environment flow:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python TexCol.py
```

Make sure `latex`, `pdflatex`, and `dvisvgm` are available in your shell `PATH`.

## Run

From the project root, with the virtual environment active:

```bash
python TexCol.py
```

## Usage

1. Open TexCol.
2. Edit the **Preamble** section, or keep the default.
3. Choose the input mode:
   - **Formula** for math expressions and equations
   - **TikZ** for diagrams and drawings
4. Type your content in the editor.
5. Choose the compiler from the top-right dropdown.
6. Click **Generate**.
7. Check the **Preview**.
8. Click **Download** to save SVG, or drag the preview into a compatible app.

## TikZ Mode

Use **TikZ** mode when you want to render diagrams instead of plain math formulas.

- If your input already contains a `tikzpicture` environment, TexCol uses it as-is.
- If not, TexCol automatically wraps your input in:

```tex
\begin{tikzpicture}
...
\end{tikzpicture}
```

- Rendering uses the `standalone` class with preview-based cropping.
- Keep required TikZ packages and libraries in your preamble, for example `\usepackage{tikz}` and `\usetikzlibrary{positioning}`.

## Compiler Selection

TexCol supports three compiler options from the UI dropdown:

- `pdflatex`, default and fastest for common workflows
- `lualatex`, useful for modern font and unicode workflows
- `xelatex`, useful for system font workflows

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

You can add custom packages and macros based on your use case.

## Export, Drag and Clipboard

- **Download** saves the current SVG to a path you choose.
- **Drag and drop** uses `TexCol_DnD_tmp/formula.svg`.
- Clipboard support is best-effort:
  - Linux uses `wl-copy` or `xclip` when available.
  - macOS uses `pbcopy` for SVG XML text when available.
  - Windows falls back to copying the SVG XML as text through Tk.

For PowerPoint, Word, browser editors, and design tools, **Download** or drag-and-drop is usually the most reliable workflow.

## Optional Linux Desktop Launcher

This creates a launcher in the Ubuntu applications menu.

### 1. Create Launcher Script

Set your project folder first:

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
exec python TexCol.py
EOF
chmod +x "$HOME/bin/texcol-launcher.sh"
```

### 2. Create Desktop Entry

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

### 3. Refresh Desktop Database

```bash
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
```

## Troubleshooting

### Windows: `Command not found: pdflatex`, `latex`, or `dvisvgm`

Close and reopen PowerShell, then run:

```powershell
where latex
where pdflatex
where dvisvgm
```

If a command is still missing, add the LaTeX distribution `bin` folder to the Windows `PATH`.

### Windows: PowerShell Cannot Activate `.venv`

Run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate again:

```powershell
.\.venv\Scripts\Activate.ps1
```

### MiKTeX Asks to Install Missing Packages

Allow MiKTeX to install missing packages when prompted. Some formulas require extra packages beyond the base distribution.

### `PIL`, `cairosvg`, or `tkinterdnd2` Import Error

Make sure your virtual environment is active, then run:

```bash
pip install -r requirements.txt
```

If `cairosvg` reports a missing Cairo DLL on Windows, install a Cairo/GTK runtime, restart the terminal, and reinstall the dependencies.

### Linux: `tkinter` Import Error

On Ubuntu/Debian:

```bash
sudo apt install python3-tk
```

### Formula Appears Clipped

TexCol applies tight bounding-box logic for many common environments. Some complex display environments may still require manual adjustments, for example using `aligned` or `gathered` variants.

## Known Limitations

- No packaged installer yet (`.exe`, `.msi`, `.deb`, AppImage, etc.)
- Clipboard behavior depends on the target application and operating system
- Dependency management is intentionally lightweight and uses `requirements.txt`

## Roadmap

- Add packaged Windows and Linux installers
- Add automated tests for the render pipeline
- Add screenshots or GIF examples to README

## License

No license is specified yet.
