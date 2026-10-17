"""Make the header-board QR code once the website is live.

    pip install qrcode[pil]
    python pdr/website/make_qr.py https://your-site-url/

Writes pdr/website/qr.png (print it at least 3 cm wide so phones scan it from a table away).
Scan it with a phone before printing the board.
"""

import sys
from pathlib import Path

try:
    import qrcode
except ImportError:
    raise SystemExit("pip install qrcode[pil]   (then run this again)")

if len(sys.argv) != 2 or not sys.argv[1].startswith("http"):
    raise SystemExit("usage: python pdr/website/make_qr.py https://your-site-url/")

out = Path(__file__).with_name("qr.png")
image = qrcode.make(sys.argv[1], box_size=20, border=2,
                    error_correction=qrcode.constants.ERROR_CORRECT_M)
image.save(out)
print(f"wrote {out}  ->  {sys.argv[1]}")
