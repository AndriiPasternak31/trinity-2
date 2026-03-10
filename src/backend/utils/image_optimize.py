"""Image optimization utilities for avatar generation."""

import io

from PIL import Image


def optimize_avatar(image_bytes: bytes, max_size: int = 512) -> bytes:
    """Resize and convert avatar image to WebP.

    Takes raw image bytes (typically PNG from Gemini at ~1024x1024),
    resizes to fit within max_size x max_size preserving aspect ratio,
    and returns WebP-encoded bytes at quality=85.

    Args:
        image_bytes: Raw image data (PNG, JPEG, etc.)
        max_size: Maximum width/height in pixels (default 512)

    Returns:
        WebP-encoded image bytes
    """
    img = Image.open(io.BytesIO(image_bytes))
    img.thumbnail((max_size, max_size), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=85)
    return buf.getvalue()
