"""
PDF → Dark Mode (Inverted) Converter
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

# ── Core conversion ───────────────────────────────────────────────────────────
def make_inverted(input_path: str, output_path: str, on_progress=None):
    doc = fitz.open(input_path)
    out = fitz.open()
    total = len(doc)

    for i, page in enumerate(doc):
        mat = fitz.Matrix(4, 4)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)

        samples = bytearray(pix.samples)
        for j in range(len(samples)):
            samples[j] = 255 - samples[j]

        inv_pix = fitz.Pixmap(fitz.csGRAY, pix.width, pix.height,
                              bytes(samples), False)

        img_pdf  = fitz.open()
        img_page = img_pdf.new_page(width=inv_pix.width, height=inv_pix.height)
        img_page.insert_image(img_page.rect, stream=inv_pix.tobytes("png"))
        out.insert_pdf(img_pdf)
        img_pdf.close()

        if on_progress:
            on_progress(i + 1, total)

    toc = doc.get_toc(simple=True)
    if toc:
        out.set_toc(toc)

    out.save(
        output_path,
        garbage=4,
        deflate=True,
        deflate_images=True,
        deflate_fonts=True,
    )
    doc.close()
    out.close()


# ── GUI ───────────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF → Dark Mode")
        self.geometry("520x340")
        self.resizable(False, False)
        self.configure(bg=BG)

        self._input_path  = tk.StringVar()
        self._output_path = tk.StringVar()
        self._running     = False
        self._bar_fill    = None

        self._build_ui()

    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────────────────
        tk.Label(self, text="PDF → Dark Mode",
                 bg=BG, fg=ACCENT, font=("Helvetica", 15, "bold")
                 ).pack(pady=(28, 2))
        tk.Label(self, text="Invert PDF colours for a dark-theme reading experience",
                 bg=BG, fg=MUTED, font=("Helvetica", 9)
                 ).pack(pady=(0, 20))

        # ── File rows ─────────────────────────────────────────────────────────
        self._file_row("Input PDF",  self._input_path,  self._browse_input)
        self._file_row("Output PDF", self._output_path, self._browse_output)

        # ── Progress bar ──────────────────────────────────────────────────────
        self._bar_canvas = tk.Canvas(self, height=6, bg=BORDER,
                                     highlightthickness=0, bd=0)
        self._bar_canvas.pack(fill="x", padx=28, pady=(20, 0))
        self._bar_canvas.update_idletasks()
        self._bar_fill = self._bar_canvas.create_rectangle(
            0, 0, 0, 6, fill=PROGRESS, outline="")

        # ── Status ────────────────────────────────────────────────────────────
        self._status = tk.Label(self, text="Select an input PDF to begin.",
                                bg=BG, fg=MUTED, font=("Helvetica", 9),
                                wraplength=460, justify="center")
        self._status.pack(pady=(8, 0))

        # ── Convert button ────────────────────────────────────────────────────
        self._btn = tk.Button(
            self, text="Convert", command=self._start,
            bg=BTN_BG, fg=ACCENT, activebackground=BTN_HOV,
            activeforeground=ACCENT, relief="flat", cursor="hand2",
            font=("Helvetica", 11, "bold"), width=18, height=2, bd=0)
        self._btn.pack(pady=(18, 0))
        self._btn.bind("<Enter>", lambda e: self._btn.config(bg=BTN_HOV))
        self._btn.bind("<Leave>", lambda e: self._btn.config(bg=BTN_BG))

    def _file_row(self, label_text, var, browse_cmd):
        frame = tk.Frame(self, bg=BG)
        frame.pack(fill="x", padx=28, pady=4)

        tk.Label(frame, text=label_text, bg=BG, fg=MUTED,
                 font=("Helvetica", 9), width=10, anchor="w"
                 ).pack(side="left")

        tk.Entry(frame, textvariable=var, bg=SURFACE, fg=ACCENT,
                 insertbackground=ACCENT, relief="flat",
                 font=("Helvetica", 9), highlightthickness=1,
                 highlightbackground=BORDER, highlightcolor=PROGRESS
                 ).pack(side="left", fill="x", expand=True, ipady=6)

        btn = tk.Button(frame, text="Browse", command=browse_cmd,
                        bg=BTN_BG, fg=ACCENT, activebackground=BTN_HOV,
                        activeforeground=ACCENT, relief="flat",
                        cursor="hand2", font=("Helvetica", 9),
                        width=7, bd=0, pady=6)
        btn.pack(side="left", padx=(6, 0))
        btn.bind("<Enter>", lambda e: btn.config(bg=BTN_HOV))
        btn.bind("<Leave>", lambda e: btn.config(bg=BTN_BG))

    # ── Browse handlers ───────────────────────────────────────────────────────
    def _browse_input(self):
        path = filedialog.askopenfilename(
            title="Select PDF", filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        self._input_path.set(path)
        base, _ = os.path.splitext(path)
        self._output_path.set(base + "_dark.pdf")
        self._set_status("Ready — click Convert.", MUTED)

    def _browse_output(self):
        path = filedialog.asksaveasfilename(
            title="Save as", defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")])
        if path:
            self._output_path.set(path)

    # ── Conversion ────────────────────────────────────────────────────────────
    def _start(self):
        inp = self._input_path.get().strip()
        out = self._output_path.get().strip()

        if not inp:
            self._set_status("Please choose an input PDF.", ERROR); return
        if not os.path.isfile(inp):
            self._set_status("Input file not found.", ERROR); return
        if not out:
            self._set_status("Please choose an output path.", ERROR); return
        if self._running:
            return

        self._running = True
        self._btn.config(state="disabled", text="Converting…")
        self._set_bar(0)
        self._set_status("Starting conversion…", MUTED)
        threading.Thread(target=self._worker, args=(inp, out), daemon=True).start()

    def _worker(self, inp, out):
        try:
            def progress(done, total):
                self.after(0, self._set_bar, done / total)
                self.after(0, self._set_status,
                           f"Page {done} of {total}…", MUTED)

            make_inverted(inp, out, on_progress=progress)
            self.after(0, self._on_done, out)
        except Exception as exc:
            self.after(0, self._on_error, str(exc))

    def _on_done(self, out_path):
        self._running = False
        self._set_bar(1.0)
        self._btn.config(state="normal", text="Convert")
        self._set_status(f"✓  Saved: {os.path.basename(out_path)}", SUCCESS)

    def _on_error(self, msg):
        self._running = False
        self._set_bar(0)
        self._btn.config(state="normal", text="Convert")
        self._set_status(f"Error: {msg}", ERROR)
        messagebox.showerror("Conversion failed", msg)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _set_bar(self, fraction: float):
        if self._bar_fill is None:
            return
        self._bar_canvas.update_idletasks()
        w = self._bar_canvas.winfo_width()
        self._bar_canvas.coords(self._bar_fill, 0, 0, int(w * fraction), 6)

    def _set_status(self, msg: str, color: str = MUTED):
        self._status.config(text=msg, fg=color)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
