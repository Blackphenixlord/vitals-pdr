# Website

**Live:** https://joshuacollado636.wixsite.com/vitals — built in Wix (Harmony editor). Fonts: Tektur
(headings) + IBM Plex Sans (body). Colors: navy `#0A0E1A`, card `#161A25`, red `#E73337`. The brochure uses
the same fonts and colors.

- `qr.png` → the website (header board + brochure)

Edit the site in the Wix editor. If the link ever changes (e.g. a custom domain):
`python pdr/website/make_qr.py <new-url>`, then rebuild the brochure (`pdr/brochure/`) and re-print the
header board QR.

Before PDR: add the two video links to the site once they're uploaded.
