from datetime import datetime
from slugify import slugify


def make_slug(topic: str) -> str:
    base = slugify(topic, max_length=40, word_boundary=True)
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{base}" if base else stamp
