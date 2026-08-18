import re
from urllib.parse import urlparse


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def normalize_domain(url: str | None) -> str | None:
    """Strip scheme/www/path/query so the same company's URLs across sources
    dedupe to the same key, e.g. 'https://www.acme.io/?ref=yc' -> 'acme.io'."""
    if not url:
        return None
    parsed = urlparse(url if "://" in url else f"//{url}", scheme="")
    host = (parsed.netloc or parsed.path).lower()
    host = host.split("/")[0].split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return host or None
