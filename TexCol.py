import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox, filedialog
import subprocess
from pathlib import Path
import shutil
import os
import io
import atexit
import time
import threading
import hashlib
import webbrowser
import re
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

from PIL import Image, ImageTk
import cairosvg
from tkinterdnd2 import TkinterDnD, DND_FILES, COPY


# ----------------------------
# Paths / config
# ----------------------------
APP_DIR = Path(__file__).resolve().parent

LEGACY_APP_DIR = Path.home() / "TexCol_app"
PREAMBLE_FILE = APP_DIR / "preamble.tex"
LEGACY_PREAMBLE_FILE = LEGACY_APP_DIR / "preamble.tex"

# Dedicated folder (no /tmp): visible to Firefox (snap-safe)
RUNTIME_DIR = Path("/home/andrea-maestri/user/TexCol_app/TexCol_DnD_tmp")


# ----------------------------
# Helpers
# ----------------------------
def _safe_wipe_dir(dir_path: Path) -> None:
    """
    Delete ALL contents inside the folder while keeping the folder itself.
    Minimal safety check: requires path name to contain 'TexCol_DnD_tmp' and be deep enough.
    """
    dp = dir_path.resolve()
    if "TexCol_DnD_tmp" not in dp.name:
        raise RuntimeError(f"Refuse wipe: path name not expected: {dp}")

    # Avoid disasters like wiping HOME or root paths
    if len(dp.parts) < 5:
        raise RuntimeError(f"Refuse wipe: path too shallow: {dp}")

    dp.mkdir(parents=True, exist_ok=True)

    for child in dp.iterdir():
        try:
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)
        except Exception:
            pass


class _RuntimeHTTPHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        return


class RoundedCard(tk.Canvas):
    def __init__(
        self,
        master,
        *,
        bg,
        fill,
        border,
        radius=22,
        padding=16,
        **kwargs,
    ):
        super().__init__(master, bg=bg, highlightthickness=0, bd=0, **kwargs)
        self.fill = fill
        self.border = border
        self.radius = radius
        self.padding = padding

        self.inner = tk.Frame(self, bg=self.fill)
        self._inner_id = self.create_window(
            self.padding, self.padding, anchor="nw", window=self.inner
        )

        self.bind("<Configure>", self._on_configure)

    def _rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        r = min(r, max(1, (x2 - x1) // 2), max(1, (y2 - y1) // 2))
        points = [
            x1 + r, y1,
            x1 + r, y1,
            x2 - r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1 + r,
            x1, y1,
        ]
        return self.create_polygon(points, smooth=True, splinesteps=36, **kwargs)

    def _on_configure(self, event=None):
        self.delete("card")

        w = max(2, self.winfo_width() - 1)
        h = max(2, self.winfo_height() - 1)

        self._rounded_rect(
            1,
            1,
            w,
            h,
            self.radius,
            fill=self.fill,
            outline=self.border,
            width=1,
            tags="card",
        )
        self.tag_lower("card")

        self.coords(self._inner_id, self.padding, self.padding)
        self.itemconfigure(
            self._inner_id,
            width=max(1, w - 2 * self.padding),
            height=max(1, h - 2 * self.padding),
        )




class IconButton(tk.Canvas):
    def __init__(
        self,
        master,
        *,
        text,
        command,
        bg,
        fill,
        hover_fill,
        fg,
        image=None,
        radius=16,
        font=("DejaVu Sans", 10, "bold"),
        padx=16,
        pady=10,
        gap=8,
        min_width=0,
    ):
        self.font = tkfont.Font(font=font)
        self.text = text
        self.command = command
        self.outer_bg = bg
        self.fill = fill
        self.hover_fill = hover_fill
        self.current_fill = fill
        self.fg = fg
        self.image = image
        self.radius = radius
        self.padx = padx
        self.pady = pady
        self.gap = gap if image and text else 0

        text_w = self.font.measure(text) if text else 0
        image_w = image.width() if image else 0
        content_w = text_w + image_w + self.gap
        width = max(min_width, content_w + 2 * padx)
        height = max(42, self.font.metrics("linespace") + 2 * pady)

        super().__init__(
            master,
            width=width,
            height=height,
            bg=bg,
            highlightthickness=0,
            bd=0,
            relief="flat",
            cursor="hand2",
        )

        self.bind("<Configure>", self._redraw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonRelease-1>", self._on_click)

        self._redraw()

    def _rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        r = min(r, max(1, (x2 - x1) // 2), max(1, (y2 - y1) // 2))
        points = [
            x1 + r, y1,
            x1 + r, y1,
            x2 - r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1 + r,
            x1, y1,
        ]
        return self.create_polygon(points, smooth=True, splinesteps=36, **kwargs)

    def _redraw(self, event=None):
        self.delete("all")
        w = max(2, self.winfo_width() - 1)
        h = max(2, self.winfo_height() - 1)

        self._rounded_rect(
            1,
            1,
            w,
            h,
            self.radius,
            fill=self.current_fill,
            outline=self.current_fill,
            width=1,
        )

        text_w = self.font.measure(self.text) if self.text else 0
        image_w = self.image.width() if self.image else 0
        content_w = text_w + image_w + (self.gap if self.image and self.text else 0)
        start_x = max((w - content_w) // 2, self.padx)

        if self.image is not None:
            self.create_image(start_x + image_w // 2, h // 2, image=self.image)
            start_x += image_w + (self.gap if self.text else 0)

        if self.text:
            self.create_text(
                start_x,
                h // 2,
                text=self.text,
                fill=self.fg,
                font=self.font,
                anchor="w",
            )

    def _on_enter(self, event=None):
        self.current_fill = self.hover_fill
        self._redraw()

    def _on_leave(self, event=None):
        self.current_fill = self.fill
        self._redraw()

    def _on_click(self, event=None):
        if callable(self.command):
            self.command()

    def set_theme(self, *, fill=None, hover_fill=None, fg=None):
        """Dynamically update button colors (used for toggle buttons)."""
        if fill is not None:
            self.fill = fill
            self.current_fill = fill
        if hover_fill is not None:
            self.hover_fill = hover_fill
        if fg is not None:
            self.fg = fg
        self._redraw()




class RoundedScrollbar(tk.Canvas):
    """Minimal vertical scrollbar with no arrows and rounded thumb."""

    def __init__(
        self,
        master,
        *,
        command,
        width=12,
        track="#f0f0f0",
        track_border="#d0d0d0",
        thumb="#7f1737",
        thumb_active="#69122e",
        radius=10,
        bg=None,
        **kwargs,
    ):
        super().__init__(
            master,
            width=width,
            highlightthickness=0,
            bd=0,
            relief="flat",
            bg=(bg if bg is not None else track),
            **kwargs,
        )
        self._command = command
        self._track = track
        self._track_border = track_border
        self._thumb = thumb
        self._thumb_active = thumb_active
        self._radius = radius

        self._first = 0.0
        self._last = 1.0
        self._dragging = False
        self._drag_offset = 0
        self._hover = False

        self.bind("<Configure>", lambda e: self._redraw())
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)

        self._redraw()

    def _set_hover(self, v: bool):
        self._hover = v
        if not self._dragging:
            self._redraw()

    def set(self, first, last):
        try:
            self._first = float(first)
            self._last = float(last)
        except Exception:
            self._first, self._last = 0.0, 1.0
        self._redraw()

    def _round_rect(self, x1, y1, x2, y2, r, **kw):
        r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
        pts = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]
        return self.create_polygon(pts, smooth=True, splinesteps=24, **kw)

    def _thumb_coords(self):
        h = max(1, self.winfo_height())
        y1 = int(self._first * h)
        y2 = int(self._last * h)
        min_len = 26
        if y2 - y1 < min_len:
            mid = (y1 + y2) // 2
            y1 = max(0, mid - min_len // 2)
            y2 = min(h, y1 + min_len)
            y1 = max(0, y2 - min_len)
        y1 = max(2, y1)
        y2 = min(h - 2, y2)
        return y1, y2

    def _redraw(self):
        self.delete("all")
        w = max(2, self.winfo_width())
        h = max(2, self.winfo_height())

        self._round_rect(
            1,
            1,
            w - 1,
            h - 1,
            self._radius,
            fill=self._track,
            outline=self._track_border,
            width=1,
        )

        y1, y2 = self._thumb_coords()
        fill = self._thumb_active if (self._dragging or self._hover) else self._thumb
        self._round_rect(
            2,
            y1,
            w - 2,
            y2,
            max(6, self._radius - 2),
            fill=fill,
            outline="",
            width=0,
        )

    def _on_click(self, event):
        y1, y2 = self._thumb_coords()
        if y1 <= event.y <= y2:
            self._dragging = True
            self._drag_offset = event.y - y1
            self._redraw()
            return

        if event.y < y1:
            self._command("scroll", -1, "pages")
        else:
            self._command("scroll", 1, "pages")

    def _on_drag(self, event):
        if not self._dragging:
            return
        h = max(1, self.winfo_height())
        y1, y2 = self._thumb_coords()
        thumb_len = max(1, y2 - y1)

        new_y1 = event.y - self._drag_offset
        new_y1 = max(2, min(h - 2 - thumb_len, new_y1))
        frac = new_y1 / max(1, (h - thumb_len))
        frac = max(0.0, min(1.0, frac))
        self._command("moveto", frac)

    def _on_release(self, event):
        if self._dragging:
            self._dragging = False
            self._redraw()


class MinimalDropdown(tk.Canvas):
    def __init__(
        self,
        master,
        *,
        values,
        variable,
        command=None,
        bg,
        fill,
        hover_fill,
        border,
        fg,
        muted,
        radius=14,
        font=("DejaVu Sans", 10, "bold"),
        padx=14,
        pady=9,
        min_width=132,
    ):
        self.values = list(values)
        self.variable = variable
        self.command = command
        self.outer_bg = bg
        self.fill = fill
        self.hover_fill = hover_fill
        self.current_fill = fill
        self.border = border
        self.fg = fg
        self.muted = muted
        self.radius = radius
        self.padx = padx
        self.pady = pady
        self.font = tkfont.Font(font=font)
        self._popup = None
        self._outside_binding = None

        text = self.variable.get() if hasattr(self.variable, 'get') else ''
        content_w = self.font.measure(str(text or '')) + 22
        width = max(min_width, content_w + 2 * padx)
        height = max(40, self.font.metrics('linespace') + 2 * pady)

        super().__init__(
            master,
            width=width,
            height=height,
            bg=bg,
            highlightthickness=0,
            bd=0,
            relief='flat',
            cursor='hand2',
        )
        self.bind('<Configure>', self._redraw)
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<Button-1>', self._toggle_popup)
        self._redraw()

    def _rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        r = min(r, max(1, (x2 - x1) // 2), max(1, (y2 - y1) // 2))
        points = [
            x1 + r, y1,
            x1 + r, y1,
            x2 - r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1 + r,
            x1, y1,
        ]
        return self.create_polygon(points, smooth=True, splinesteps=36, **kwargs)

    def _redraw(self, event=None):
        self.delete('all')
        w = max(2, self.winfo_width() - 1)
        h = max(2, self.winfo_height() - 1)
        self._rounded_rect(
            1, 1, w, h, self.radius,
            fill=self.current_fill,
            outline=self.border,
            width=1,
        )
        text = str(self.variable.get() if hasattr(self.variable, 'get') else '')
        self.create_text(
            self.padx,
            h // 2,
            text=text,
            fill=self.fg,
            font=self.font,
            anchor='w',
        )
        arrow_x = w - self.padx - 5
        arrow_y = h // 2
        self.create_polygon(
            arrow_x - 5, arrow_y - 3,
            arrow_x + 5, arrow_y - 3,
            arrow_x, arrow_y + 3,
            fill=self.muted,
            outline=self.muted,
        )

    def _on_enter(self, event=None):
        self.current_fill = self.hover_fill
        self._redraw()

    def _on_leave(self, event=None):
        if self._popup is None:
            self.current_fill = self.fill
            self._redraw()

    def _toggle_popup(self, event=None):
        if self._popup is not None:
            self._close_popup()
        else:
            self._open_popup()

    def _open_popup(self):
        if self._popup is not None:
            return
        self.current_fill = self.hover_fill
        self._redraw()

        popup = tk.Toplevel(self)
        popup.overrideredirect(True)
        popup.transient(self.winfo_toplevel())
        popup.configure(bg=self.outer_bg)
        popup.attributes('-topmost', True)
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 6
        popup.geometry(f'+{x}+{y}')

        card = RoundedCard(
            popup,
            bg=self.outer_bg,
            fill=self.fill,
            border=self.border,
            radius=16,
            padding=6,
            width=max(self.winfo_width(), 132),
        )
        card.pack(fill='both', expand=True)

        for idx, value in enumerate(self.values):
            row = tk.Label(
                card.inner,
                text=value,
                bg=self.fill,
                fg=self.fg,
                font=("DejaVu Sans", 10, 'bold' if value == self.variable.get() else 'normal'),
                padx=12,
                pady=9,
                anchor='w',
                cursor='hand2',
            )
            row.pack(fill='x')
            row.bind('<Enter>', lambda e, r=row: r.configure(bg=self.hover_fill))
            row.bind('<Leave>', lambda e, r=row, v=value: r.configure(bg=self.fill))
            row.bind('<Button-1>', lambda e, v=value: self._select(v))

        popup.update_idletasks()
        self._popup = popup
        popup.bind('<FocusOut>', lambda e: self._close_popup())
        popup.bind('<Escape>', lambda e: self._close_popup())

    def _handle_outside_click(self, event):
        if self._popup is None:
            return
        widget = event.widget
        if widget is self or widget.winfo_toplevel() is self._popup:
            return
        self._close_popup()

    def _select(self, value):
        self.variable.set(value)
        if callable(self.command):
            self.command(value)
        self._close_popup()
        self._redraw()

    def _close_popup(self):
        if self._popup is not None:
            try:
                self._popup.destroy()
            except Exception:
                pass
            self._popup = None
        self._outside_binding = None
        self.current_fill = self.fill
        self._redraw()


class MinimalDialog(tk.Toplevel):
    def __init__(self, parent, *, title, message, colors, kind='info'):
        super().__init__(parent)
        self.withdraw()
        self.transient(parent)
        self.title(title)
        self.configure(bg=colors['bg'])
        self.resizable(True, True)
        self.minsize(380, 180)
        self.geometry('620x340')

        wrap = 'word'
        font = ("DejaVu Sans", 10)
        if len(message) > 220 or "\n" in message:
            font = ("DejaVu Sans Mono", 10)
            wrap = 'char'

        shell = tk.Frame(self, bg=colors['bg'])
        shell.pack(fill='both', expand=True, padx=16, pady=16)

        card = RoundedCard(
            shell,
            bg=colors['bg'],
            fill=colors['surface'],
            border=colors['border'],
            radius=22,
            padding=14,
        )
        card.pack(fill='both', expand=True)

        head = tk.Frame(card.inner, bg=colors['surface'])
        head.pack(fill='x', pady=(0, 10))

        badge_text = {'info': 'Info', 'warning': 'Warning', 'error': 'Error'}.get(kind, 'Notice')
        badge = tk.Label(
            head,
            text=badge_text,
            bg=colors['ghost'],
            fg=colors['accent'],
            font=("DejaVu Sans", 9, 'bold'),
            padx=10,
            pady=4,
        )
        badge.pack(side='left')

        title_lbl = tk.Label(
            head,
            text=title,
            bg=colors['surface'],
            fg=colors['text'],
            font=("DejaVu Sans", 12, 'bold'),
        )
        title_lbl.pack(side='left', padx=(10, 0))

        body_shell = RoundedCard(
            card.inner,
            bg=colors['surface'],
            fill=colors['surface_alt'],
            border=colors['input_border'],
            radius=18,
            padding=10,
            height=190,
        )
        body_shell.pack(fill='both', expand=True)

        text = tk.Text(
            body_shell.inner,
            bg=colors['surface_alt'],
            fg=colors['text'],
            insertbackground=colors['accent'],
            relief='flat',
            bd=0,
            highlightthickness=0,
            wrap=wrap,
            font=font,
            padx=8,
            pady=6,
        )
        sb = RoundedScrollbar(
            body_shell.inner,
            command=text.yview,
            width=12,
            track=colors['surface_soft'],
            track_border=colors['input_border'],
            thumb=colors['accent'],
            thumb_active=colors['accent_hover'],
            radius=10,
            bg=colors['surface_alt'],
        )
        text.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y', padx=(8, 0))
        text.pack(side='left', fill='both', expand=True)
        text.insert('1.0', message)
        text.configure(state='disabled')

        foot = tk.Frame(card.inner, bg=colors['surface'])
        foot.pack(fill='x', pady=(12, 0))

        ok_btn = IconButton(
            foot,
            text='OK',
            command=self._on_ok,
            bg=colors['surface'],
            fill=colors['accent'],
            hover_fill=colors['accent_hover'],
            fg='#ffffff',
            radius=14,
            min_width=86,
            padx=14,
            pady=8,
        )
        ok_btn.pack(side='right')

        self.bind('<Escape>', lambda e: self._on_ok())
        self.bind('<Return>', lambda e: self._on_ok())
        self.protocol('WM_DELETE_WINDOW', self._on_ok)
        self.deiconify()
        self.grab_set()
        self.update_idletasks()
        self._center(parent)

    def _center(self, parent):
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        w = self.winfo_width()
        h = self.winfo_height()
        x = px + max(0, (pw - w) // 2)
        y = py + max(0, (ph - h) // 2)
        self.geometry(f'{w}x{h}+{x}+{y}')

    def _on_ok(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()


def _extract_first_useful_latex_error(log_text: str) -> str:
    """Return a short, human-useful error snippet from a LaTeX log."""
    if not log_text:
        return ""
    lines = log_text.splitlines()
    # Prefer TeX-style error lines starting with "!"
    for i, line in enumerate(lines):
        if line.lstrip().startswith("!"):
            snippet = [line]
            # include a few following context lines (often include 'l.<num>')
            for j in range(i + 1, min(i + 10, len(lines))):
                if lines[j].strip() == "" and len(snippet) >= 2:
                    break
                snippet.append(lines[j])
                if lines[j].lstrip().startswith("l."):
                    # keep one more context line if present
                    if j + 1 < len(lines) and lines[j + 1].strip():
                        snippet.append(lines[j + 1])
                    break
            return "\n".join(snippet).strip()
    # Fallback: look for common fatal markers
    for key in ("Emergency stop.", "Fatal error", "Undefined control sequence"):
        for i, line in enumerate(lines):
            if key in line:
                return "\n".join(lines[max(0, i - 2): i + 4]).strip()
    # Last resort: first non-empty lines
    head = [ln for ln in lines if ln.strip()][:6]
    return "\n".join(head).strip()


class ErrorDialog(tk.Toplevel):
    """Minimal themed error dialog with summary + expandable full log + copy."""

    def __init__(self, parent, *, title, summary, full_log, colors):
        super().__init__(parent)
        self.withdraw()
        self.transient(parent)
        self.title(title)
        self.configure(bg=colors["bg"])
        self.resizable(True, True)
        self.minsize(520, 240)
        self.geometry("760x420")

        self._colors = colors
        self._full_log = full_log or ""
        self._expanded = False

        # Card
        card = tk.Frame(self, bg=colors["surface"], highlightthickness=1, highlightbackground=colors["border"])
        card.pack(fill="both", expand=True, padx=18, pady=18)

        head = tk.Frame(card, bg=colors["surface"])
        head.pack(fill="x", padx=16, pady=(14, 10))

        tk.Label(
            head,
            text="Error",
            bg=colors["surface"],
            fg=colors["accent"],
            font=("DejaVu Sans", 12, "bold"),
        ).pack(side="left")

        # Summary
        summary_frame = tk.Frame(card, bg=colors["surface"])
        summary_frame.pack(fill="x", padx=16)

        tk.Label(
            summary_frame,
            text=summary or "Compilation failed.",
            bg=colors["surface"],
            fg=colors["text"],
            justify="left",
            anchor="w",
            font=("DejaVu Sans", 10),
            wraplength=700,
        ).pack(fill="x")

        # Full log (hidden by default)
        self.log_wrap = tk.Frame(card, bg=colors["surface"])
        self.log_text = tk.Text(
            self.log_wrap,
            height=10,
            font=("DejaVu Sans Mono", 10),
            bg=colors["surface_alt"],
            fg=colors["text"],
            insertbackground=colors["text"],
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=colors["border"],
            highlightcolor=colors["accent"],
            padx=12,
            pady=10,
            wrap="none",
        )
        self.log_text.insert("1.0", self._full_log)
        self.log_text.configure(state="disabled")

        sb_y = ttk.Scrollbar(self.log_wrap, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb_y.set)

        self.log_text.pack(side="left", fill="both", expand=True)
        sb_y.pack(side="right", fill="y")

        # Buttons
        btns = tk.Frame(card, bg=colors["surface"])
        btns.pack(fill="x", padx=16, pady=(12, 14))

        self.toggle_btn = tk.Button(
            btns,
            text="Show full log",
            bg=colors["ghost"],
            fg=colors["text"],
            activebackground=colors["soft_hover"],
            activeforeground=colors["text"],
            relief="flat",
            bd=0,
            padx=12,
            pady=8,
            cursor="hand2",
            command=self._toggle,
        )
        self.toggle_btn.pack(side="left")

        copy_btn = tk.Button(
            btns,
            text="Copy",
            bg=colors["ghost"],
            fg=colors["text"],
            activebackground=colors["soft_hover"],
            activeforeground=colors["text"],
            relief="flat",
            bd=0,
            padx=12,
            pady=8,
            cursor="hand2",
            command=self._copy,
        )
        copy_btn.pack(side="left", padx=(10, 0))

        close_btn = tk.Button(
            btns,
            text="Close",
            bg=colors["accent"],
            fg="#ffffff",
            activebackground=colors["accent_hover"],
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=14,
            pady=8,
            cursor="hand2",
            command=self.destroy,
        )
        close_btn.pack(side="right")

        self.bind("<Escape>", lambda e: self.destroy())

        self.update_idletasks()
        self.deiconify()
        self.grab_set()

    def _toggle(self):
        if not self._expanded:
            self.log_wrap.pack(fill="both", expand=True, padx=16, pady=(10, 0))
            self.toggle_btn.configure(text="Hide full log")
            self._expanded = True
        else:
            self.log_wrap.pack_forget()
            self.toggle_btn.configure(text="Show full log")
            self._expanded = False

    def _copy(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(self._full_log)
        except Exception:
            pass

class TexColApp:

    def _apply_modern_theme(self):
        self.colors = {
            "bg": "#f8eef1",
            "surface": "#fffafb",
            "surface_alt": "#f7edf1",
            "surface_soft": "#f3e4ea",
            "border": "#e7ccd6",
            "input_border": "#dec0cb",
            "text": "#2d1019",
            "muted": "#815d69",
            "accent": "#7f1737",
            "accent_hover": "#69122e",
            "soft_hover": "#edd9e1",
            "preview_border": "#dcc0ca",
            "ghost": "#f1e0e7",
            "clear_fill": "#f6e7ec",
            "clear_hover": "#efd5de",
        }

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "Title.TLabel",
            background=self.colors["bg"],
            foreground=self.colors["text"],
            font=("DejaVu Sans", 24, "bold"),
        )
        style.configure(
            "CardTitle.TLabel",
            background=self.colors["surface"],
            foreground=self.colors["text"],
            font=("DejaVu Sans", 11, "bold"),
        )
        style.configure(
            "Status.TLabel",
            background=self.colors["bg"],
            foreground=self.colors["muted"],
            font=("DejaVu Sans", 10),
        )

    def _make_text_widget(self, parent, height):
        widget = tk.Text(
            parent,
            height=height,
            font=("DejaVu Sans Mono", 11),
            bg=self.colors["surface_alt"],
            fg=self.colors["text"],
            insertbackground=self.colors["accent"],
            relief="flat",
            bd=0,
            highlightthickness=0,
            selectbackground="#dcb0c0",
            selectforeground=self.colors["text"],
            padx=14,
            pady=12,
            undo=True,
            wrap="word",
        )
        self._bind_text_shortcuts(widget)
        return widget

    def _make_minimal_scrollbar(self, parent, command):
        return RoundedScrollbar(
            parent,
            command=command,
            width=12,
            track=self.colors["surface_soft"],
            track_border=self.colors["input_border"],
            thumb=self.colors["accent"],
            thumb_active=self.colors["accent_hover"],
            radius=10,
            bg=self.colors["surface_alt"],
        )
    def _setup_code_editor(self, widget: tk.Text):
        """Apply lightweight LaTeX syntax highlighting (Overleaf-like cues)."""
        if not hasattr(self, "_hl_jobs"):
            self._hl_jobs = {}
        # Tags
        widget.tag_configure("kw", foreground=self.colors["accent"], font=("DejaVu Sans Mono", 11, "bold"))
        widget.tag_configure("env", foreground=self.colors["accent_hover"])
        widget.tag_configure("cmd", foreground="#8b2c3a")  
        widget.tag_configure("comment", foreground="#94a3b8", font=("DejaVu Sans Mono", 11))

        widget.bind("<KeyRelease>", lambda e, w=widget: self._schedule_highlight(w))
        widget.bind("<ButtonRelease-1>", lambda e, w=widget: self._schedule_highlight(w))
        self._schedule_highlight(widget, immediate=True)

    def _schedule_highlight(self, widget: tk.Text, immediate: bool = False):
        if not hasattr(self, "_hl_jobs"):
            self._hl_jobs = {}
        job = self._hl_jobs.get(widget)
        if job:
            try:
                self.root.after_cancel(job)
            except Exception:
                pass
        delay = 1 if immediate else 120
        self._hl_jobs[widget] = self.root.after(delay, lambda w=widget: self._apply_highlight(w))

    def _apply_highlight(self, widget: tk.Text):
        try:
            text = widget.get("1.0", "end-1c")
        except Exception:
            return

        # Clear tags
        for tag in ("kw", "env", "cmd", "comment"):
            widget.tag_remove(tag, "1.0", "end")

        # Comments: % ... endline
        for m in re.finditer(r"(?m)%.*$", text):
            s = f"1.0+{m.start()}c"
            e = f"1.0+{m.end()}c"
            widget.tag_add("comment", s, e)

        # Keywords
        for m in re.finditer(r"\\(usepackage|begin|end|documentclass|usetikzlibrary|newcommand|renewcommand)\b", text):
            s = f"1.0+{m.start()}c"
            e = f"1.0+{m.end()}c"
            widget.tag_add("kw", s, e)

        # Environment names inside \begin{...} or \end{...}
        for m in re.finditer(r"\\(?:begin|end)\{([^}]+)\}", text):
            env_start = m.start(1)
            env_end = m.end(1)
            s = f"1.0+{env_start}c"
            e = f"1.0+{env_end}c"
            widget.tag_add("env", s, e)

        # Generic commands (keep last so it doesn't override kw)
        for m in re.finditer(r"\\[A-Za-z@]+\*?", text):
            # Skip if already tagged as kw
            s = f"1.0+{m.start()}c"
            e = f"1.0+{m.end()}c"
            # If keyword tag overlaps, don't add cmd
            if widget.tag_nextrange("kw", s, e):
                continue
            widget.tag_add("cmd", s, e)


    def _make_rounded_textbox(self, parent, height, min_height):
        shell = RoundedCard(
            parent,
            bg=self.colors["surface"],
            fill=self.colors["surface_alt"],
            border=self.colors["input_border"],
            radius=18,
            padding=10,
            height=min_height,
        )

        text = self._make_text_widget(shell.inner, height)
        sb = self._make_minimal_scrollbar(shell.inner, text.yview)
        text.configure(yscrollcommand=sb.set)

        sb.pack(side="right", fill="y", padx=(8, 0))
        text.pack(side="left", fill="both", expand=True)

        return shell, text

    def _select_all_text(self, event=None):
        widget = event.widget if event is not None else None
        if widget is None:
            return "break"
        try:
            widget.tag_add("sel", "1.0", "end-1c")
            widget.mark_set("insert", "1.0")
            widget.see("insert")
            widget.focus_set()
        except Exception:
            pass
        return "break"

    def _paste_replace_selection(self, event=None):
        widget = event.widget if event is not None else None
        if widget is None:
            return "break"
        try:
            if widget.tag_ranges("sel"):
                start = widget.index("sel.first")
                widget.delete("sel.first", "sel.last")
                widget.mark_set("insert", start)
        except Exception:
            pass
        widget.event_generate("<<Paste>>")
        return "break"

    def _bind_text_shortcuts(self, widget):
        widget.bind("<Control-a>", self._select_all_text)
        widget.bind("<Control-A>", self._select_all_text)
        widget.bind("<Control-v>", self._paste_replace_selection)
        widget.bind("<Control-V>", self._paste_replace_selection)

    def _show_dialog(self, title, message, kind="info"):
        dlg = MinimalDialog(self.root, title=title, message=str(message), colors=self.colors, kind=kind)
        self.root.wait_window(dlg)

    def _show_info(self, title, message):
        self._show_dialog(title, message, kind="info")

    def _show_warning(self, title, message):
        self._show_dialog(title, message, kind="warning")

    def _show_error(self, title, message):
        full = str(message)
        summary = _extract_first_useful_latex_error(full)
        dlg = ErrorDialog(self.root, title=title, summary=summary, full_log=full, colors=self.colors)
        self.root.wait_window(dlg)

    def _set_input_mode(self, mode: str):
        mode = (mode or "").strip().lower()
        if mode not in {"formula", "tikz"}:
            mode = "formula"
        self.input_mode.set(mode)

        if mode == "formula":
            self.mode_formula_btn.set_theme(
                fill=self.colors["accent"], hover_fill=self.colors["accent_hover"], fg="#ffffff"
            )
            self.mode_tikz_btn.set_theme(
                fill=self.colors["ghost"], hover_fill=self.colors["soft_hover"], fg=self.colors["text"]
            )
        else:
            self.mode_tikz_btn.set_theme(
                fill=self.colors["accent"], hover_fill=self.colors["accent_hover"], fg="#ffffff"
            )
            self.mode_formula_btn.set_theme(
                fill=self.colors["ghost"], hover_fill=self.colors["soft_hover"], fg=self.colors["text"]
            )

    def _load_icon_asset(self, candidates, size=(18, 18)):
        if not hasattr(self, "_icon_refs"):
            self._icon_refs = {}

        search_dirs = [APP_DIR / "icons", RUNTIME_DIR.parent / "icons", LEGACY_APP_DIR / "icons"]
        extensions = (".png", ".webp", ".jpg", ".jpeg")

        for directory in search_dirs:
            if not directory.exists():
                continue
            for name in candidates:
                for ext in extensions:
                    path = directory / f"{name}{ext}"
                    if path.exists():
                        try:
                            img = Image.open(path).convert("RGBA")
                            img = img.resize(size, Image.LANCZOS)
                            tk_img = ImageTk.PhotoImage(img)
                            self._icon_refs[str(path)] = tk_img
                            return tk_img
                        except Exception:
                            pass
        return None

    def _load_button_icons(self):
        self.icons = {
            "generate": self._load_icon_asset(["generate", "run", "play"]),
            "download": self._load_icon_asset(["download", "export", "save-svg", "save_svg"]),
            "save_preamble": self._load_icon_asset(["save_preamble", "save-preamble", "savepreamble", "save"]),
            "clear": self._load_icon_asset(["clear", "trash", "delete", "broom"]),
        }

    def __init__(self, root):
        self.root = root
        root.title("TexCol")
        root.geometry("760x780")
        root.minsize(440, 640)

        self._apply_modern_theme()
        self._load_button_icons()
        root.configure(bg=self.colors["bg"])

        # Runtime directory (fixed)
        self.runtime_dir = RUNTIME_DIR
        try:
            _safe_wipe_dir(self.runtime_dir)
        except Exception as e:
            self._show_error(
                "TexCol",
                f"Unable to initialize runtime folder:\n{self.runtime_dir}\n\nDetails:\n{e}",
            )
            raise

        self.build_dir = self.runtime_dir / "build"
        self.build_dir.mkdir(parents=True, exist_ok=True)
        # Cache: per-render subdirs keyed by input hash
        self.cache_dir = self.runtime_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_max_entries = 120
        self._cache_max_age_sec = 7 * 24 * 3600

        # Runtime artifacts (drag source + browser page)
        self.runtime_svg = self.runtime_dir / "formula.svg"
        self.browser_page = self.runtime_dir / "ppt_copy.html"

        self._runtime_cleaned = False
        self._last_render_key = None
        self.httpd = None
        self.http_thread = None

        atexit.register(self._cleanup_runtime)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        main = tk.Frame(root, bg=self.colors["bg"])
        main.pack(fill="both", expand=True, padx=14, pady=14)

        header = tk.Frame(main, bg=self.colors["bg"])
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(header, text="TexCol", style="Title.TLabel").pack(anchor="w")

        preamble_card = RoundedCard(
            main,
            bg=self.colors["bg"],
            fill=self.colors["surface"],
            border=self.colors["border"],
            radius=24,
            padding=12,
            height=220,
        )
        preamble_card.pack(fill="x", pady=(0, 14))

        preamble_head = tk.Frame(preamble_card.inner, bg=self.colors["surface"])
        preamble_head.pack(fill="x", pady=(0, 8))
        ttk.Label(preamble_head, text="Preamble", style="CardTitle.TLabel").pack(side="left")
        self.save_button = IconButton(
            preamble_head,
            text="Save",
            image=self.icons.get("save_preamble"),
            command=self.save_preamble,
            bg=self.colors["surface"],
            fill=self.colors["ghost"],
            hover_fill=self.colors["soft_hover"],
            fg=self.colors["text"],
            radius=14,
            font=("DejaVu Sans", 10, "bold"),
            min_width=88,
        )
        self.save_button.pack(side="right")

        preamble_box, self.preamble = self._make_rounded_textbox(
            preamble_card.inner, height=6, min_height=145
        )
        preamble_box.pack(fill="x")

        # Input mode toggle + compiler
        self.input_mode = tk.StringVar(value="formula")
        self.compiler = tk.StringVar(value="pdflatex")

        formula_card = RoundedCard(
            main,
            bg=self.colors["bg"],
            fill=self.colors["surface"],
            border=self.colors["border"],
            radius=24,
            padding=12,
            height=215,
        )
        formula_card.pack(fill="x", pady=(0, 14))

        formula_head = tk.Frame(formula_card.inner, bg=self.colors["surface"])
        formula_head.pack(fill="x", pady=(0, 8))

        toggle = tk.Frame(formula_head, bg=self.colors["surface"])
        toggle.pack(side="left")
        self.mode_formula_btn = IconButton(
            toggle,
            text="Formula",
            image=None,
            command=lambda: self._set_input_mode("formula"),
            bg=self.colors["surface"],
            fill=self.colors["accent"],
            hover_fill=self.colors["accent_hover"],
            fg="#ffffff",
            radius=14,
            font=("DejaVu Sans", 10, "bold"),
            padx=14,
            pady=8,
            min_width=96,
        )
        self.mode_formula_btn.pack(side="left", padx=(0, 8))
        self.mode_tikz_btn = IconButton(
            toggle,
            text="TikZ",
            image=None,
            command=lambda: self._set_input_mode("tikz"),
            bg=self.colors["surface"],
            fill=self.colors["ghost"],
            hover_fill=self.colors["soft_hover"],
            fg=self.colors["text"],
            radius=14,
            font=("DejaVu Sans", 10, "bold"),
            padx=14,
            pady=8,
            min_width=72,
        )
        self.mode_tikz_btn.pack(side="left")
        # Compiler selector (right)
        self.compiler_dropdown = MinimalDropdown(
            formula_head,
            values=("pdflatex", "lualatex", "xelatex"),
            variable=self.compiler,
            bg=self.colors["surface"],
            fill=self.colors["ghost"],
            hover_fill=self.colors["soft_hover"],
            border=self.colors["input_border"],
            fg=self.colors["text"],
            muted=self.colors["muted"],
            radius=14,
            min_width=136,
        )
        self.compiler_dropdown.pack(side="right")

        formula_box, self.formula = self._make_rounded_textbox(
            formula_card.inner, height=6, min_height=140
        )
        formula_box.pack(fill="x")
        # Code-editor cues (lightweight LaTeX highlighting)
        self._setup_code_editor(self.preamble)
        self._setup_code_editor(self.formula)


        action_card = RoundedCard(
            main,
            bg=self.colors["bg"],
            fill=self.colors["surface"],
            border=self.colors["border"],
            radius=22,
            padding=10,
            height=68,
        )
        action_card.pack(fill="x", pady=(0, 14))

        action_bar = tk.Frame(action_card.inner, bg=self.colors["surface"])
        action_bar.pack(fill="x")

        self.generate_button = IconButton(
            action_bar,
            text="Generate",
            image=self.icons.get("generate"),
            command=self.generate,
            bg=self.colors["surface"],
            fill=self.colors["accent"],
            hover_fill=self.colors["accent_hover"],
            fg="#ffffff",
            radius=16,
            min_width=118,
        )
        self.generate_button.pack(side="left", padx=(0, 10))

        self.download_button = IconButton(
            action_bar,
            text="Download",
            image=self.icons.get("download"),
            command=self.download_svg,
            bg=self.colors["surface"],
            fill=self.colors["ghost"],
            hover_fill=self.colors["soft_hover"],
            fg=self.colors["text"],
            radius=16,
            min_width=118,
        )
        self.download_button.pack(side="left", padx=(0, 10))

        self.clear_button = IconButton(
            action_bar,
            text="Clear",
            image=self.icons.get("clear"),
            command=self.clean_tmp,
            bg=self.colors["surface"],
            fill=self.colors["clear_fill"],
            hover_fill=self.colors["clear_hover"],
            fg=self.colors["text"],
            radius=16,
            min_width=96,
        )
        self.clear_button.pack(side="left")

        preview_card = RoundedCard(
            main,
            bg=self.colors["bg"],
            fill=self.colors["surface"],
            border=self.colors["border"],
            radius=24,
            padding=12,
            height=240,
        )
        preview_card.pack(fill="both", expand=True)

        preview_shell = RoundedCard(
            preview_card.inner,
            bg=self.colors["surface"],
            fill=self.colors["surface_alt"],
            border=self.colors["preview_border"],
            radius=20,
            padding=10,
        )
        preview_shell.pack(fill="both", expand=True)

        self.preview_canvas = tk.Canvas(
            preview_shell.inner,
            bg=self.colors["surface_alt"],
            cursor="hand2",
            highlightthickness=0,
            bd=0,
            relief="flat",
        )
        self.preview_canvas.pack(fill="both", expand=True)
        self.preview_canvas.bind("<Configure>", self._redraw_preview)

        # Drag source: exports self.runtime_svg
        self.preview_canvas.drag_source_register(1, DND_FILES)
        self.preview_canvas.dnd_bind("<<DragInitCmd>>", self._on_drag_init)

        self.status = ttk.Label(main, text="", style="Status.TLabel", anchor="w")
        self.status.pack(fill="x", pady=(8, 0))

        self.svg_data = None
        self.png_bytes = None
        self.preview_img = None

        self._set_input_mode("formula")
        self.load_preamble()

    # ----------------------------
    # Cleanup
    # ----------------------------
    def _cleanup_runtime(self):
        if self._runtime_cleaned:
            return

        if self.httpd is not None:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:
                pass
            self.httpd = None
            self.http_thread = None

        # Clean temporary files but keep the folder
        try:
            _safe_wipe_dir(self.runtime_dir)
            # Recreate build_dir to avoid errors if the process keeps running
            self.build_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        self._runtime_cleaned = True

    def _on_close(self):
        self._cleanup_runtime()
        self.root.destroy()

    def clean_tmp(self):
        # Stop server before cleaning
        if self.httpd is not None:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:
                pass
            self.httpd = None
            self.http_thread = None

        try:
            _safe_wipe_dir(self.runtime_dir)
            self.build_dir.mkdir(parents=True, exist_ok=True)
            self.svg_data = None
            self.png_bytes = None
            self._last_render_key = None
            self.formula.delete("1.0", "end")
            self._redraw_preview()
            self.status.config(text="Cleared")
        except Exception as e:
            self._show_error("TexCol", f"Temporary cleanup error:\n{e}")

    # ----------------------------
    # Drag (SVG file)
    # ----------------------------
    def _on_drag_init(self, event):
        if self.runtime_svg.exists():
            # TkDND expects a path "list"; braces handle spaces.
            data = f"{{{self.runtime_svg}}}"
            return (COPY, DND_FILES, data)
        return None

    # ----------------------------
    # Browser helper page (copy image)
    # ----------------------------
    def _start_http_server(self):
        if self.httpd is not None:
            return

        def handler_factory(*args, **kwargs):
            return _RuntimeHTTPHandler(*args, directory=str(self.runtime_dir), **kwargs)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory)
        self.http_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.http_thread.start()

    def _write_browser_page(self):
        self.browser_page.write_text(
            """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>TexCol - Copy for PowerPoint Web</title>
  <style>
    :root {
      --bg: #f8eef1;
      --surface: #fffdfd;
      --surface-alt: #f7edf1;
      --border: #e7ccd6;
      --text: #2d1520;
      --muted: #815d69;
      --accent: #7f1737;
    }
    body {
      font-family: Inter, system-ui, sans-serif;
      margin: 0;
      padding: 28px;
      background: var(--bg);
      color: var(--text);
    }
    .card {
      max-width: 1080px;
      margin: 0 auto;
      background: var(--surface);
      padding: 22px;
      border: 1px solid var(--border);
      border-radius: 24px;
      box-shadow: 0 14px 40px rgba(122, 31, 61, 0.08);
    }
    .title {
      margin: 0 0 6px;
      font-size: 24px;
      font-weight: 700;
    }
    .hint {
      margin: 0 0 16px;
      color: var(--muted);
      line-height: 1.5;
    }
    .preview {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 240px;
      border: 1px dashed #d8bcc8;
      border-radius: 20px;
      background: var(--surface-alt);
      padding: 16px;
    }
    img {
      max-width: 95%;
      max-height: 70vh;
    }
    .badge {
      display: inline-block;
      margin-bottom: 12px;
      padding: 6px 10px;
      border-radius: 999px;
      background: #f4e5eb;
      color: var(--accent);
      font-size: 12px;
      font-weight: 600;
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="badge">TexCol copy helper</div>
    <h1 class="title">Copy for PowerPoint Web</h1>
    <p class="hint"><strong>Firefox:</strong> right-click the formula, choose <em>Copy image</em>, then paste it into the slide with Ctrl+V.</p>
    <div class="preview">
      <img id="formula" src="formula.svg" alt="formula svg">
    </div>
  </div>
</body>
</html>
""",
            encoding="utf-8",
        )

    # ----------------------------
    # Preamble
    # ----------------------------
    def load_preamble(self):
        if PREAMBLE_FILE.exists():
            self.preamble.insert("1.0", PREAMBLE_FILE.read_text(encoding="utf-8"))
            return

        if LEGACY_PREAMBLE_FILE.exists():
            content = LEGACY_PREAMBLE_FILE.read_text(encoding="utf-8")
            self.preamble.insert("1.0", content)
            try:
                PREAMBLE_FILE.write_text(content, encoding="utf-8")
            except Exception:
                pass

    def save_preamble(self):
        try:
            PREAMBLE_FILE.write_text(self.preamble.get("1.0", "end"), encoding="utf-8")
            self._show_info("TexCol", f"Preamble saved to:\n{PREAMBLE_FILE}")
        except Exception as e:
            self._show_error("TexCol", f"Unable to save preamble:\n{e}")

    # ----------------------------
    # Generate
    # ----------------------------
    def _clean_build_dir(self):
        # clean only build_dir
        self.build_dir.mkdir(parents=True, exist_ok=True)
        for child in self.build_dir.iterdir():
            try:
                if child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)
                else:
                    child.unlink(missing_ok=True)
            except Exception:
                pass

    def _render_cache_key(self, *, compiler: str, mode: str, preamble: str, body: str) -> str:
        h = hashlib.sha256()
        h.update((compiler or "").encode())
        h.update(b"\0")
        h.update((mode or "").encode())
        h.update(b"\0")
        h.update((preamble or "").encode("utf-8", errors="ignore"))
        h.update(b"\0")
        h.update((body or "").encode("utf-8", errors="ignore"))
        return h.hexdigest()[:24]

    def _cache_paths(self, key: str):
        d = self.cache_dir / key
        return d, (d / "eq.tex"), (d / "eq.pdf"), (d / "eq.svg"), (d / "eq.png")

    def _cache_try_load(self, key: str) -> bool:
        d, _, _, svg_path, png_path = self._cache_paths(key)
        if not svg_path.exists():
            return False
        try:
            self.svg_data = svg_path.read_text(encoding="utf-8")
            self.runtime_svg.write_text(self.svg_data, encoding="utf-8")
            if png_path.exists():
                self.png_bytes = png_path.read_bytes()
            else:
                self.png_bytes = cairosvg.svg2png(bytestring=self.svg_data.encode())
                png_path.write_bytes(self.png_bytes)
            self._redraw_preview()
            # touch for LRU-ish eviction
            now = time.time()
            os.utime(d, (now, now))
            return True
        except Exception:
            return False

    def _cache_store_png(self, key: str):
        d, _, _, _, png_path = self._cache_paths(key)
        try:
            if self.png_bytes:
                png_path.write_bytes(self.png_bytes)
        except Exception:
            pass

    def _cache_gc(self):
        """Garbage-collect old cache entries."""
        try:
            entries = []
            now = time.time()
            for p in self.cache_dir.iterdir():
                if not p.is_dir():
                    continue
                try:
                    mtime = p.stat().st_mtime
                except Exception:
                    mtime = 0
                # age eviction
                if mtime and (now - mtime) > self._cache_max_age_sec:
                    shutil.rmtree(p, ignore_errors=True)
                    continue
                entries.append((mtime, p))
            # size eviction (keep newest)
            if len(entries) > self._cache_max_entries:
                entries.sort(key=lambda t: t[0], reverse=True)
                for _, p in entries[self._cache_max_entries:]:
                    shutil.rmtree(p, ignore_errors=True)
        except Exception:
            pass

    def generate(self):
        preamble = self.preamble.get("1.0", "end").strip()
        formula = self.formula.get("1.0", "end").strip()
        mode = "formula"
        try:
            mode = (self.input_mode.get() or "formula").strip().lower()
        except Exception:
            mode = "formula"
        if mode not in {"formula", "tikz"}:
            mode = "formula"

        if not formula:
            self._show_warning("TexCol", "Empty formula.")
            return

        compiler = (self.compiler.get() or "pdflatex").strip()
        if compiler not in {"pdflatex", "lualatex", "xelatex"}:
            compiler = "pdflatex"


        
        if mode == "tikz":
            body_src = formula.strip()
            if not body_src:
                self._show_warning("TexCol", "Empty TikZ input.")
                return

            # Auto-wrap if user did not provide a tikzpicture environment
            if re.search(r"\begin\\{tikzpicture\\}", body_src) is None:
                body = "\\begin{tikzpicture}\n" + body_src + "\n\\end{tikzpicture}"
            else:
                body = body_src

            tex = (
                "\\documentclass[tikz,border=2pt]{standalone}\n"
                f"{preamble}\n"
                "\\begin{document}\n"
                f"{body}\n"
                "\\end{document}\n"
            )

            key = self._render_cache_key(compiler=compiler, mode="tikz", preamble=preamble, body=body)
            if key == self._last_render_key and self.svg_data:
                self.status.config(text="Already up to date")
                return
            if self._cache_try_load(key):
                self._last_render_key = key
                self.status.config(text="Loaded from cache")
                return

            work_dir, tex_path, pdf_path, svg_path, png_path = self._cache_paths(key)
            work_dir.mkdir(parents=True, exist_ok=True)
            tex_path.write_text(tex, encoding="utf-8")

            t0 = time.perf_counter()
            try:
                subprocess.run(
                    [
                        compiler,
                        "-interaction=nonstopmode",
                        "-halt-on-error",
                        "-output-directory",
                        str(work_dir),
                        str(tex_path),
                    ],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                subprocess.run(
                    ["dvisvgm", "--pdf", "-n", "-o", str(svg_path), str(pdf_path)],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                self.svg_data = svg_path.read_text(encoding="utf-8")
                self.runtime_svg.write_text(self.svg_data, encoding="utf-8")
                self.png_bytes = cairosvg.svg2png(bytestring=self.svg_data.encode())
                png_path.write_bytes(self.png_bytes)
                self._redraw_preview()

                self._last_render_key = key
                self._cache_gc()
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                self.status.config(text=f"Rendered in {elapsed_ms} ms")
                return

            except subprocess.CalledProcessError as e:
                out = b""
                if getattr(e, "stdout", None):
                    out += e.stdout
                if getattr(e, "stderr", None):
                    out += b"\n" + e.stderr
                msg = out.decode(errors="replace") if out else str(e)
                self._show_error("LaTeX error", msg)
                self.status.config(text="Error.")
                return
            except FileNotFoundError as e:
                self._show_error(
                    "TexCol",
                    f"Command not found: {e.filename}\n"
                    "Install required packages, for example:\n"
                    "  sudo apt install texlive-latex-base dvisvgm"
                )
                self.status.config(text="Error.")
                return

        display_envs = {
            "align", "align*",
            "alignat", "alignat*",
            "flalign", "flalign*",
            "gather", "gather*",
            "multline", "multline*",
            "eqnarray", "eqnarray*",
            "equation", "equation*",
        }
        inner_math_envs = {
            "aligned",
            "alignedat",
            "gathered",
            "split",
            "matrix",
            "pmatrix",
            "bmatrix",
            "Bmatrix",
            "vmatrix",
            "Vmatrix",
            "smallmatrix",
            "cases",
        }
        ambiguous_display_envs = {
            "multline", "multline*",
            "eqnarray", "eqnarray*",
        }
        display_to_inner = {
            "align": "aligned",
            "align*": "aligned",
            "alignat": "alignedat",
            "alignat*": "alignedat",
            "flalign": "aligned",
            "flalign*": "aligned",
            "gather": "gathered",
            "gather*": "gathered",
        }

        def tight_math_box(content: str) -> str:
            content = content.strip()
            return "\\mbox{$\\displaystyle\n" + content + "\n$}"

        def numbered_tight_math_box(content: str, tag: str = "(1)") -> str:
            content = content.strip()
            return (
                "\\begingroup\n"
                "\\setbox0=\\hbox{$\\displaystyle\n" + content + "\n$}%\n"
                "\\hbox{\\box0\\hskip 0.8em {\\normalfont " + tag + "}}%\n"
                "\\endgroup"
            )

        def strip_math_delimiters(s: str) -> str:
            s = s.strip()
            if s.startswith(r"\[") and s.endswith(r"\]"):
                return s[2:-2].strip()
            if s.startswith("$$") and s.endswith("$$"):
                return s[2:-2].strip()
            if s.startswith(r"\(") and s.endswith(r"\)"):
                return s[2:-2].strip()
            if len(s) >= 2 and s.startswith("$") and s.endswith("$") and not s.startswith("$$"):
                return s[1:-1].strip()
            return s

        def parse_wrapped_environment(s: str):
            m = re.match(r"^\s*\\begin\{([A-Za-z*]+)\}(.*)\\end\{\1\}\s*$", s, re.DOTALL)
            if not m:
                return None, None
            return m.group(1), m.group(2).strip()

        def normalize_inline_math_content(content: str) -> str:
            content = content.strip()
            env, inner = parse_wrapped_environment(content)
            if env is None:
                return strip_math_delimiters(content)
            if env == "split":
                return "\\begin{aligned}\n" + inner + "\n\\end{aligned}"
            if env in inner_math_envs:
                return content
            if env in display_to_inner:
                mapped = display_to_inner[env]
                return "\\begin{" + mapped + "}\n" + inner + "\n\\end{" + mapped + "}"
            if env in {"equation", "equation*"}:
                return normalize_inline_math_content(inner)
            return content

        def normalize_environment(env: str, inner: str):
            inner = inner.strip()

            if env == "equation":
                return numbered_tight_math_box(normalize_inline_math_content(inner)), env

            if env == "equation*":
                return tight_math_box(normalize_inline_math_content(inner)), env

            if env == "split":
                return tight_math_box("\\begin{aligned}\n" + inner + "\n\\end{aligned}"), env

            if env in inner_math_envs:
                return tight_math_box("\\begin{" + env + "}\n" + inner + "\n\\end{" + env + "}"), env

            if env in display_to_inner:
                mapped = display_to_inner[env]
                return tight_math_box("\\begin{" + mapped + "}\n" + inner + "\n\\end{" + mapped + "}"), env

            if env in ambiguous_display_envs:
                return "\\begin{" + env + "}\n" + inner + "\n\\end{" + env + "}", env

            return None, env

        stripped = formula.strip()
        first_token = stripped.split(None, 1)[0] if stripped else ""
        remainder = stripped[len(first_token):].lstrip() if first_token else ""

        body = None
        converted_env_name = None

        env_name, env_inner = parse_wrapped_environment(stripped)
        if env_name is not None:
            body, converted_env_name = normalize_environment(env_name, env_inner)
        elif first_token in display_envs or first_token in inner_math_envs:
            body, converted_env_name = normalize_environment(first_token, remainder)
        elif (
            (stripped.startswith(r"\[") and stripped.endswith(r"\]")) or
            (stripped.startswith("$$") and stripped.endswith("$$")) or
            (stripped.startswith(r"\(") and stripped.endswith(r"\)")) or
            (len(stripped) >= 2 and stripped.startswith("$") and stripped.endswith("$") and not stripped.startswith("$$"))
        ):
            body = tight_math_box(strip_math_delimiters(stripped))
        else:
            body = tight_math_box(stripped)

        if body is None:
            body = stripped
            if converted_env_name in ambiguous_display_envs:
                self._show_warning(
                    "TexCol - bounding box",
                    "L'ambiente '%s' non e' stato convertito automaticamente in una variante tight.\n\n"
                    "Se vuoi un SVG non tagliato, conviene usare una forma interna come:\n"
                    "  - aligned / alignedat\n"
                    "  - gathered\n"
                    "oppure una formula singola senza delimitatori display."
                    % converted_env_name
                )

        
        tex = (
            "\\documentclass[preview,border=2pt]{standalone}\n"
            f"{preamble}\n"
            "\\begin{document}\n"
            "{\\fontsize{25}{30}\\selectfont\n"
            f"{body}\n"
            "}\n"
            "\\end{document}\n"
        )

        key = self._render_cache_key(compiler=compiler, mode="formula", preamble=preamble, body=body)
        if key == self._last_render_key and self.svg_data:
            self.status.config(text="Already up to date")
            return
        if self._cache_try_load(key):
            self._last_render_key = key
            self.status.config(text="Loaded from cache")
            return

        work_dir, tex_path, pdf_path, svg_path, png_path = self._cache_paths(key)
        work_dir.mkdir(parents=True, exist_ok=True)
        tex_path.write_text(tex, encoding="utf-8")
        t0 = time.perf_counter()

        try:
            subprocess.run(
                [
                    compiler,
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    "-output-directory",
                    str(work_dir),
                    str(tex_path),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            subprocess.run(
                ["dvisvgm", "--pdf", "-n", "-o", str(svg_path), str(pdf_path)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.svg_data = svg_path.read_text(encoding="utf-8")
            self.runtime_svg.write_text(self.svg_data, encoding="utf-8")
            self.png_bytes = cairosvg.svg2png(bytestring=self.svg_data.encode())
            png_path.write_bytes(self.png_bytes)

            self._redraw_preview()
            self._last_render_key = key
            self._cache_gc()
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            self.status.config(text=f"Rendered in {elapsed_ms} ms")

        except subprocess.CalledProcessError as e:
            out = b""
            if getattr(e, "stdout", None):
                out += e.stdout
            if getattr(e, "stderr", None):
                out += b"\n" + e.stderr
            msg = out.decode(errors="replace") if out else str(e)
            self._show_error("LaTeX error", msg)
            self.status.config(text="Error.")
        except FileNotFoundError as e:
            self._show_error(
                "TexCol",
                f"Command not found: {e.filename}\n"
                "Install required packages, for example:\n"
                "  sudo apt install texlive-latex-base dvisvgm"
            )
            self.status.config(text="Error.")


    def open_ppt_web_copy(self):
        if not self.svg_data:
            self._show_warning("TexCol", "No formula generated.")
            return

        self.runtime_svg.write_text(self.svg_data, encoding="utf-8")
        self._write_browser_page()
        self._start_http_server()
        url = f"http://127.0.0.1:{self.httpd.server_port}/{self.browser_page.name}?v={int(time.time() * 1000)}"
        webbrowser.open_new_tab(url)
        self.status.config(text="Opened in browser")

    # ----------------------------
    # Preview
    # ----------------------------
    def _redraw_preview(self, event=None):
        self.preview_canvas.delete("all")

        cw = self.preview_canvas.winfo_width()
        ch = self.preview_canvas.winfo_height()
        if cw < 10 or ch < 10:
            return

        if not self.png_bytes:
            self.preview_canvas.create_text(
                cw // 2,
                ch // 2,
                text="Preview",
                fill=self.colors["muted"],
                font=("DejaVu Sans", 13),
            )
            return

        try:
            img = Image.open(io.BytesIO(self.png_bytes))

            iw, ih = img.size
            scale = min(cw / iw, ch / ih, 1.0)
            new_size = (max(1, int(iw * scale)), max(1, int(ih * scale)))
            img = img.resize(new_size, Image.LANCZOS)

            self.preview_img = ImageTk.PhotoImage(img)
            self.preview_canvas.create_image(cw // 2, ch // 2, anchor="center", image=self.preview_img)
        except Exception:
            self.preview_canvas.create_text(
                cw // 2,
                ch // 2,
                text="Preview error",
                fill=self.colors["muted"],
                font=("DejaVu Sans", 13),
            )

    # ----------------------------
    # Copy SVG (clipboard)
    # ----------------------------
    def copy_svg(self):
        if not self.svg_data:
            self._show_warning("TexCol", "No formula generated.")
            return

        svg_bytes = self.svg_data.encode("utf-8")
        self.runtime_svg.write_text(self.svg_data, encoding="utf-8")
        svg_uri = f"{self.runtime_svg.resolve().as_uri()}\n".encode("utf-8")

        # Wayland: wl-copy (wl-clipboard)
        if shutil.which("wl-copy"):
            try:
                subprocess.run(
                    ["wl-copy", "--type", "text/uri-list"],
                    input=svg_uri,
                    check=True,
                )
                self._show_info("TexCol", "SVG copied as file (URI).")
                return
            except Exception as e:
                try:
                    subprocess.run(
                        ["wl-copy", "--type", "image/svg+xml"],
                        input=svg_bytes,
                        check=True,
                    )
                    self._show_info("TexCol", "SVG copied to clipboard (image/svg+xml).")
                    return
                except Exception:
                    self._show_error("TexCol", f"wl-copy error: {e}")
                    return

        # X11: xclip
        if shutil.which("xclip"):
            try:
                subprocess.run(
                    ["xclip", "-selection", "clipboard", "-t", "text/uri-list", "-i"],
                    input=svg_uri,
                    check=True,
                )
                self._show_info("TexCol", "SVG copied as file (URI).")
                return
            except Exception as e:
                try:
                    subprocess.run(
                        ["xclip", "-selection", "clipboard", "-t", "image/svg+xml", "-i"],
                        input=svg_bytes,
                        check=True,
                    )
                    self._show_info("TexCol", "SVG copied to clipboard (image/svg+xml).")
                    return
                except Exception:
                    self._show_error("TexCol", f"xclip error: {e}")
                    return

        self._show_warning(
            "TexCol",
            "Neither wl-copy nor xclip was found.\n"
            "Install one of:\n"
            "  sudo apt install wl-clipboard\n"
            "  sudo apt install xclip\n\n"
            "Alternatively, use drag and drop or Download."
        )

    # ----------------------------
    # Download SVG
    # ----------------------------
    def download_svg(self):
        if not self.svg_data:
            self._show_warning("TexCol", "No formula generated.")
            return

        path = filedialog.asksaveasfilename(
            title="Save SVG",
            defaultextension=".svg",
            initialfile="formula.svg",
            filetypes=[("SVG", "*.svg"), ("All files", "*.*")],
        )
        if not path:
            return

        out_path = Path(path)
        try:
            out_path.write_text(self.svg_data, encoding="utf-8")
            self.status.config(text="SVG saved")
            self._show_info("TexCol", f"SVG saved to:\n{out_path}")
        except Exception as e:
            self._show_error("TexCol", f"Unable to save SVG:\n{e}")

# ----------------------------
# Main
# ----------------------------
if __name__ == "__main__":
    root = TkinterDnD.Tk(baseName="texcol", className="TexCol")
    root.title("TexCol")

    try:
        icon_path = Path("/home/andrea-maestri/user/TexCol_app/texcol.png")
        if icon_path.exists():
            icon_img = Image.open(icon_path).convert("RGBA")
            icon_img.thumbnail((128, 128), Image.LANCZOS)
            ico = ImageTk.PhotoImage(icon_img)
            root.iconphoto(True, ico)
            root._texcol_icon = ico
    except Exception as e:
        print("ICON ERROR:", repr(e))

    app = TexColApp(root)
    root.mainloop()