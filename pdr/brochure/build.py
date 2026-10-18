"""Rebuild brochure.pdf from brochure.html (needs playwright + chromium)."""
from pathlib import Path
from playwright.sync_api import sync_playwright

src = Path(__file__).with_name("brochure.html").resolve()
with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page()
    pg.goto(src.as_uri())
    pg.wait_for_timeout(500)
    pg.pdf(path=str(src.with_suffix(".pdf")), width="11in", height="8.5in", print_background=True)
    b.close()
print("wrote", src.with_suffix(".pdf"))
