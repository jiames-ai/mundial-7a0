from __future__ import annotations

import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCALES = ("en", "de", "ja", "pt", "es", "fr", "it", "tr", "zh")
PAGES = ("privacy", "terms", "contact", "disclaimer")
CSP = (
    "default-src 'self' data: blob:; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' data: https://fonts.gstatic.com; "
    "img-src 'self' data: blob:; "
    "connect-src 'self'; frame-src 'none'; object-src 'none'; base-uri 'self'"
)
HEAD_MARKER = '<meta name="mirror-runtime" content="ad-free-i18n"/>'
HEAD_INSERT = (
    HEAD_MARKER
    + f'<meta http-equiv="Content-Security-Policy" content="{CSP}"/>'
    + '<link rel="stylesheet" href="/mirror.css"/>'
)
BODY_INSERT = '<script src="/mirror-runtime.js" defer></script>'


def copy_page(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def inject(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r'<script\b[^>]*\bsrc="https://(?:pagead2\.googlesyndication\.com|www\.googletagmanager\.com|static\.cloudflareinsights\.com|[^"/]+\.(?:effectivecpmnetwork|highperformanceformat)\.com)/[^">]*"[^>]*>\s*</script>',
        "",
        text,
        flags=re.IGNORECASE,
    )
    if HEAD_MARKER in text:
        path.write_text(text, encoding="utf-8")
        return
    head, remainder = text.split("</head>", 1)
    head = re.sub(
        r'<script\s+async=""\s+crossorigin="anonymous"\s+src="https://pagead2\.googlesyndication\.com/[^\"]+"></script>',
        "",
        head,
    )
    head = re.sub(
        r'<link\s+rel="preload"\s+href="https://www\.googletagmanager\.com/[^\"]+"\s+as="script"/>',
        "",
        head,
    )
    head = re.sub(r'<meta\s+name="google-adsense-account"\s+content="[^"]+"/>', "", head)
    head = head.replace("<head>", f"<head>{HEAD_INSERT}", 1)
    text = f"{head}</head>{remainder}"
    text = text.replace("</body>", f"{BODY_INSERT}</body>", 1)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    sources = {
        "home": ROOT / "index.html",
        **{page: ROOT / page / "index.html" for page in PAGES},
    }

    for locale in LOCALES:
        copy_page(sources["home"], ROOT / locale / "index.html")
        for page in PAGES:
            copy_page(sources[page], ROOT / locale / page / "index.html")

    legacy_aliases = {
        "privacidad": "privacy",
        "terminos": "terms",
        "aviso-legal": "disclaimer",
        "privacidade": "privacy",
        "termos": "terms",
        "aviso-legal-pt": "disclaimer",
    }
    for alias, page in legacy_aliases.items():
        copy_page(sources[page], ROOT / alias / "index.html")

    for path in ROOT.rglob("index.html"):
        inject(path)

    print(f"prepared {len(list(ROOT.rglob('index.html')))} HTML pages")


if __name__ == "__main__":
    main()
