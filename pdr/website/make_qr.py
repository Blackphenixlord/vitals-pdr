"""Make the QR codes for the website (currently https://joshuacollado636.wixsite.com/vitals).

    pip install qrcode[pil]
    python pdr/website/make_qr.py https://your-site-url/

Writes pdr/website/qr.png (the website). The header board and the brochure use it.
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
for name, target in (("qr.png", url),):
    out = Path(__file__).with_name(name)
    qrcode.make(target, box_size=20, border=2,
                error_correction=qrcode.constants.ERROR_CORRECT_M).save(out)
    print(f"wrote {out}  ->  {target}")
