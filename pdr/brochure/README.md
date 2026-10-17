# Brochure

`brochure.pdf` — US Letter, landscape, 2 pages. Print **double-sided, flip on the short edge**, fold in three.
Same colors, fonts, emblem and screenshots as the app and the website.

Before printing:
1. Fill in `[ School name ]`, `[ school number ]` and `[ City ]` in `brochure.html`.
2. Host the website, then `python pdr/website/make_qr.py <site-url>` (makes both QR codes).
3. `python pdr/brochure/make_pdf.py` to rebuild the PDF.

Covers the HUNCH brochure list: school, team, NASA project name, team project name, teacher,
city/state, description, value statement, top attributes, prototype pictures (screen captures — no
students), website QR, technical specs + QR, functional diagram.
