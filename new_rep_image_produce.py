"""Create four chronological representative COR-1 images per observing day.

The input files for each day are sorted by DATE-OBS and divided into four
nearly equal-sized groups.  Every input file is used exactly once.  Each group
can be combined with a mean, a median, or both.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import yaml
from astropy.io import fits
from tqdm import tqdm


# -----------------------------------------------------------------------------
# User controls
# -----------------------------------------------------------------------------

NUMBER_OF_REPRESENTATIVES = 4

# Use None to process all four groups.  Examples: (1,), (2, 3), or (1, 4).
SUBSTACKS_TO_PROCESS: tuple[int, ...] | None = None

# Keeping both preserves the behavior of the original script, but creates
# 4 mean files plus 4 median files per day.  Use ("median",) or ("mean",)
# to create exactly four output FITS files per day.
COMBINE_METHODS = ("mean", "median")

WRITE_DAY_DIRECTORY_COPY = False
WRITE_CONSOLIDATED_COPY = False

OVERWRITE_OUTPUTS = True

# Match the original behavior by treating unexpected FITS files in a daily
# input directory as an error instead of silently combining a partial set.
STRICT_INPUT_FILENAMES = True

VALID_FILE_SUFFIXES = (
    "0_0P4c1A.fts",
    "0_0P4c1B.fts",
)


# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------

SCRIPT_PATH = Path(__file__).resolve()
REPO_PATH = SCRIPT_PATH.parent

with (REPO_PATH / "config.yaml").open("r", encoding="utf-8") as stream:
    yaml_parse = yaml.safe_load(stream)

INPUT_PATH = Path(yaml_parse["input_path"])

# A copy is written beside each day's input directory and another consolidated
# copy is written under A/Representative_Images or B/Representative_Images.
CUSTOM_OUTPUT_ROOT = INPUT_PATH / 'Rep_Images'

# Create directory if it doesn't exist
CUSTOM_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class FitsRecord:
    """The file path, header, and observation timestamp for one image."""

    path: Path
    header: fits.Header
    date_obs: str


def is_processed_cor1_file(path: Path) -> bool:
    """Return True only for the processed COR-1 FITS filenames of interest."""

    return path.is_file() and path.name.endswith(VALID_FILE_SUFFIXES)


def find_processed_day_directories(control_path: Path) -> list[Path]:
    """Find directories below control_path that contain processed COR-1 files."""

    day_directories: list[Path] = []

    for root, directory_names, file_names in os.walk(control_path):
        root_path = Path(root)

        # Do not recurse into output directories created by this script.
        if "Representative_Images" in root_path.parts:
            directory_names[:] = []
            continue

        is_processed_path = any(
            "processed" in part.lower() for part in root_path.parts
        )
        if not is_processed_path:
            continue

        if any((root_path / name).name.endswith(VALID_FILE_SUFFIXES) for name in file_names):
            day_directories.append(root_path)

    return sorted(day_directories)


def load_sorted_records(process_path: Path) -> list[FitsRecord]:
    """Read headers and return valid input files sorted by DATE-OBS."""

    records: list[FitsRecord] = []

    fits_files = [
        path
        for path in process_path.iterdir()
        if path.is_file() and path.suffix.lower() == ".fts"
    ]
    unexpected_files = [
        path for path in fits_files if not is_processed_cor1_file(path)
    ]
    if STRICT_INPUT_FILENAMES and unexpected_files:
        unexpected_names = ", ".join(path.name for path in unexpected_files)
        raise ValueError(
            f"Unexpected FITS files in {process_path}: {unexpected_names}"
        )

    for file_path in fits_files:
        if not is_processed_cor1_file(file_path):
            continue

        header = fits.getheader(file_path, ext=0)
        if "DATE-OBS" not in header:
            raise KeyError(f"{file_path} has no DATE-OBS header keyword")

        records.append(
            FitsRecord(
                path=file_path,
                header=header,
                date_obs=str(header["DATE-OBS"]).strip(),
            )
        )

    # FITS DATE-OBS values are ISO-8601 strings, so lexical order is
    # chronological when the files use a consistent UTC representation.
    records.sort(key=lambda record: record.date_obs)
    return records


def load_clean_image(file_path: Path) -> np.ndarray:
    """Load one image as floating point and replace non-finite values."""

    image = np.array(fits.getdata(file_path, ext=0), dtype=np.float64, copy=True)
    finite_mask = np.isfinite(image)

    if not finite_mask.all():
        if not finite_mask.any():
            raise ValueError(f"All pixels are NaN or infinite in {file_path}")

        # Preserve the original script's behavior: replace bad pixels with the
        # minimum finite value in that image, but do it without a Python loop.
        image[~finite_mask] = image[finite_mask].min()

    return image


def load_substack(records: Sequence[FitsRecord]) -> np.ndarray:
    """Load one substack and verify that all image dimensions agree."""

    images = [load_clean_image(record.path) for record in records]
    shapes = {image.shape for image in images}

    if len(shapes) != 1:
        file_list = ", ".join(record.path.name for record in records)
        raise ValueError(f"Image dimensions do not match in substack: {file_list}")

    return np.stack(images, axis=0)


def make_output_header(
    records: Sequence[FitsRecord],
    substack_number: int,
    total_substacks: int,
) -> fits.Header:
    """Copy a middle header and add provenance for the combined image."""

    middle_record = records[len(records) // 2]
    header = middle_record.header.copy()

    # DATE-OBS remains the observation time of the middle input frame.
    header["DATE-BEG"] = (records[0].date_obs, "First input observation")
    header["DATE-END"] = (records[-1].date_obs, "Last input observation")
    header["NCOMBINE"] = (len(records), "Number of images combined")
    header["REPGRP"] = (substack_number, "Representative group number")
    header["REPTOTAL"] = (total_substacks, "Groups requested for this day")
    header.add_history(
        f"Combined chronological group {substack_number} of {total_substacks}."
    )

    return header


def combine_stack(stack: np.ndarray, method: str) -> np.ndarray:
    """Combine a three-dimensional image stack with the requested statistic."""

    if method == "mean":
        return np.mean(stack, axis=0)
    if method == "median":
        return np.median(stack, axis=0)

    raise ValueError(f"Unsupported combine method: {method!r}")


def selected_substack_numbers(total_substacks: int) -> set[int]:
    """Validate and return the one-based group numbers to process."""

    if SUBSTACKS_TO_PROCESS is None:
        return set(range(1, total_substacks + 1))

    selected = set(SUBSTACKS_TO_PROCESS)
    invalid = sorted(number for number in selected if not 1 <= number <= total_substacks)
    if invalid:
        raise ValueError(
            f"SUBSTACKS_TO_PROCESS contains invalid values {invalid}; "
            f"valid values are 1 through {total_substacks}."
        )

    return selected


def output_directories(
    process_path: Path,
    control_path: Path,
) -> list[Path]:
    """Return all enabled output directories, without duplicates."""

    directories: list[Path] = []

    if WRITE_DAY_DIRECTORY_COPY:
        directories.append(
            process_path / "Representative_Images" / "4_per_day"
        )

    if WRITE_CONSOLIDATED_COPY:
        directories.append(
            control_path / "Representative_Images" / "4_per_day"
        )

    if CUSTOM_OUTPUT_ROOT is not None:
        # control_path.name is either "A" or "B".
        directories.append(
            CUSTOM_OUTPUT_ROOT / control_path.name / "4_per_day"
        )

    unique_directories = list(dict.fromkeys(directories))

    if not unique_directories:
        raise ValueError(
            "No output directory is enabled. Enable an output option "
            "or provide CUSTOM_OUTPUT_ROOT."
        )

    for directory in unique_directories:
        directory.mkdir(parents=True, exist_ok=True)

    return unique_directories


def day_label_from_records(records: Sequence[FitsRecord], fallback: str) -> str:
    """Return YYYYMMDD from DATE-OBS, falling back to the directory name."""

    first_date = records[0].date_obs
    if len(first_date) >= 10 and first_date[4] == "-" and first_date[7] == "-":
        return first_date[:10].replace("-", "")

    return fallback


def write_four_representatives(process_path: Path, control_path: Path) -> int:
    """Create up to four selected chronological representative groups for a day.

    Returns the number of FITS files written, counting all enabled output copies.
    """

    records = load_sorted_records(process_path)
    number_of_files = len(records)

    if number_of_files == 0:
        LOGGER.warning("No valid processed COR-1 files in %s", process_path)
        return 0

    if number_of_files < NUMBER_OF_REPRESENTATIVES:
        LOGGER.warning(
            "Skipping %s: found %d files, but %d are required to make four "
            "non-empty substacks without duplicating images.",
            process_path,
            number_of_files,
            NUMBER_OF_REPRESENTATIVES,
        )
        return 0

    # array_split uses every index once and distributes any remainder over the
    # earliest groups.  Example: 10 files -> group sizes 3, 3, 2, 2.
    index_groups = np.array_split(
        np.arange(number_of_files),
        NUMBER_OF_REPRESENTATIVES,
    )

    selected_groups = selected_substack_numbers(NUMBER_OF_REPRESENTATIVES)
    directories = output_directories(process_path, control_path)
    day_label = day_label_from_records(records, fallback=process_path.name)

    group_sizes = [len(group) for group in index_groups]
    LOGGER.info(
        "%s: splitting %d files into groups of %s",
        day_label,
        number_of_files,
        group_sizes,
    )

    files_written = 0

    for substack_number, index_group in enumerate(index_groups, start=1):
        if substack_number not in selected_groups:
            continue

        substack_records = [records[int(index)] for index in index_group]
        stack = load_substack(substack_records)
        output_header = make_output_header(
            substack_records,
            substack_number=substack_number,
            total_substacks=NUMBER_OF_REPRESENTATIVES,
        )

        for method in COMBINE_METHODS:
            combined_image = combine_stack(stack, method)
            output_name = (
                f"{day_label}_rep_{substack_number:02d}_of_"
                f"{NUMBER_OF_REPRESENTATIVES:02d}_{method}.fts"
            )

            for directory in directories:
                output_path = directory / output_name
                fits.PrimaryHDU(
                    data=combined_image,
                    header=output_header,
                ).writeto(output_path, overwrite=OVERWRITE_OUTPUTS)
                files_written += 1

        # Release this group's image cube before loading the next one.
        del stack

    return files_written


def process_images(control_path: Path) -> None:
    """Process every daily directory below one COR-1 channel directory."""

    processed_paths = find_processed_day_directories(control_path)
    if not processed_paths:
        LOGGER.warning("No processed day directories found below %s", control_path)
        return

    total_written = 0
    for process_path in tqdm(processed_paths, desc=control_path.name):
        try:
            total_written += write_four_representatives(process_path, control_path)
        except Exception:
            LOGGER.exception("Failed while processing %s", process_path)

    LOGGER.info("Finished %s; wrote %d FITS files", control_path, total_written)


def main() -> None:
    process_images(INPUT_PATH / "A")
    process_images(INPUT_PATH / "B")


if __name__ == "__main__":
    main()
