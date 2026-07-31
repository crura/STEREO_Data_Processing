"""Combine monthly COR-1 GIFs into full-year H.264 MP4 movies.

This script is designed to consume the monthly GIFs produced by
``COR1_monthly_representative_gifs_sunpy.py``.  The expected default layout is::

    <input_path>/<channel>/Representative_Images/Monthly_GIFs/mean/
        COR1_<channel>_<YYYYMM>_mean.gif

    <input_path>/<channel>/Representative_Images/Monthly_GIFs/median/
        COR1_<channel>_<YYYYMM>_median.gif

By default, one side-by-side annual movie is written for each channel/year,
with mean frames on the left and median frames on the right.  The monthly GIFs
are processed from January through December, and their internal frame order is
preserved.

The output is an H.264 MP4 with a broadly compatible yuv420p pixel format.
No representative FITS files are reopened or re-rendered.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterator, Optional, Sequence

import imageio.v2 as imageio
import numpy as np
import yaml
from PIL import Image


# -----------------------------------------------------------------------------
# User controls
# -----------------------------------------------------------------------------

# The current data set contains COR-1B products.  Change to ("A", "B") when
# monthly GIFs exist for both channels.
CHANNELS = ("B",)

# None discovers every year represented by the monthly GIF filenames.
# Example: YEARS_TO_PROCESS = (2008,)
YEARS_TO_PROCESS: Optional[tuple[int, ...]] = None

# None includes every available month.  Otherwise use integers 1 through 12.
# Example: MONTHS_TO_PROCESS = (1, 2, 3, 4, 5, 6)
MONTHS_TO_PROCESS: Optional[tuple[int, ...]] = None

# Output choices:
#   "side_by_side" -> one movie: mean left, median right
#   "separate"     -> one full-year mean movie and one full-year median movie
#   "both"         -> create the comparison movie and both separate movies
OUTPUT_MODE = "side_by_side"

# Methods used for separate output.  The side-by-side output always compares
# mean and median in that order.
METHODS = ("mean", "median")
COMPARISON_METHODS = ("mean", "median")

# Optional per-channel override.  Each path must point to the Monthly_GIFs
# directory that contains the mean/ and median/ subdirectories.
MONTHLY_GIF_DIRECTORY_OVERRIDES: dict[str, Optional[str]] = {
    "A": None,
    "B": None,
    # Example:
    # "B": "/Volumes/Seagate/Chris/COR1_Monthly_GIFs/B",
}

# None writes below:
# <input_path>/<channel>/Representative_Images/Yearly_Movies
#
# A custom root writes below:
# <MOVIE_OUTPUT_ROOT>/<channel>
MOVIE_OUTPUT_ROOT: Optional[str] = None
# Example:
# MOVIE_OUTPUT_ROOT = "/Volumes/Seagate/Chris/COR1_Yearly_Movies"

# Preserve each GIF frame's duration.  With the monthly GIF defaults, normal
# frames are 200 ms and the final frame of each month is held for 800 ms.
# Set False to show every source frame exactly once at VIDEO_FPS.
PRESERVE_GIF_TIMING = True
DEFAULT_GIF_FRAME_DURATION_MS = 200
MAX_GIF_FRAME_DURATION_MS = 5_000

# The monthly GIF script used 200 ms per ordinary frame, so 5 fps reproduces
# that cadence exactly.  An 800 ms month-end frame becomes four video frames.
VIDEO_FPS = 5.0

# H.264 encoding controls.  Smaller CRF values increase quality and file size.
VIDEO_CODEC = "libx264"
VIDEO_PIXEL_FORMAT = "yuv420p"
VIDEO_CRF = 18
VIDEO_PRESET = "medium"
FFMPEG_LOG_LEVEL = "warning"

# Side-by-side layout.  Frames are centered without changing their scale.
SIDE_BY_SIDE_GAP_PX = 8
BACKGROUND_RGB = (0, 0, 0)

# Input validation and error behavior.
REQUIRE_ALL_12_MONTHS = False
REQUIRE_MATCHING_COMPARISON_MONTHS = True
REQUIRE_MATCHING_COMPARISON_FRAME_COUNTS = True
SKIP_BAD_GIFS = False
OVERWRITE_MOVIES = True


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

MONTHLY_GIF_PATTERN = re.compile(
    r"^COR1_(?P<channel>[AB])_(?P<month>\d{6})_"
    r"(?P<method>mean|median)\.gif$",
    flags=re.IGNORECASE,
)


# -----------------------------------------------------------------------------
# Paths and discovery
# -----------------------------------------------------------------------------


def load_input_path() -> Path:
    """Read ``input_path`` from config.yaml beside this script."""

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
    """Validate user-editable controls before opening any GIFs."""

    invalid_channels = set(CHANNELS) - {"A", "B"}
    if invalid_channels:
        raise ValueError(f"Unsupported CHANNELS values: {sorted(invalid_channels)}")

    if OUTPUT_MODE not in {"side_by_side", "separate", "both"}:
        raise ValueError(
            "OUTPUT_MODE must be 'side_by_side', 'separate', or 'both'"
        )

    invalid_methods = set(METHODS) - {"mean", "median"}
    if invalid_methods:
        raise ValueError(f"Unsupported METHODS values: {sorted(invalid_methods)}")

    if tuple(COMPARISON_METHODS) != ("mean", "median"):
        raise ValueError(
            "COMPARISON_METHODS must remain ('mean', 'median') so the "
            "comparison layout and filenames are unambiguous"
        )

    if YEARS_TO_PROCESS is not None:
        if not YEARS_TO_PROCESS or any(year < 1 for year in YEARS_TO_PROCESS):
            raise ValueError("YEARS_TO_PROCESS must contain positive years or be None")

    if MONTHS_TO_PROCESS is not None:
        if not MONTHS_TO_PROCESS or any(
            month < 1 or month > 12 for month in MONTHS_TO_PROCESS
        ):
            raise ValueError(
                "MONTHS_TO_PROCESS must contain month numbers 1 through 12 or be None"
            )

    if VIDEO_FPS <= 0:
        raise ValueError("VIDEO_FPS must be positive")
    if DEFAULT_GIF_FRAME_DURATION_MS <= 0:
        raise ValueError("DEFAULT_GIF_FRAME_DURATION_MS must be positive")
    if MAX_GIF_FRAME_DURATION_MS <= 0:
        raise ValueError("MAX_GIF_FRAME_DURATION_MS must be positive")
    if not 0 <= VIDEO_CRF <= 51:
        raise ValueError("VIDEO_CRF must be between 0 and 51")
    if SIDE_BY_SIDE_GAP_PX < 0:
        raise ValueError("SIDE_BY_SIDE_GAP_PX cannot be negative")
    if len(BACKGROUND_RGB) != 3 or any(
        component < 0 or component > 255 for component in BACKGROUND_RGB
    ):
        raise ValueError("BACKGROUND_RGB must contain three values from 0 to 255")


def monthly_gif_root(input_path: Path, channel: str) -> Path:
    """Return the channel-level Monthly_GIFs directory."""

    override = MONTHLY_GIF_DIRECTORY_OVERRIDES.get(channel)
    if override:
        return Path(override).expanduser()

    return input_path / channel / "Representative_Images" / "Monthly_GIFs"


def movie_output_directory(input_path: Path, channel: str) -> Path:
    """Return the output directory for annual MP4 files."""

    if MOVIE_OUTPUT_ROOT:
        return Path(MOVIE_OUTPUT_ROOT).expanduser() / channel

    return input_path / channel / "Representative_Images" / "Yearly_Movies"


def discover_monthly_gifs(
    root: Path,
    channel: str,
    method: str,
) -> dict[int, dict[int, Path]]:
    """Return monthly GIFs grouped as ``year -> month -> path``."""

    method_directory = root / method
    if not method_directory.is_dir():
        LOGGER.warning("Monthly GIF directory not found: %s", method_directory)
        return {}

    selected_years = set(YEARS_TO_PROCESS) if YEARS_TO_PROCESS else None
    selected_months = set(MONTHS_TO_PROCESS) if MONTHS_TO_PROCESS else None
    grouped: dict[int, dict[int, Path]] = defaultdict(dict)

    for path in sorted(method_directory.glob("*.gif")):
        match = MONTHLY_GIF_PATTERN.fullmatch(path.name)
        if match is None:
            continue

        file_channel = match.group("channel").upper()
        file_method = match.group("method").lower()
        if file_channel != channel or file_method != method:
            continue

        year_month = match.group("month")
        year = int(year_month[:4])
        month = int(year_month[4:6])
        if not 1 <= month <= 12:
            LOGGER.warning("Ignoring invalid month in filename: %s", path)
            continue
        if selected_years is not None and year not in selected_years:
            continue
        if selected_months is not None and month not in selected_months:
            continue

        existing = grouped[year].get(month)
        if existing is not None:
            raise ValueError(
                f"Duplicate COR-1{channel} {year_month} {method} GIFs: "
                f"{existing} and {path}"
            )
        grouped[year][month] = path

    return {year: dict(months) for year, months in grouped.items()}


def report_missing_months(
    channel: str,
    year: int,
    method: str,
    months: Sequence[int],
) -> None:
    """Report absent calendar months and optionally fail."""

    expected = set(MONTHS_TO_PROCESS or tuple(range(1, 13)))
    missing = sorted(expected - set(months))
    if not missing:
        return

    message = (
        f"COR-1{channel} {year} {method} is missing monthly GIFs for "
        f"months {missing}"
    )
    if REQUIRE_ALL_12_MONTHS:
        raise FileNotFoundError(message)
    LOGGER.warning(message)


# -----------------------------------------------------------------------------
# GIF frame handling
# -----------------------------------------------------------------------------


def open_gif(path: Path) -> Image.Image:
    """Open one GIF and verify that it contains at least one frame."""

    image = Image.open(path)
    frame_count = int(getattr(image, "n_frames", 1))
    if frame_count < 1:
        image.close()
        raise ValueError(f"GIF contains no frames: {path}")
    return image


def gif_canvas_size(path: Path) -> tuple[int, int]:
    """Return the fixed canvas size of one GIF."""

    with open_gif(path) as image:
        return image.size


def maximum_canvas_size(paths: Sequence[Path]) -> tuple[int, int]:
    """Return the largest width and height among a set of GIFs."""

    widths: list[int] = []
    heights: list[int] = []

    for path in paths:
        try:
            width, height = gif_canvas_size(path)
        except Exception:
            if not SKIP_BAD_GIFS:
                raise
            LOGGER.exception("Skipping unreadable GIF while checking size: %s", path)
            continue
        widths.append(width)
        heights.append(height)

    if not widths:
        raise ValueError("No readable GIFs were available to determine frame size")

    return max(widths), max(heights)


def make_even(value: int) -> int:
    """Return an even integer suitable for yuv420p video encoding."""

    return value if value % 2 == 0 else value + 1


def even_size(size: tuple[int, int]) -> tuple[int, int]:
    """Make both dimensions even for H.264/yuv420p compatibility."""

    return make_even(size[0]), make_even(size[1])


def current_frame_duration_ms(gif: Image.Image) -> int:
    """Read and sanitize the duration of the GIF's current frame."""

    raw_duration = gif.info.get("duration", DEFAULT_GIF_FRAME_DURATION_MS)
    try:
        duration = int(raw_duration)
    except (TypeError, ValueError):
        duration = DEFAULT_GIF_FRAME_DURATION_MS

    if duration <= 0:
        duration = DEFAULT_GIF_FRAME_DURATION_MS

    if duration > MAX_GIF_FRAME_DURATION_MS:
        LOGGER.warning(
            "Capping unusually long GIF frame duration from %d ms to %d ms",
            duration,
            MAX_GIF_FRAME_DURATION_MS,
        )
        duration = MAX_GIF_FRAME_DURATION_MS

    return duration


def frame_repetitions(duration_ms: int) -> int:
    """Convert a GIF frame duration to a whole number of video frames."""

    if not PRESERVE_GIF_TIMING:
        return 1

    repetitions = int(round(duration_ms * VIDEO_FPS / 1000.0))
    return max(1, repetitions)


def read_current_gif_frame(gif: Image.Image) -> Image.Image:
    """Return the current GIF frame as an independent RGB image."""

    # Pillow applies GIF palette, transparency, and disposal information while
    # seeking.  The copy detaches this frame from the open GIF file.
    return gif.convert("RGB").copy()


def center_frame_on_canvas(
    frame: Image.Image,
    canvas_size: tuple[int, int],
) -> Image.Image:
    """Center one RGB frame on a fixed-size background without rescaling it."""

    canvas_width, canvas_height = canvas_size
    if frame.width > canvas_width or frame.height > canvas_height:
        raise ValueError(
            f"Frame size {frame.size} exceeds target canvas {canvas_size}"
        )

    canvas = Image.new("RGB", canvas_size, BACKGROUND_RGB)
    x = (canvas_width - frame.width) // 2
    y = (canvas_height - frame.height) // 2
    canvas.paste(frame, (x, y))
    frame.close()
    return canvas


def build_comparison_frame(
    mean_frame: Image.Image,
    median_frame: Image.Image,
    panel_size: tuple[int, int],
    output_size: tuple[int, int],
) -> Image.Image:
    """Place mean and median frames side by side on one fixed video canvas."""

    panel_width, panel_height = panel_size
    output_width, output_height = output_size

    if mean_frame.width > panel_width or mean_frame.height > panel_height:
        raise ValueError(
            f"Mean frame size {mean_frame.size} exceeds panel size {panel_size}"
        )
    if median_frame.width > panel_width or median_frame.height > panel_height:
        raise ValueError(
            f"Median frame size {median_frame.size} exceeds panel size {panel_size}"
        )

    canvas = Image.new("RGB", output_size, BACKGROUND_RGB)

    mean_x = (panel_width - mean_frame.width) // 2
    mean_y = (panel_height - mean_frame.height) // 2

    right_panel_x = panel_width + SIDE_BY_SIDE_GAP_PX
    median_x = right_panel_x + (panel_width - median_frame.width) // 2
    median_y = (panel_height - median_frame.height) // 2

    # Any extra pixel added to make the final dimensions even remains as a thin
    # black border along the right or bottom edge.
    if mean_x + mean_frame.width > output_width:
        raise ValueError("Mean frame placement exceeds output width")
    if median_x + median_frame.width > output_width:
        raise ValueError("Median frame placement exceeds output width")
    if max(mean_y + mean_frame.height, median_y + median_frame.height) > output_height:
        raise ValueError("Frame placement exceeds output height")

    canvas.paste(mean_frame, (mean_x, mean_y))
    canvas.paste(median_frame, (median_x, median_y))
    mean_frame.close()
    median_frame.close()
    return canvas


def append_repeated_frame(
    writer,
    frame: Image.Image,
    repetitions: int,
) -> int:
    """Append one RGB frame to the video writer one or more times."""

    array = np.asarray(frame, dtype=np.uint8)
    if array.ndim != 3 or array.shape[2] != 3:
        raise ValueError(f"Expected an RGB frame, found array shape {array.shape}")

    for _ in range(repetitions):
        writer.append_data(array)

    frame.close()
    return repetitions


# -----------------------------------------------------------------------------
# Video encoding
# -----------------------------------------------------------------------------


def create_video_writer(path: Path):
    """Create an ImageIO/FFmpeg H.264 writer."""

    return imageio.get_writer(
        str(path),
        format="FFMPEG",
        mode="I",
        fps=VIDEO_FPS,
        codec=VIDEO_CODEC,
        pixelformat=VIDEO_PIXEL_FORMAT,
        macro_block_size=None,
        quality=None,
        ffmpeg_log_level=FFMPEG_LOG_LEVEL,
        output_params=[
            "-crf",
            str(VIDEO_CRF),
            "-preset",
            VIDEO_PRESET,
            "-movflags",
            "+faststart",
        ],
    )


def temporary_movie_path(destination: Path) -> Path:
    """Return a temporary MP4 path that FFmpeg can infer correctly."""

    return destination.with_name(f"{destination.stem}.tmp{destination.suffix}")


def prepare_destination(destination: Path) -> Optional[Path]:
    """Create parent directories and return a temporary output path."""

    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists() and not OVERWRITE_MOVIES:
        LOGGER.info("Skipping existing movie: %s", destination)
        return None

    temporary = temporary_movie_path(destination)
    if temporary.exists():
        temporary.unlink()
    return temporary


def finish_movie(
    temporary: Path,
    destination: Path,
    encoded_frames: int,
) -> None:
    """Atomically move a completed temporary MP4 into place and report it."""

    if encoded_frames < 1:
        if temporary.exists():
            temporary.unlink()
        raise ValueError(f"No video frames were written for {destination}")

    temporary.replace(destination)
    duration_seconds = encoded_frames / VIDEO_FPS
    size_mb = destination.stat().st_size / (1024 * 1024)
    LOGGER.info(
        "Wrote %s: %d encoded frames, %.1f seconds, %.1f MB",
        destination,
        encoded_frames,
        duration_seconds,
        size_mb,
    )


def create_separate_year_movie(
    channel: str,
    year: int,
    method: str,
    monthly_paths: dict[int, Path],
    destination: Path,
) -> bool:
    """Concatenate one method's monthly GIFs into a full-year MP4."""

    if not monthly_paths:
        LOGGER.warning("No COR-1%s %d %s monthly GIFs found", channel, year, method)
        return False

    ordered_months = sorted(monthly_paths)
    report_missing_months(channel, year, method, ordered_months)
    ordered_paths = [monthly_paths[month] for month in ordered_months]

    canvas_size = even_size(maximum_canvas_size(ordered_paths))
    temporary = prepare_destination(destination)
    if temporary is None:
        return False

    LOGGER.info(
        "Creating COR-1%s %d %s movie from months %s at canvas %s",
        channel,
        year,
        method,
        ordered_months,
        canvas_size,
    )

    writer = None
    encoded_frames = 0
    source_frames = 0

    try:
        writer = create_video_writer(temporary)

        for month in ordered_months:
            path = monthly_paths[month]
            LOGGER.info("Adding %s", path)

            try:
                with open_gif(path) as gif:
                    frame_count = int(getattr(gif, "n_frames", 1))
                    for frame_index in range(frame_count):
                        gif.seek(frame_index)
                        duration_ms = current_frame_duration_ms(gif)
                        frame = read_current_gif_frame(gif)
                        frame = center_frame_on_canvas(frame, canvas_size)
                        repetitions = frame_repetitions(duration_ms)
                        encoded_frames += append_repeated_frame(
                            writer,
                            frame,
                            repetitions,
                        )
                        source_frames += 1
            except Exception:
                if not SKIP_BAD_GIFS:
                    raise
                LOGGER.exception("Skipping unreadable monthly GIF: %s", path)

        writer.close()
        writer = None
        finish_movie(temporary, destination, encoded_frames)
        LOGGER.info(
            "COR-1%s %d %s used %d source GIF frames",
            channel,
            year,
            method,
            source_frames,
        )
        return True

    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise
    finally:
        if writer is not None:
            writer.close()


def comparison_months(
    channel: str,
    year: int,
    mean_paths: dict[int, Path],
    median_paths: dict[int, Path],
) -> list[int]:
    """Return months that can be paired in the mean/median comparison."""

    mean_months = set(mean_paths)
    median_months = set(median_paths)

    missing_mean = sorted(median_months - mean_months)
    missing_median = sorted(mean_months - median_months)
    if missing_mean or missing_median:
        message = (
            f"COR-1{channel} {year} comparison has unmatched monthly GIFs; "
            f"missing mean months={missing_mean}, "
            f"missing median months={missing_median}"
        )
        if REQUIRE_MATCHING_COMPARISON_MONTHS:
            raise FileNotFoundError(message)
        LOGGER.warning(message)

    months = sorted(mean_months & median_months)
    if not months:
        raise FileNotFoundError(
            f"No paired mean/median GIF months found for COR-1{channel} {year}"
        )

    report_missing_months(channel, year, "mean/median comparison", months)
    return months


def create_comparison_year_movie(
    channel: str,
    year: int,
    mean_paths: dict[int, Path],
    median_paths: dict[int, Path],
    destination: Path,
) -> bool:
    """Create one annual side-by-side mean-versus-median MP4."""

    months = comparison_months(channel, year, mean_paths, median_paths)
    all_paths = [mean_paths[month] for month in months] + [
        median_paths[month] for month in months
    ]

    panel_size = maximum_canvas_size(all_paths)
    combined_size = even_size(
        (
            panel_size[0] * 2 + SIDE_BY_SIDE_GAP_PX,
            panel_size[1],
        )
    )

    temporary = prepare_destination(destination)
    if temporary is None:
        return False

    LOGGER.info(
        "Creating COR-1%s %d mean-vs-median movie from months %s; "
        "panel=%s output=%s",
        channel,
        year,
        months,
        panel_size,
        combined_size,
    )

    writer = None
    encoded_frames = 0
    paired_source_frames = 0

    try:
        writer = create_video_writer(temporary)

        for month in months:
            mean_path = mean_paths[month]
            median_path = median_paths[month]
            LOGGER.info("Pairing %s with %s", mean_path, median_path)

            try:
                with open_gif(mean_path) as mean_gif, open_gif(median_path) as median_gif:
                    mean_count = int(getattr(mean_gif, "n_frames", 1))
                    median_count = int(getattr(median_gif, "n_frames", 1))

                    if mean_count != median_count:
                        message = (
                            f"Frame-count mismatch for COR-1{channel} {year}{month:02d}: "
                            f"mean={mean_count}, median={median_count}"
                        )
                        if REQUIRE_MATCHING_COMPARISON_FRAME_COUNTS:
                            raise ValueError(message)
                        LOGGER.warning("%s; using the first %d paired frames", message, min(mean_count, median_count))

                    pair_count = min(mean_count, median_count)
                    for frame_index in range(pair_count):
                        mean_gif.seek(frame_index)
                        median_gif.seek(frame_index)

                        mean_duration = current_frame_duration_ms(mean_gif)
                        median_duration = current_frame_duration_ms(median_gif)
                        if mean_duration != median_duration:
                            LOGGER.warning(
                                "Duration mismatch in COR-1%s %d%02d frame %d: "
                                "mean=%d ms, median=%d ms; using the longer duration",
                                channel,
                                year,
                                month,
                                frame_index,
                                mean_duration,
                                median_duration,
                            )

                        mean_frame = read_current_gif_frame(mean_gif)
                        median_frame = read_current_gif_frame(median_gif)
                        comparison = build_comparison_frame(
                            mean_frame,
                            median_frame,
                            panel_size,
                            combined_size,
                        )

                        duration_ms = max(mean_duration, median_duration)
                        repetitions = frame_repetitions(duration_ms)
                        encoded_frames += append_repeated_frame(
                            writer,
                            comparison,
                            repetitions,
                        )
                        paired_source_frames += 1

            except Exception:
                if not SKIP_BAD_GIFS:
                    raise
                LOGGER.exception(
                    "Skipping unreadable comparison month COR-1%s %d%02d",
                    channel,
                    year,
                    month,
                )

        writer.close()
        writer = None
        finish_movie(temporary, destination, encoded_frames)
        LOGGER.info(
            "COR-1%s %d comparison used %d paired source GIF frames",
            channel,
            year,
            paired_source_frames,
        )
        return True

    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise
    finally:
        if writer is not None:
            writer.close()


# -----------------------------------------------------------------------------
# Channel/year orchestration
# -----------------------------------------------------------------------------


def all_discovered_years(
    method_groups: dict[str, dict[int, dict[int, Path]]],
) -> list[int]:
    """Return the selected union of years found across methods."""

    discovered = {
        year
        for years in method_groups.values()
        for year in years
    }

    if YEARS_TO_PROCESS is not None:
        return sorted(set(YEARS_TO_PROCESS) & discovered)
    return sorted(discovered)


def process_channel(input_path: Path, channel: str) -> int:
    """Create all selected annual movies for one COR-1 channel."""

    root = monthly_gif_root(input_path, channel)
    method_groups = {
        method: discover_monthly_gifs(root, channel, method)
        for method in {"mean", "median"}
    }

    years = all_discovered_years(method_groups)
    if not years:
        LOGGER.warning("No matching monthly GIFs found below %s", root)
        return 0

    output_directory = movie_output_directory(input_path, channel)
    movies_written = 0

    for year in years:
        if OUTPUT_MODE in {"side_by_side", "both"}:
            mean_paths = method_groups["mean"].get(year, {})
            median_paths = method_groups["median"].get(year, {})
            destination = (
                output_directory
                / f"COR1_{channel}_{year}_mean_vs_median.mp4"
            )
            if create_comparison_year_movie(
                channel,
                year,
                mean_paths,
                median_paths,
                destination,
            ):
                movies_written += 1

        if OUTPUT_MODE in {"separate", "both"}:
            for method in METHODS:
                monthly_paths = method_groups[method].get(year, {})
                destination = output_directory / f"COR1_{channel}_{year}_{method}.mp4"
                if create_separate_year_movie(
                    channel,
                    year,
                    method,
                    monthly_paths,
                    destination,
                ):
                    movies_written += 1

    return movies_written


def main() -> None:
    """Program entry point."""

    validate_controls()
    input_path = load_input_path()

    total_written = 0
    for channel in CHANNELS:
        total_written += process_channel(input_path, channel)

    LOGGER.info("Finished; wrote %d annual movie file(s)", total_written)


if __name__ == "__main__":
    main()