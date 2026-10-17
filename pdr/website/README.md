# Website

`index.html` is the whole site — one page plus `img/` and `emblem.svg`, works on a phone. It uses the same colors, fonts and emblem as the app and the brochure. Copy the whole `website/` folder when you host it.

## Hosting it (pick one)

The repo is **private**, so GitHub Pages on this repo needs a paid plan (or GitHub's free student
pack). Simplest options:

1. **Your existing site** — copy the `website/` folder into the `Blackphenixlord.github.io` repo as
   `vitals/` → `https://blackphenixlord.github.io/vitals/`.
2. **Google Sites** — the HUNCH list allows a Google Site; paste the sections in.

Then: `python pdr/website/make_qr.py <url>` → `qr.png` (header board + brochure) and `qr_specs.png` (brochure), then `python pdr/brochure/make_pdf.py`. Scan them before printing.

Before PDR: replace the Videos line with the two uploaded video links.
