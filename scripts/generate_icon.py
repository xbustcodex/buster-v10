# scripts/generate_icon.py
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw


def create_buster_icon() -> None:
    asset_dir = Path("buster/ui/v9/assets")
    asset_dir.mkdir(parents=True, exist_ok=True)
    icon_path = asset_dir / "buster.ico"

    # Generate multi-resolution icon sizes for Windows compatibility
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    images = []

    for size in sizes:
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw a sleek rounded dark container with a glowing accent border
        margin = max(1, size[0] // 16)
        draw.rounded_rectangle(
            [margin, margin, size[0] - margin, size[1] - margin],
            radius=size[0] // 4,
            fill=(24, 24, 28, 255),
            outline=(0, 220, 130, 255),  # Secure green accent
            width=max(1, size[0] // 32),
        )

        # Draw a stylized "B" core symbol inside
        font_box = [size[0] // 4, size[1] // 5, 3 * size[0] // 4, 4 * size[1] // 5]
        draw.text(
            (font_box[0], font_box[1] // 2),
            "B",
            fill=(255, 255, 255, 255),
        )

        images.append(img)

    # Save out as an ICO file containing multiple sizes
    images[0].save(
        icon_path,
        format="ICO",
        sizes=[img.size for img in images],
        append_images=images[1:],
    )
    print(f"[+] Application icon successfully generated at: {icon_path}")


if __name__ == "__main__":
    create_buster_icon()