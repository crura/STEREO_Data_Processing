from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageSequence

# Directory containing all GIFs to combine.
GIF_DIRECTORY = Path("/Users/crura/Desktop/Research/2026_Summer_Project/Representative_Images/B/4_per_day/Monthly_Gifs/B/median")
OUTPUT_MOVIE = GIF_DIRECTORY / "combined_year.mp4"
FPS = 5


def main() -> None:
    gif_files = sorted(
        GIF_DIRECTORY.glob("*.gif"),
        key=lambda path: path.name.lower(),
    )

    if not gif_files:
        raise FileNotFoundError(f"No GIF files found in {GIF_DIRECTORY}")

    print("Combining GIFs in this order:")
    for gif_file in gif_files:
        print(f"  {gif_file.name}")

    writer = imageio.get_writer(
        OUTPUT_MOVIE,
        fps=FPS,
        codec="libx264",
        pixelformat="yuv420p",
        macro_block_size=None,
    )

    target_size = None

    try:
        for gif_file in gif_files:
            with Image.open(gif_file) as gif:
                for frame in ImageSequence.Iterator(gif):
                    frame = frame.convert("RGB")

                    if target_size is None:
                        # H.264/yuv420p requires even image dimensions.
                        target_size = (
                            frame.width - frame.width % 2,
                            frame.height - frame.height % 2,
                        )

                    if frame.size != target_size:
                        frame = frame.resize(target_size, Image.Resampling.LANCZOS)

                    writer.append_data(np.asarray(frame))
    finally:
        writer.close()

    print(f"Movie written to: {OUTPUT_MOVIE}")


if __name__ == "__main__":
    main()