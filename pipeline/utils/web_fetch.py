"""Fetch and extract main article text from a URL using trafilatura."""

import trafilatura


def fetch_article(url: str, max_chars: int = 8000) -> tuple[str, str]:
    """Returns (article_text, error). On success error is empty.
    On failure article_text is empty and error explains why.
    Article text is truncated to max_chars."""
    url = (url or "").strip()
    if not url:
        return "", ""
    if not (url.startswith("http://") or url.startswith("https://")):
        return "", f"URL must start with http:// or https:// (got {url!r})"
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return "", f"failed to download {url}"
        extracted = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=False,
            favor_recall=True,
        )
        if not extracted or not extracted.strip():
            return "", f"no extractable article text at {url}"
        return extracted.strip()[:max_chars], ""
    except Exception as e:
        return "", f"fetch failed: {e}"
