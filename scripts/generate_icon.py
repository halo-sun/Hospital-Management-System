#!/usr/bin/env python3
"""Generate the application icon in PNG and multi-resolution ICO formats.

Produces:
  assets/icon.png  — 256×256 source PNG (Linux desktop entry)
  assets/icon.ico  — Multi-resolution ICO (16, 24, 32, 48, 64, 128, 256)

Run once from the project root:
    python scripts/generate_icon.py
"""
from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw, ImageFont

# ── Design constants (matches src/gui/theme.py primary palette) ──
PRIMARY = (44, 62, 80)       # #2C3E50 — dark blue-grey
ACCENT = (52, 152, 219)     # #3498DB — bright blue
WHITE = (255, 255, 255)
ICON_SIZES_ICO = (16, 24, 32, 48, 64, 128, 256)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")


def _draw_cross(size: int) -> Image.Image:
    """Draw a medical cross icon at the given pixel size."""
    img = Image.new("RGBA", (size, size), PRIMARY)
    draw = ImageDraw.Draw(img)

    # Rounded-rectangle background via filled circle + rect
    margin = max(1, size // 16)
    corner_r = max(2, size // 6)
    draw.rounded_rectangle(
        [margin, margin, size - margin - 1, size - margin - 1],
        radius=corner_r,
        fill=PRIMARY,
    )

    # Cross dimensions
    cx, cy = size // 2, size // 2
    arm_w = max(2, size // 5)    # cross arm width
    arm_len = max(3, size // 3)  # cross arm half-length

    # Vertical bar
    draw.rounded_rectangle(
        [cx - arm_w // 2, cy - arm_len, cx + arm_w // 2, cy + arm_len],
        radius=max(1, arm_w // 4),
        fill=WHITE,
    )
    # Horizontal bar
    draw.rounded_rectangle(
        [cx - arm_len, cy - arm_w // 2, cx + arm_len, cy + arm_w // 2],
        radius=max(1, arm_w // 4),
        fill=WHITE,
    )

    # Small accent dot at cross center for visual interest
    dot_r = max(1, arm_w // 4)
    draw.ellipse(
        [cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r],
        fill=ACCENT,
    )

    return img


def main() -> None:
    os.makedirs(ASSETS_DIR, exist_ok=True)

    # Generate 256×256 source PNG
    png_path = os.path.join(ASSETS_DIR, "icon.png")
    icon_256 = _draw_cross(256)
    icon_256.save(png_path, "PNG")
    print(f"Saved {png_path}")

    # Generate multi-resolution ICO
    ico_path = os.path.join(ASSETS_DIR, "icon.ico")
    images = [_draw_cross(s) for s in ICON_SIZES_ICO]
    # Pillow's ICO writer takes the first image as the base;
    # additional sizes are passed via append_images.
    images[0].save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in ICON_SIZES_ICO],
        append_images=images[1:],
    )
    print(f"Saved {ico_path} ({len(ICON_SIZES_ICO)} sizes: {ICON_SIZES_ICO})")


if __name__ == "__main__":
    main()
