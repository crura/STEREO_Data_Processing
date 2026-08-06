from pathlib import Path
import os
image_directory = Path("/Users/crura/Desktop/Research/2026_Summer_Project/Representative_Images/B/4_per_day")
constraint_directory = Path("/Users/crura/Desktop/Research/2026_Summer_Project/2008_QRaFT_Features/FITS")
output_path = "/Users/crura/Desktop/Research/2026_Summer_Project/Representative_Images/B/overlayed_4_per_day"
VALID_FILE_SUFFIXES = (
    ".fts",
    ".fits",
)
qraft_suffix = ".sav.fits"

def find_files_from_suffix(input_directory: str | Path, suffix: str) -> list[Path]:
    """Return files directly inside one directory based on suffix."""

    input_directory = Path(input_directory)

    return sorted(
        path
        for path in input_directory.iterdir()
        if path.is_file()
        and path.name.lower().endswith(suffix)
    )

imagefiles = find_files_from_suffix(image_directory, "median.fts")
qraftfiles = find_files_from_suffix(constraint_directory, ".fits")

def produce_overlay_images(imagefiles, qraftfiles):
    for i in range(len(imagefiles)-1):
        image_file = imagefiles[i]
        constraint_file = qraftfiles[i]
        image = fits.getdata(image_file).astype(float)
        angles = fits.getdata(constraint_file).astype(float)

        valid = np.isfinite(angles) & (angles != 0)
        angle_overlay = np.where(valid, np.mod(angles, 2 * np.pi), np.nan)
        
        positive = image[np.isfinite(image) & (image > 0)]
        vmin, vmax = np.percentile(positive, [1, 99.9])
        
        fig, ax = plt.subplots(figsize=(9, 9))
        
        ax.imshow(
            image,
            origin="lower",
            cmap="gray",
            norm=LogNorm(vmin=vmin, vmax=vmax),
        )
        
        overlay = ax.imshow(
            angle_overlay,
            origin="lower",
            cmap="twilight",
            vmin=0,
            vmax=2 * np.pi,
        )
        
        fig.colorbar(
            overlay,
            ax=ax,
            label="QRaFT orientation angle (radians)",
        )
        
        ax.set_xlabel("X (pixel)")
        ax.set_ylabel("Y (pixel)")
        ax.set_title("COR1 image with QRaFT constraints")
        
        fig.tight_layout()
        plt.savefig(os.path.join(output_path, image_file.stem + "_qraft_overlayed.png"))
        plt.close

# produce_overlay_images(imagefiles, qraftfiles)

png_files = find_files_from_suffix("/Users/crura/Desktop/Research/2026_Summer_Project/Representative_Images/B/overlayed_4_per_day", ".png")

GIF_FILE = output_path + "qraft_orientations.gif"

# Combine the PNG files into an animated GIF.
frames = [
    Image.open(path).convert("RGB")
    for path in png_files
]

frames[0].save(
    GIF_FILE,
    save_all=True,
    append_images=frames[1:],
    duration=FRAME_DURATION_MS,
    loop=0,
)

for frame in frames:
    frame.close()


print(f"Saved {len(png_files)} PNG frames")
print(f"Saved GIF: {GIF_FILE}")
# for i in range(len(png_files)-1):