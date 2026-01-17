#!/usr/bin/env python3
"""
PWA Icon Generator for LetsGoal
Generates all required PWA icons with lotus gradient colors.
"""

import os
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Installing Pillow...")
    os.system("pip3 install Pillow")
    from PIL import Image, ImageDraw

# Lotus gradient colors
GRADIENT_START = (102, 126, 234)  # #667eea
GRADIENT_END = (118, 75, 162)     # #764ba2

# Icon sizes required for PWA
ICON_SIZES = [72, 96, 128, 144, 152, 192, 384, 512]
APPLE_ICON_SIZE = 180
FAVICON_SIZES = [16, 32]

OUTPUT_DIR = Path(__file__).parent.parent / "frontend" / "assets" / "icons"


def interpolate_color(color1, color2, factor):
    """Interpolate between two colors."""
    return tuple(int(c1 + (c2 - c1) * factor) for c1, c2 in zip(color1, color2))


def create_gradient_icon(size, safe_zone_percent=0.1):
    """Create a circular icon with gradient background."""
    # Create image with transparency
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Calculate safe zone padding (for maskable icons)
    padding = int(size * safe_zone_percent)
    circle_size = size - (padding * 2)

    # Draw gradient circle
    for y in range(padding, size - padding):
        for x in range(padding, size - padding):
            # Check if point is within circle
            center_x = size // 2
            center_y = size // 2
            distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
            radius = circle_size // 2

            if distance <= radius:
                # Calculate gradient factor (diagonal)
                factor = (x + y) / (2 * size)
                color = interpolate_color(GRADIENT_START, GRADIENT_END, factor)
                img.putpixel((x, y), (*color, 255))

    # Draw "LG" text in center (simplified lotus representation)
    # Using a simple approach without fonts - draw a lotus-like shape
    center_x = size // 2
    center_y = size // 2

    # Draw simple lotus shape (3 petals)
    petal_size = size // 6
    white_color = (255, 255, 255, 230)

    # Center dot
    dot_radius = max(2, size // 20)
    for y in range(center_y - dot_radius, center_y + dot_radius + 1):
        for x in range(center_x - dot_radius, center_x + dot_radius + 1):
            if ((x - center_x) ** 2 + (y - center_y) ** 2) <= dot_radius ** 2:
                if 0 <= x < size and 0 <= y < size:
                    img.putpixel((x, y), white_color)

    # Top petal (ellipse)
    petal_height = petal_size * 2
    petal_width = petal_size
    for dy in range(-petal_height, 1):
        for dx in range(-petal_width, petal_width + 1):
            # Ellipse equation
            if (dx / petal_width) ** 2 + (dy / petal_height) ** 2 <= 1:
                x = center_x + dx
                y = center_y + dy - dot_radius
                if 0 <= x < size and 0 <= y < size:
                    # Check if within main circle
                    dist = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
                    if dist <= (circle_size // 2) - 2:
                        img.putpixel((x, y), white_color)

    # Bottom left petal
    for dy in range(0, petal_height + 1):
        for dx in range(-petal_width, 1):
            if (dx / petal_width) ** 2 + (dy / petal_height) ** 2 <= 1:
                x = center_x + dx - dot_radius // 2
                y = center_y + dy + dot_radius // 2
                if 0 <= x < size and 0 <= y < size:
                    dist = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
                    if dist <= (circle_size // 2) - 2:
                        img.putpixel((x, y), white_color)

    # Bottom right petal
    for dy in range(0, petal_height + 1):
        for dx in range(0, petal_width + 1):
            if (dx / petal_width) ** 2 + (dy / petal_height) ** 2 <= 1:
                x = center_x + dx + dot_radius // 2
                y = center_y + dy + dot_radius // 2
                if 0 <= x < size and 0 <= y < size:
                    dist = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
                    if dist <= (circle_size // 2) - 2:
                        img.putpixel((x, y), white_color)

    return img


def create_favicon_ico(sizes=[16, 32]):
    """Create a multi-resolution favicon.ico file."""
    images = []
    for size in sizes:
        img = create_gradient_icon(size, safe_zone_percent=0.05)
        images.append(img)
    return images


def main():
    """Generate all PWA icons."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Generating PWA icons in {OUTPUT_DIR}")

    # Generate standard PWA icons
    for size in ICON_SIZES:
        icon = create_gradient_icon(size)
        filename = f"icon-{size}x{size}.png"
        icon.save(OUTPUT_DIR / filename, 'PNG')
        print(f"  ✓ {filename}")

    # Generate Apple Touch Icon
    apple_icon = create_gradient_icon(APPLE_ICON_SIZE)
    apple_icon.save(OUTPUT_DIR / "apple-touch-icon.png", 'PNG')
    print(f"  ✓ apple-touch-icon.png")

    # Generate favicons
    for size in FAVICON_SIZES:
        icon = create_gradient_icon(size, safe_zone_percent=0.05)
        filename = f"favicon-{size}x{size}.png"
        icon.save(OUTPUT_DIR / filename, 'PNG')
        print(f"  ✓ {filename}")

    # Generate favicon.ico (multi-resolution)
    ico_images = create_favicon_ico()
    ico_images[0].save(
        OUTPUT_DIR / "favicon.ico",
        format='ICO',
        sizes=[(16, 16), (32, 32)]
    )
    print(f"  ✓ favicon.ico")

    # Generate maskable icon (with extra safe zone)
    maskable = create_gradient_icon(512, safe_zone_percent=0.15)
    maskable.save(OUTPUT_DIR / "maskable-icon-512x512.png", 'PNG')
    print(f"  ✓ maskable-icon-512x512.png")

    print(f"\nAll icons generated successfully!")


if __name__ == "__main__":
    main()
