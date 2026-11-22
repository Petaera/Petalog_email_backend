"""Render every template with sample data into ./previews/ (git-ignored).

    python scripts/render_previews.py

Open the .html files in a browser to review the design. No network, no
Supabase, no email is sent.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from petalog_reports.render import render_email  # noqa: E402
from petalog_reports.sample import sample_report  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "previews")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # the ₹ sign on Windows consoles
    os.makedirs(OUT, exist_ok=True)
    cases = [(t, n, False) for t in (1, 2, 3) for n in (1, 3)] + [(1, 1, True)]
    for template, locations, quiet in cases:
        report = sample_report(template, locations, quiet=quiet)
        email = render_email(report, app_url="https://petalog.in",
                             logo_url="https://petalog.in/android-chrome-512x512.png",
                             unsubscribe_url="https://example.invalid/v1/unsubscribe?t=sample",
                             attachment_note="Full details are attached as an Excel workbook.")
        name = f"template{template}_{'multi' if locations > 1 else 'single'}{'_quiet' if quiet else ''}"
        with open(os.path.join(OUT, name + ".html"), "w", encoding="utf-8") as fh:
            fh.write(email.html)
        with open(os.path.join(OUT, name + ".txt"), "w", encoding="utf-8") as fh:
            fh.write(f"Subject: {email.subject}\nPreheader: {email.preheader}\n\n{email.text}")
        print(f"{name}: {email.subject}")


if __name__ == "__main__":
    main()
