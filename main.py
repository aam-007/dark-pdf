"""
PDF → Black & White Converter
Requires: pip install pymupdf
Tkinter ships with standard Python (no extra install needed).
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os

try:
    import fitz  # PyMuPDF
except ImportError:
    raise SystemExit("PyMuPDF not found. Run: pip install pymupdf")

# ── Palette ──────────────────────────────────────────────────────────────────
BG       = "#1a1a1a"
SURFACE  = "#242424"
BORDER   = "#333333"
ACCENT   = "#e0e0e0"
MUTED    = "#888888"
BTN_BG   = "#2e2e2e"
BTN_HOV  = "#3a3a3a"
SUCCESS  = "#6fcf97"
ERROR    = "#eb5757"
PROGRESS = "#4a90e2"

# ── Helpers ───────────────────────────────────────────────────────────────────
def make_bw(input_path: str, output_path: str, on_progress=None):
    """Render every page to greyscale and reassemble as a PDF."""
    doc = fitz.open(input_path)
    out = fitz.open()
    total = len(doc)

    for i, page in enumerate(doc):
        # Render at 2× resolution for crisp output
        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
        img_pdf = fitz.open("pdf", pix.pdfocr_tobytes())   # embed as 1-page PDF
        out.insert_pdf(img_pdf)
        if on_progress:
            on_progress(i + 1, total)

    out.save(output_path, garbage=4, deflate=True)
    doc.close()
    out.close()


# ── Main Window ───────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF → B&W")
        self.geometry("480x360")
        self.resizable(False, False)
        self.configure(bg=BG)

        self._input_path  = tk.StringVar()
        self._output_path = tk.StringVar()
        self._status      = tk.StringVar(value="Select a PDF to get started.")
        self._progress    = tk.DoubleVar(value=0)
        self._running     = False

        self._build()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build(self):
        pad = dict(padx=24)

        # Title
        tk.Label(self, text="PDF → Black & White",
                 bg=BG, fg=ACCENT, font=("Helvetica", 15, "bold")
                 ).pack(pady=(28, 4))
        tk.Label(self, text="Convert any PDF to greyscale",
                 bg=BG, fg=MUTED, font=("Helvetica", 10)
                 ).pack(pady=(0, 22))

        # Input row
        self._file_row("Input PDF", self._input_path,
                        self._browse_input, **pad)

        # Output row
        self._file_row("Output PDF", self._output_path,
                        self._browse_output, **pad)

        # Progress bar (custom canvas)
        self._bar_bg = tk.Canvas(self, height=6, bg=BORDER,
                                 highlightthickness=0, bd=0)
        self._bar_bg.pack(fill="x", padx=24, pady=(22, 0))
        self._bar_fill = self._bar_bg.create_rectangle(
            0, 0, 0, 6, fill=PROGRESS, outline="")

        # Status label
        tk.Label(self, textvariable=self._status,
                 bg=BG, fg=MUTED, font=("Helvetica", 9),
                 wraplength=420, justify="center"
                 ).pack(pady=(8, 0))

        # Convert button
        self._btn = self._flat_button(self, "Convert", self._start,
                                      bg=BTN_BG, fg=ACCENT,
                                      font=("Helvetica", 11, "bold"),
                                      width=18, height=2)
        self._btn.pack(pady=(20, 0))

    def _file_row(self, label, var, cmd, **pack_kw):
        frame = tk.Frame(self, bg=BG)
        frame.pack(fill="x", pady=5, **pack_kw)

        tk.Label(frame, text=label, bg=BG, fg=MUTED,
                 font=("Helvetica", 9), width=10, anchor="w"
                 ).pack(side="left")

        entry = tk.Entry(frame, textvariable=var, bg=SURFACE,
                         fg=ACCENT, insertbackground=ACCENT,
                         relief="flat", font=("Helvetica", 9),
                         highlightthickness=1,
                         highlightbackground=BORDER,
                         highlightcolor=PROGRESS)
        entry.pack(side="left", fill="x", expand=True, ipady=6)

        btn = self._flat_button(frame, "Browse", cmd,
                                bg=BTN_BG, fg=ACCENT,
                                font=("Helvetica", 9), width=7)
        btn.pack(side="left", padx=(6, 0))

    @staticmethod
    def _flat_button(parent, text, cmd, **kw):
        """Borderless flat button with hover effect."""
        b = tk.Button(parent, text=text, command=cmd,
                      relief="flat", cursor="hand2",
                      activeforeground=ACCENT,
                      activebackground=BTN_HOV,
                      bd=0, pady=6, **kw)
        b.bind("<Enter>", lambda e: b.config(bg=BTN_HOV))
        b.bind("<Leave>", lambda e: b.config(bg=kw.get("bg", BTN_BG)))
        return b

    # ── Actions ───────────────────────────────────────────────────────────────
    def _browse_input(self):
        path = filedialog.askopenfilename(
            title="Select PDF", filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        self._input_path.set(path)
        # Auto-suggest output path
        base, _ = os.path.splitext(path)
        self._output_path.set(base + "_bw.pdf")
        self._status.set("Ready. Click Convert when you're set.")

    def _browse_output(self):
        path = filedialog.asksaveasfilename(
            title="Save as", defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")])
        if path:
            self._output_path.set(path)

    def _start(self):
        inp = self._input_path.get().strip()
        out = self._output_path.get().strip()

        if not inp:
            self._flash_status("Please choose an input PDF.", ERROR)
            return
        if not os.path.isfile(inp):
            self._flash_status("Input file not found.", ERROR)
            return
        if not out:
            self._flash_status("Please choose an output path.", ERROR)
            return
        if self._running:
            return

        self._running = True
        self._btn.config(state="disabled", text="Converting…")
        self._progress.set(0)
        self._set_bar(0)
        self._status.set("Converting…")

        threading.Thread(target=self._run,
                         args=(inp, out), daemon=True).start()

    def _run(self, inp, out):
        try:
            def progress(done, total):
                pct = done / total
                self.after(0, self._set_bar, pct)
                self.after(0, self._status.set,
                           f"Page {done} / {total}")

            make_bw(inp, out, on_progress=progress)
            self.after(0, self._done, out)
        except Exception as exc:
            self.after(0, self._error, str(exc))

    def _done(self, out_path):
        self._running = False
        self._set_bar(1.0)
        self._btn.config(state="normal", text="Convert")
        self._flash_status(f"✓ Saved: {os.path.basename(out_path)}", SUCCESS)

    def _error(self, msg):
        self._running = False
        self._set_bar(0)
        self._btn.config(state="normal", text="Convert")
        self._flash_status(f"Error: {msg}", ERROR)
        messagebox.showerror("Conversion failed", msg)

    # ── Utilities ─────────────────────────────────────────────────────────────
    def _set_bar(self, fraction: float):
        self._bar_bg.update_idletasks()
        w = self._bar_bg.winfo_width()
        self._bar_bg.coords(self._bar_fill, 0, 0, int(w * fraction), 6)

    def _flash_status(self, msg, color):
        self._status.set(msg)
        # find the status label and recolour it
        for widget in self.winfo_children():
            if isinstance(widget, tk.Label) and \
               widget.cget("textvariable") == str(self._status):
                widget.config(fg=color)
                break
        # find it by traversing properly
        self._recolor_status(self, color)

    def _recolor_status(self, parent, color):
        for w in parent.winfo_children():
            if isinstance(w, tk.Label):
                try:
                    if str(w.cget("textvariable")) == str(self._status):
                        w.config(fg=color)
                        return True
                except Exception:
                    pass
            if self._recolor_status(w, color):
                return True
        return False


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
