
"""Create monthly GIFs from four-per-day COR-1 representative FITS images.

Expected representative-image filenames::

    YYYYMMDD_rep_01_of_04_mean.fts
    YYYYMMDD_rep_02_of_04_mean.fts
    ...
    YYYYMMDD_rep_04_of_04_median.fts

For each channel and calendar month, this script creates one mean GIF and one
median GIF.  Every frame is rendered with SunPy Map, the Greys_r colormap,
and an independent finite-pixel 1st-99th percentile normalization. Frames
are ordered by date and then by representative number, so
one month plays as day 1 reps 1-4, day 2 reps 1-4, and so on.

By default, representative FITS files are read from::

    <input_path>/A/Representative_Images/4_per_day
    <input_path>/B/Representative_Images/4_per_day

where ``input_path`` comes from config.yaml beside this script.  GIFs are
written below each channel's Representative_Images/Monthly_GIFs directory.
"""

from __future__ import annotations

import logging
import re
import warnings
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional, Sequence

import matplotlib

# Use a non-interactive backend so the script can render GIF frames without
# opening a display window.
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import sunpy.map
import yaml
from astropy.io import fits
from astropy.io.fits.verify import VerifyWarning
from PIL import Image, ImageDraw, ImageFont

try:
    # Matplotlib 3.5+
    from matplotlib import colormaps
except ImportError:  # pragma: no cover - compatibility with older Matplotlib
    colormaps = None
    from matplotlib import cm


# -----------------------------------------------------------------------------
# User controls
# -----------------------------------------------------------------------------

# Use ("B",) when only COR-1B representative images are present.
CHANNELS = ("A", "B")

# One monthly GIF is generated for each selected combination method.
METHODS = ("mean", "median")

# None processes every month found.  Otherwise use YYYYMM strings, for example:
# MONTHS_TO_PROCESS = ("200801", "200802")
MONTHS_TO_PROCESS: Optional[tuple[str, ...]] = None

# Include all four chronological representatives from each available day.
# This can be changed to, for example, (1,) or (1, 4).
REPRESENTATIVES_TO_INCLUDE = (1, 2, 3, 4)

# Optional explicit source directories.  Leave a value as None to use:
# <input_path>/<channel>/Representative_Images/4_per_day
SOURCE_DIRECTORY_OVERRIDES: dict[str, Optional[str]] = {
    "A": None,
    "B": "/Users/crura/Desktop/Research/2026_Summer_Project/Representative_Images/B/4_per_day",
    # Example custom location:
    # "B": "/Volumes/Seagate/Chris/COR1_Representative_Images/B/4_per_day",
}

# None writes GIFs below each channel's Representative_Images directory.
# A custom root creates <GIF_OUTPUT_ROOT>/<channel>/<method>/*.gif.
GIF_OUTPUT_ROOT: Optional[str] = "/Users/crura/Desktop/Research/2026_Summer_Project/Representative_Images/B/4_per_day/Monthly_Gifs"
# Example:
# GIF_OUTPUT_ROOT = "/Volumes/Seagate/Chris/COR1_Monthly_GIFs"

# The default consolidated 4_per_day directory is flat, so recursion is not
# needed.  Set True only when representative images are in subdirectories.
# Duplicate date/representative/method files found recursively are de-duplicated.
SEARCH_RECURSIVELY = False

# Playback controls.  200 ms is 5 frames/second.  With four reps per day, a
# complete 31-day month lasts about 25 seconds before looping.
FRAME_DURATION_MS = 200
LAST_FRAME_DURATION_MS: Optional[int] = 800
GIF_LOOP = 0  # 0 means loop forever.

# Each FITS image is first rendered by Matplotlib/SunPy at this fixed canvas
# size.  It is then downsized only if it exceeds the pixel limits below.
MAP_FIGURE_WIDTH_INCHES = 8.0
MAP_FIGURE_HEIGHT_INCHES = 8.0
MAP_FIGURE_DPI = 100
SHOW_MAP_AXES = True

# Resize only when a rendered map is larger than these limits.  Aspect ratio is
# preserved.  Smaller frames are not enlarged.
MAX_FRAME_WIDTH = 768
MAX_FRAME_HEIGHT = 768

# Match the requested COR-1 plotting style.  Greys_r maps the low end of the
# normalization to dark values and the high end to white values.
COLORMAP = "Greys_r"
LOWER_PERCENTILE = 1.0
UPPER_PERCENTILE = 99.0

# "frame" applies the 1st-99th percentile normalization independently to every
# mean or median representative image, matching the supplied plotting example.
# "monthly" remains available when a fixed scale across a GIF is preferred.
SCALE_MODE = "frame"  # "monthly" or "frame"

# False gives mean and median their own monthly scales.  True uses one shared
# scale for both methods in a channel/month, making them directly comparable.
SHARE_SCALE_BETWEEN_METHODS = False

# Monthly limits are estimated from this many evenly spaced pixels per FITS
# image, avoiding the memory cost of concatenating every full-resolution image.
SAMPLES_PER_IMAGE = 20_000

SHOW_FRAME_LABELS = True
SHOW_DATE_OBS = True
SHOW_NCOMBINE = True
FONT_PATH: Optional[str] = None
FONT_SIZE = 18
LABEL_PADDING = 8

# Keep these disabled for WCS-correct SunPy rendering.  Flipping or rotating
# only the NumPy array would make the FITS WCS header inconsistent with the
# displayed pixels.
FLIP_VERTICAL = False
FLIP_HORIZONTAL = False
ROTATE_DEGREES = 0

# GIF encoding controls.
GIF_COLORS = 256
DITHER_GIF = False
OPTIMIZE_GIF = False
OVERWRITE_GIFS = True

# Continue a monthly GIF when one FITS file cannot be read or rendered.
SKIP_BAD_IMAGES = True
MEMMAP_FITS = False
SUPPRESS_FITS_VERIFY_WARNINGS = True


# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------

SCRIPT_PATH = Path(__file__).resolve()
REPO_PATH = SCRIPT_PATH.parent
CONFIG_PATH = REPO_PATH / "config.yaml"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
LOGGER = logging.getLogger(__name__)

if SUPPRESS_FITS_VERIFY_WARNINGS:
    warnings.simplefilter("ignore", VerifyWarning)


@dataclass(frozen=True)
class RepresentativeImage:
    """Metadata parsed from one representative-image filename."""

    path: Path
    date: datetime
    representative: int
    total_representatives: int
    method: str

    @property
    def month(self) -> str:
        return self.date.strftime("%Y%m")

    @property
    def key(self) -> tuple[str, int, str]:
        return (
            self.date.strftime("%Y%m%d"),
            self.representative,
            self.method,
        )


REPRESENTATIVE_PATTERN = re.compile(
    r"^(?P<date>\d{8})_rep_(?P<rep>\d{2})_of_(?P<total>\d{2})_"
    r"(?P<method>mean|median)\.(?:fts|fits)$",
    flags=re.IGNORECASE,
)


def load_input_path() -> Path:
    """Read input_path from config.yaml beside this script."""

    if not CONFIG_PATH.is_file():
        raise FileNotFoundError(
            f"Configuration file not found: {CONFIG_PATH}. "
            "Place this script beside config.yaml."
        )

    with CONFIG_PATH.open("r", encoding="utf-8") as stream:
        config = yaml.safe_load(stream)

    if not isinstance(config, dict) or not config.get("input_path"):
        raise KeyError(f"{CONFIG_PATH} must contain a non-empty input_path value")

    return Path(str(config["input_path"])).expanduser()


def validate_controls() -> None:
    """Fail early when a user control is invalid."""

    valid_channels = {"A", "B"}
    invalid_channels = set(CHANNELS) - valid_channels
    if invalid_channels:
        raise ValueError(f"Unsupported CHANNELS values: {sorted(invalid_channels)}")

    valid_methods = {"mean", "median"}
    invalid_methods = set(METHODS) - valid_methods
    if invalid_methods:
        raise ValueError(f"Unsupported METHODS values: {sorted(invalid_methods)}")

    if not REPRESENTATIVES_TO_INCLUDE:
        raise ValueError("REPRESENTATIVES_TO_INCLUDE cannot be empty")
    if any(number < 1 for number in REPRESENTATIVES_TO_INCLUDE):
        raise ValueError("Representative numbers must be positive integers")

    if MONTHS_TO_PROCESS is not None:
        invalid_months = [
            month
            for month in MONTHS_TO_PROCESS
            if re.fullmatch(r"\d{6}", month) is None
            or not 1 <= int(month[4:6]) <= 12
        ]
        if invalid_months:
            raise ValueError(
                "MONTHS_TO_PROCESS values must use YYYYMM format; invalid: "
                f"{invalid_months}"
            )

    if SCALE_MODE not in {"monthly", "frame"}:
        raise ValueError("SCALE_MODE must be 'monthly' or 'frame'")
    if not 0 <= LOWER_PERCENTILE < UPPER_PERCENTILE <= 100:
        raise ValueError(
            "Percentiles must satisfy 0 <= LOWER_PERCENTILE < "
            "UPPER_PERCENTILE <= 100"
        )
    if SAMPLES_PER_IMAGE < 1:
        raise ValueError("SAMPLES_PER_IMAGE must be at least 1")

    if FRAME_DURATION_MS < 1:
        raise ValueError("FRAME_DURATION_MS must be positive")
    if LAST_FRAME_DURATION_MS is not None and LAST_FRAME_DURATION_MS < 1:
        raise ValueError("LAST_FRAME_DURATION_MS must be positive or None")
    if MAP_FIGURE_WIDTH_INCHES <= 0 or MAP_FIGURE_HEIGHT_INCHES <= 0:
        raise ValueError("Map figure dimensions must be positive")
    if MAP_FIGURE_DPI < 1:
        raise ValueError("MAP_FIGURE_DPI must be positive")
    if MAX_FRAME_WIDTH < 1 or MAX_FRAME_HEIGHT < 1:
        raise ValueError("Maximum frame dimensions must be positive")
    if not 2 <= GIF_COLORS <= 256:
        raise ValueError("GIF_COLORS must be between 2 and 256")
    if ROTATE_DEGREES not in {0, 90, 180, 270}:
        raise ValueError("ROTATE_DEGREES must be 0, 90, 180, or 270")
    if FLIP_VERTICAL or FLIP_HORIZONTAL or ROTATE_DEGREES:
        raise ValueError(
            "FLIP_VERTICAL, FLIP_HORIZONTAL, and ROTATE_DEGREES must remain "
            "disabled when using coordinate-aware SunPy map plotting"
        )

    # Validate the colormap now rather than after many FITS files are scanned.
    get_colormap(COLORMAP)


def get_colormap(name: str):
    """Return a Matplotlib colormap across old and new Matplotlib versions."""

    if colormaps is not None:
        return colormaps.get_cmap(name)
    return cm.get_cmap(name)  # type: ignore[name-defined]


def source_directory(input_path: Path, channel: str) -> Path:
    """Return the representative FITS directory for one channel."""

    override = SOURCE_DIRECTORY_OVERRIDES.get(channel)
    if override:
        return Path(override).expanduser()

    return input_path / channel / "Representative_Images" / "4_per_day"


def output_directory(source_path: Path, channel: str, method: str) -> Path:
    """Return the output directory for one channel and combination method."""

    if GIF_OUTPUT_ROOT:
        root = Path(GIF_OUTPUT_ROOT).expanduser() / channel
    else:
        # source_path normally ends in Representative_Images/4_per_day.
        root = source_path.parent / "Monthly_GIFs"

    return root / method


def candidate_fits_files(source_path: Path) -> Iterable[Path]:
    """Yield files from the selected source directory."""

    if SEARCH_RECURSIVELY:
        yield from source_path.rglob("*")
    else:
        yield from source_path.iterdir()


def discover_representative_images(source_path: Path) -> list[RepresentativeImage]:
    """Find, parse, filter, and de-duplicate representative FITS images."""

    if not source_path.is_dir():
        LOGGER.warning("Representative-image directory not found: %s", source_path)
        return []

    selected_methods = set(METHODS)
    selected_representatives = set(REPRESENTATIVES_TO_INCLUDE)
    selected_months = set(MONTHS_TO_PROCESS) if MONTHS_TO_PROCESS else None

    by_key: dict[tuple[str, int, str], RepresentativeImage] = {}

    for path in candidate_fits_files(source_path):
        if not path.is_file():
            continue

        match = REPRESENTATIVE_PATTERN.fullmatch(path.name)
        if match is None:
            continue

        method = match.group("method").lower()
        representative = int(match.group("rep"))
        total_representatives = int(match.group("total"))

        if method not in selected_methods:
            continue
        if representative not in selected_representatives:
            continue

        try:
            date = datetime.strptime(match.group("date"), "%Y%m%d")
        except ValueError:
            LOGGER.warning("Ignoring invalid date in filename: %s", path)
            continue

        record = RepresentativeImage(
            path=path,
            date=date,
            representative=representative,
            total_representatives=total_representatives,
            method=method,
        )

        if selected_months is not None and record.month not in selected_months:
            continue

        existing = by_key.get(record.key)
        if existing is None:
            by_key[record.key] = record
            continue

        # Recursive searches can encounter a daily copy and a consolidated copy.
        # Prefer whichever path is closer to the selected source directory.
        existing_depth = len(existing.path.relative_to(source_path).parts)
        new_depth = len(path.relative_to(source_path).parts)
        if new_depth < existing_depth:
            by_key[record.key] = record
            kept, ignored = path, existing.path
        else:
            kept, ignored = existing.path, path

        LOGGER.warning(
            "Duplicate representative image for %s rep %d %s; keeping %s and "
            "ignoring %s",
            record.date.strftime("%Y-%m-%d"),
            representative,
            method,
            kept,
            ignored,
        )

    records = list(by_key.values())
    records.sort(key=lambda item: (item.date, item.representative, item.method))
    return records


def report_incomplete_days(records: Sequence[RepresentativeImage], channel: str) -> None:
    """Warn when a present day lacks one of the selected representative groups."""

    expected = set(REPRESENTATIVES_TO_INCLUDE)
    groups: dict[tuple[str, str], set[int]] = defaultdict(set)

    for record in records:
        key = (record.date.strftime("%Y%m%d"), record.method)
        groups[key].add(record.representative)

    for (day, method), found in sorted(groups.items()):
        missing = sorted(expected - found)
        if missing:
            LOGGER.warning(
                "%s %s %s is missing representative groups %s",
                channel,
                day,
                method,
                missing,
            )


def read_fits_data(path: Path) -> np.ndarray:
    """Read a primary FITS image into a writable float32 array."""

    with fits.open(path, memmap=MEMMAP_FITS) as hdul:
        if hdul[0].data is None:
            raise ValueError(f"Primary HDU contains no image data: {path}")
        data = np.array(hdul[0].data, dtype=np.float32, copy=True)

    if data.ndim != 2:
        raise ValueError(f"Expected a 2-D FITS image, found shape {data.shape}: {path}")

    return data


def read_fits_data_and_header(path: Path) -> tuple[np.ndarray, fits.Header]:
    """Read one FITS image and a copy of its primary header."""

    with fits.open(path, memmap=MEMMAP_FITS) as hdul:
        if hdul[0].data is None:
            raise ValueError(f"Primary HDU contains no image data: {path}")
        data = np.array(hdul[0].data, dtype=np.float32, copy=True)
        header = hdul[0].header.copy()

    if data.ndim != 2:
        raise ValueError(f"Expected a 2-D FITS image, found shape {data.shape}: {path}")

    return data, header


def finite_sample(data: np.ndarray, maximum_samples: int) -> np.ndarray:
    """Return a deterministic, evenly spaced sample of finite pixels."""

    flat = data.reshape(-1)
    stride = max(1, flat.size // maximum_samples)
    sample = flat[::stride][:maximum_samples]
    sample = sample[np.isfinite(sample)]
    return np.asarray(sample, dtype=np.float32)


def limits_from_samples(samples: Sequence[np.ndarray]) -> tuple[float, float]:
    """Calculate robust display limits from sampled pixels."""

    nonempty = [sample for sample in samples if sample.size]
    if not nonempty:
        raise ValueError("No finite pixels were available for intensity scaling")

    combined = np.concatenate(nonempty)
    vmin, vmax = np.percentile(
        combined,
        [LOWER_PERCENTILE, UPPER_PERCENTILE],
    )
    vmin = float(vmin)
    vmax = float(vmax)

    if not np.isfinite(vmin) or not np.isfinite(vmax):
        raise ValueError("Calculated non-finite intensity limits")

    if vmax <= vmin:
        finite_min = float(np.min(combined))
        finite_max = float(np.max(combined))
        if finite_max > finite_min:
            return finite_min, finite_max
        return finite_min, finite_min + 1.0

    return vmin, vmax


def calculate_monthly_limits(
    records: Sequence[RepresentativeImage],
) -> tuple[float, float]:
    """Estimate one robust intensity range for a set of monthly frames."""

    samples: list[np.ndarray] = []

    for record in records:
        try:
            data = read_fits_data(record.path)
            sample = finite_sample(data, SAMPLES_PER_IMAGE)
            if sample.size:
                samples.append(sample)
        except Exception:
            if not SKIP_BAD_IMAGES:
                raise
            LOGGER.exception("Could not sample %s for monthly scaling", record.path)

    return limits_from_samples(samples)


def calculate_frame_limits(data: np.ndarray) -> tuple[float, float]:
    """Calculate exact finite-pixel percentile limits for one frame."""

    finite = np.asarray(data[np.isfinite(data)], dtype=np.float32)
    if finite.size == 0:
        raise ValueError("No finite pixels were available for frame scaling")

    vmin, vmax = np.percentile(
        finite,
        [LOWER_PERCENTILE, UPPER_PERCENTILE],
    )
    vmin = float(vmin)
    vmax = float(vmax)

    if not np.isfinite(vmin) or not np.isfinite(vmax):
        raise ValueError("Calculated non-finite frame intensity limits")

    if vmax <= vmin:
        finite_min = float(np.min(finite))
        finite_max = float(np.max(finite))
        if finite_max > finite_min:
            return finite_min, finite_max
        return finite_min, finite_min + 1.0

    return vmin, vmax


def orient_data(data: np.ndarray) -> np.ndarray:
    """Apply the configured flips and right-angle rotation."""

    oriented = data
    if FLIP_VERTICAL:
        oriented = np.flipud(oriented)
    if FLIP_HORIZONTAL:
        oriented = np.fliplr(oriented)
    if ROTATE_DEGREES:
        oriented = np.rot90(oriented, k=ROTATE_DEGREES // 90)
    return oriented


def render_sunpy_map(
    data: np.ndarray,
    header: fits.Header,
    vmin: float,
    vmax: float,
) -> Image.Image:
    """Render one FITS image through SunPy Map and return an RGB image."""

    if vmax <= vmin:
        raise ValueError(f"Invalid intensity limits: vmin={vmin}, vmax={vmax}")

    cor1map = sunpy.map.Map(data, header)
    cor1map.plot_settings["cmap"] = get_colormap(COLORMAP)
    cor1map.plot_settings["norm"] = matplotlib.colors.Normalize(
        vmin=vmin,
        vmax=vmax,
    )

    figure = plt.figure(
        figsize=(MAP_FIGURE_WIDTH_INCHES, MAP_FIGURE_HEIGHT_INCHES),
        dpi=MAP_FIGURE_DPI,
        facecolor="white",
    )

    try:
        axes = figure.add_subplot(111, projection=cor1map)
        axes.set_facecolor("white")

        # This is the same plotting path as:
        # cor1map.plot_settings['cmap'] = matplotlib.colormaps['Greys_r']
        # cor1map.plot_settings['norm'] = plt.Normalize(vmin=..., vmax=...)
        # cor1map.plot(axes=axes, title=False)
        cor1map.plot(axes=axes, title=False)

        if SHOW_MAP_AXES:
            # Fixed margins keep every GIF frame the same pixel dimensions.
            figure.subplots_adjust(left=0.14, right=0.97, bottom=0.12, top=0.97)
        else:
            axes.set_axis_off()
            figure.subplots_adjust(left=0.0, right=1.0, bottom=0.0, top=1.0)

        figure.canvas.draw()
        rgba = np.asarray(figure.canvas.buffer_rgba(), dtype=np.uint8)
        rgb = np.array(rgba[..., :3], dtype=np.uint8, copy=True)
        return Image.fromarray(rgb, mode="RGB")
    finally:
        plt.close(figure)


def resize_image(image: Image.Image) -> Image.Image:
    """Downsize an image to the configured bounding box without enlarging it."""

    width, height = image.size
    scale = min(
        1.0,
        MAX_FRAME_WIDTH / width,
        MAX_FRAME_HEIGHT / height,
    )

    if scale >= 1.0:
        return image

    new_size = (
        max(1, int(round(width * scale))),
        max(1, int(round(height * scale))),
    )
    resampling = getattr(Image, "Resampling", Image).LANCZOS
    resized = image.resize(new_size, resample=resampling)
    image.close()
    return resized


def load_font() -> ImageFont.ImageFont:
    """Load a readable TrueType font, falling back to Pillow's default font."""

    candidates = []
    if FONT_PATH:
        candidates.append(FONT_PATH)
    candidates.append("DejaVuSans.ttf")

    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, FONT_SIZE)
        except OSError:
            continue

    LOGGER.warning(
        "Could not load FONT_PATH or DejaVuSans.ttf; using Pillow's default font"
    )
    return ImageFont.load_default()


FONT = load_font()


def frame_label(
    record: RepresentativeImage,
    header: fits.Header,
    channel: str,
) -> str:
    """Build the annotation displayed above one GIF frame."""

    first_line = (
        f"COR-1{channel} | {record.date.strftime('%Y-%m-%d')} | "
        f"representative {record.representative}/{record.total_representatives} | "
        f"{record.method}"
    )

    details: list[str] = []
    if SHOW_DATE_OBS and header.get("DATE-OBS") is not None:
        details.append(f"DATE-OBS {str(header['DATE-OBS']).strip()}")
    if SHOW_NCOMBINE and header.get("NCOMBINE") is not None:
        details.append(f"NCOMBINE {header['NCOMBINE']}")

    if details:
        return first_line + "\n" + " | ".join(details)
    return first_line


def add_label_bar(image: Image.Image, label: str) -> Image.Image:
    """Add a black title bar without covering scientific image pixels."""

    if not SHOW_FRAME_LABELS:
        return image

    scratch = Image.new("RGB", (1, 1))
    scratch_draw = ImageDraw.Draw(scratch)
    try:
        bounds = scratch_draw.multiline_textbbox(
            (0, 0),
            label,
            font=FONT,
            spacing=3,
        )
        text_width = bounds[2] - bounds[0]
        text_height = bounds[3] - bounds[1]
    except AttributeError:  # pragma: no cover - old Pillow compatibility
        text_width, text_height = scratch_draw.multiline_textsize(
            label,
            font=FONT,
            spacing=3,
        )
    scratch.close()

    # The bar cannot be narrower than the image.  A very long custom label is
    # allowed to widen the canvas rather than being silently clipped.
    canvas_width = max(image.width, text_width + 2 * LABEL_PADDING)
    bar_height = text_height + 2 * LABEL_PADDING
    canvas = Image.new("RGB", (canvas_width, image.height + bar_height), (0, 0, 0))

    image_x = (canvas_width - image.width) // 2
    canvas.paste(image, (image_x, bar_height))
    image.close()

    draw = ImageDraw.Draw(canvas)
    draw.multiline_text(
        (LABEL_PADDING, LABEL_PADDING),
        label,
        fill=(255, 255, 255),
        font=FONT,
        spacing=3,
    )
    return canvas


def convert_for_gif(image: Image.Image) -> Image.Image:
    """Convert an RGB frame to an indexed palette suitable for GIF."""

    if hasattr(Image, "Palette"):
        adaptive_palette = Image.Palette.ADAPTIVE
    else:  # pragma: no cover - old Pillow compatibility
        adaptive_palette = Image.ADAPTIVE

    if DITHER_GIF:
        dither = getattr(getattr(Image, "Dither", Image), "FLOYDSTEINBERG")
    else:
        dither = getattr(getattr(Image, "Dither", Image), "NONE")

    converted = image.convert(
        "P",
        palette=adaptive_palette,
        colors=GIF_COLORS,
        dither=dither,
    )
    image.close()
    return converted


def render_frame(
    record: RepresentativeImage,
    channel: str,
    monthly_limits: Optional[tuple[float, float]],
) -> Image.Image:
    """Render one representative FITS file as an indexed GIF frame."""

    data, header = read_fits_data_and_header(record.path)

    if monthly_limits is None:
        # Exact per-frame 1st and 99th percentiles, as requested.
        vmin, vmax = calculate_frame_limits(data)
    else:
        vmin, vmax = monthly_limits

    image = render_sunpy_map(data, header, vmin, vmax)
    image = resize_image(image)
    image = add_label_bar(image, frame_label(record, header, channel))
    return convert_for_gif(image)


def save_monthly_gif(
    records: Sequence[RepresentativeImage],
    channel: str,
    month: str,
    method: str,
    monthly_limits: Optional[tuple[float, float]],
    destination: Path,
) -> bool:
    """Render and save one channel/month/method GIF."""

    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists() and not OVERWRITE_GIFS:
        LOGGER.info("Skipping existing GIF: %s", destination)
        return False

    frames: list[Image.Image] = []
    LOGGER.info(
        "Rendering COR-1%s %s %s: %d candidate frames",
        channel,
        month,
        method,
        len(records),
    )

    try:
        for index, record in enumerate(records, start=1):
            try:
                frames.append(render_frame(record, channel, monthly_limits))
            except Exception:
                if not SKIP_BAD_IMAGES:
                    raise
                LOGGER.exception("Skipping unreadable GIF frame: %s", record.path)

            if index == 1 or index % 25 == 0 or index == len(records):
                LOGGER.info(
                    "COR-1%s %s %s: rendered %d/%d",
                    channel,
                    month,
                    method,
                    index,
                    len(records),
                )

        if not frames:
            LOGGER.warning(
                "No valid frames remained for COR-1%s %s %s",
                channel,
                month,
                method,
            )
            return False

        durations = [FRAME_DURATION_MS] * len(frames)
        if LAST_FRAME_DURATION_MS is not None:
            durations[-1] = LAST_FRAME_DURATION_MS

        temporary = destination.with_name(destination.stem + ".tmp.gif")
        frames[0].save(
            temporary,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=GIF_LOOP,
            optimize=OPTIMIZE_GIF,
            disposal=2,
            comment=(
                f"COR-1{channel} {month} {method}; "
                f"{len(frames)} representative-image frames"
            ).encode("ascii"),
        )
        temporary.replace(destination)

        size_mb = destination.stat().st_size / (1024 * 1024)
        LOGGER.info(
            "Wrote %s with %d frames (%.1f MB)",
            destination,
            len(frames),
            size_mb,
        )
        return True

    finally:
        for frame in frames:
            frame.close()


def group_records(
    records: Sequence[RepresentativeImage],
) -> dict[str, dict[str, list[RepresentativeImage]]]:
    """Group records as month -> method -> chronologically sorted images."""

    grouped: dict[str, dict[str, list[RepresentativeImage]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for record in records:
        grouped[record.month][record.method].append(record)

    for method_groups in grouped.values():
        for method_records in method_groups.values():
            method_records.sort(key=lambda item: (item.date, item.representative))

    return grouped


def process_channel(input_path: Path, channel: str) -> int:
    """Create every selected monthly GIF for one COR-1 channel."""

    source_path = source_directory(input_path, channel)
    records = discover_representative_images(source_path)
    if not records:
        LOGGER.warning("No matching representative FITS files found in %s", source_path)
        return 0

    report_incomplete_days(records, channel)
    grouped = group_records(records)
    gifs_written = 0

    for month in sorted(grouped):
        method_groups = grouped[month]

        shared_limits: Optional[tuple[float, float]] = None
        if SCALE_MODE == "monthly" and SHARE_SCALE_BETWEEN_METHODS:
            shared_records = [
                record
                for method in METHODS
                for record in method_groups.get(method, [])
            ]
            if shared_records:
                shared_limits = calculate_monthly_limits(shared_records)
                LOGGER.info(
                    "COR-1%s %s shared mean/median limits: %.6g to %.6g",
                    channel,
                    month,
                    shared_limits[0],
                    shared_limits[1],
                )

        for method in METHODS:
            method_records = method_groups.get(method, [])
            if not method_records:
                LOGGER.warning(
                    "No COR-1%s %s representative images for %s",
                    channel,
                    method,
                    month,
                )
                continue

            if SCALE_MODE == "frame":
                limits = None
            elif shared_limits is not None:
                limits = shared_limits
            else:
                limits = calculate_monthly_limits(method_records)
                LOGGER.info(
                    "COR-1%s %s %s limits: %.6g to %.6g",
                    channel,
                    month,
                    method,
                    limits[0],
                    limits[1],
                )

            destination = (
                output_directory(source_path, channel, method)
                / f"COR1_{channel}_{month}_{method}.gif"
            )

            if save_monthly_gif(
                records=method_records,
                channel=channel,
                month=month,
                method=method,
                monthly_limits=limits,
                destination=destination,
            ):
                gifs_written += 1

    return gifs_written


def main() -> None:
    """Program entry point."""

    validate_controls()
    input_path = load_input_path()

    total_written = 0
    for channel in CHANNELS:
        total_written += process_channel(input_path, channel)

    LOGGER.info("Finished; wrote %d monthly GIF files", total_written)


if __name__ == "__main__":
    main()