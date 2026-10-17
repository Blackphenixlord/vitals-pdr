"""Render the brochure to PDF (US Letter, landscape, two pages).

    pip install playwright        (once; uses any Chromium playwright already has)
    python pdr/brochure/make_pdf.py

Writes pdr/brochure/brochure.pdf. Print double-sided, flip on the SHORT edge,
then fold in three. Re-run after making the QR codes (pdr/website/make_qr.py).
"""

import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent


def chromium_path():
    """Use a Chromium playwright already downloaded, if the bundled one is missing."""
    root = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".cache")) / "ms-playwright"
    for exe in sorted(root.glob("chromium-*/chrome-*/chrome*"), reverse=True):
        if exe.name in ("chrome.exe", "chrome"):
            return str(exe)
    return None


with sync_playwright() as p:
    try:
        browser = p.chromium.launch()
    except Exception:
        path = chromium_path()
        if not path:
            sys.exit("No Chromium found - run: python -m playwright install chromium")
        browser = p.chromium.launch(executable_path=path)
    page = browser.new_page()
    page.goto((HERE / "brochure.html").as_uri())
    page.wait_for_timeout(500)
    out = HERE / "brochure.pdf"
    page.pdf(path=str(out), width="11in", height="8.5in", print_background=True,
             margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
    browser.close()
print(f"wrote {out}")
