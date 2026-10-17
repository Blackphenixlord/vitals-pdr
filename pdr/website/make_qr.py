"""Make the header-board QR code once the website is live.

    pip install qrcode[pil]
    python pdr/website/make_qr.py https://your-site-url/

Writes pdr/website/qr.png (the website) and qr_specs.png (the site's #specs section).
The header board uses qr.png; the brochure uses both - then re-run pdr/brochure/make_pdf.py.
Print them at least 3 cm wide. Scan them with a phone before printing.
"""

import sys
from pathlib import Path

try:
    import qrcode
except ImportError:
    raise SystemExit("pip install qrcode[pil]   (then run this again)")

if len(sys.argv) != 2 or not sys.argv[1].startswith("http"):
    raise SystemExit("usage: python pdr/website/make_qr.py https://your-site-url/")

url = sys.argv[1].split("#")[0]
for name, target in (("qr.png", url), ("qr_specs.png", url + "#specs")):
    out = Path(__file__).with_name(name)
    qrcode.make(target, box_size=20, border=2,
                error_correction=qrcode.constants.ERROR_CORRECT_M).save(out)
    print(f"wrote {out}  ->  {target}")
