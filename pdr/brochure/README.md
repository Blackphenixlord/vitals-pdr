# Brochure

Tri-fold, US Letter landscape, printed both sides (flip on short edge). Same look as the website:
Tektur + IBM Plex Sans (in `fonts/`, OFL), navy/red palette, the VITALS emblem.

- `brochure.pdf` — print this
- `brochure.html` — the source. Edit, then rebuild:

```bash
pip install playwright && python -m playwright install chromium
python pdr/brochure/build.py
```

Page 1 (outside): problem flap · team + QR (back) · cover. Page 2 (inside): core features · how it works +
numbers · the prototype.
