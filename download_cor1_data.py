from __future__ import annotations

import calendar
import logging
from datetime import datetime
from pathlib import Path
from parfive import Downloader

from sunpy.net import Fido, attrs as a
import os

import yaml

# Open and parse the YAML file
with open("/Users/crura/Desktop/Research/2026_Summer_Project/STEREO_Data_Processing/config.yaml", "r") as file:
    try:
        input_data = yaml.safe_load(file)
    except yaml.YAMLError as error:
        print(f"Error parsing YAML: {error}")


# -----------------------------------------------------------------------------
# User configuration
# -----------------------------------------------------------------------------
A_OR_B = str(input_data['a_or_b'])
YEAR = input_data['input_year']
SPACECRAFT = "STEREO_" + A_OR_B
INPUT_PATH = Path(input_data['input_path'])
START_TIME = str(input_data['start_time'])
END_TIME = str(input_data['end_time'])

DOWNLOAD_ROOT = INPUT_PATH / A_OR_B
string_process_log = "process_log_" + str(YEAR) + "_" + A_OR_B + ".log"
PROCESS_LOG = INPUT_PATH / string_process_log

string_error_log = "process_error_log_" + str(YEAR) + "_" + A_OR_B + ".log"
ERROR_LOG = INPUT_PATH / string_error_log


# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------

LOGGER = logging.getLogger("cor1_download")
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False

log_format = logging.Formatter(
    "%(asctime)s %(levelname)s %(message)s"
)

process_handler = logging.FileHandler(PROCESS_LOG)
process_handler.setLevel(logging.INFO)
process_handler.setFormatter(log_format)

error_handler = logging.FileHandler(ERROR_LOG)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(log_format)

LOGGER.addHandler(process_handler)
LOGGER.addHandler(error_handler)



class COR1Downloader(Downloader):
    """Download only STEREO sequential COR1 files."""

    def enqueue_file(
        self,
        url,
        path=None,
        filename=None,
        overwrite=None,
        **kwargs,
    ):
        # Do not download n4c1B(A) or any other unwanted files
        end_tag = "s4c1" + A_OR_B.lower() + ".fts"
        if not url.lower().endswith(end_tag):
            return None

        # Temporary workaround for the expired NASA server certificate
        if url.startswith(
            "https://stereo-ssc.nascom.nasa.gov/"
        ):
            kwargs["ssl"] = False

        return super().enqueue_file(
            url,
            path=path,
            filename=filename,
            overwrite=overwrite,
            **kwargs,
        )


# -----------------------------------------------------------------------------
# Download functions
# -----------------------------------------------------------------------------

def download_cor1_day(day: datetime) -> list[Path]:
    """Download STEREO SECCHI/COR1 files for one daily time interval."""

    date_label = day.strftime("%Y%m%d")
    # convert input hour, minute, seconds into ints
    hour_start, min_start, sec_start = [int(x) for x in START_TIME.split(':')]
    hour_end, min_end, sec_end = [int(x) for x in END_TIME.split(':')]

    start_time = day.replace(
        hour=hour_start,
        minute=min_start,
        second=sec_start,
    )

    end_time = day.replace(
        hour=hour_end,
        minute=min_end,
        second=sec_end,
    )

    output_directory = DOWNLOAD_ROOT / date_label
    output_directory.mkdir(parents=True, exist_ok=True)

    LOGGER.info(
        "%s: searching from %s through %s",
        date_label,
        start_time.isoformat(),
        end_time.isoformat(),
    )

    query = Fido.search(
        a.Time(start_time, end_time),
        a.Instrument("SECCHI"),
        a.Source(SPACECRAFT),
        a.Detector("COR1"),
    )

    if len(query) == 0:
        LOGGER.error("%s: no COR1 files found", date_label)
        return []

    downloader = COR1Downloader(
    max_conn=1,
    max_splits=1,
    progress=True,
    overwrite=False,
    )

    downloaded = Fido.fetch(
        query,
        path=str(output_directory / "{file}"),
        downloader=downloader,
    )
    tag = "s4c1" + A_OR_B.lower()
    print(f"Downloaded {len(downloaded)} ${tag} files")

    for error in downloaded.errors:
        print(f"Failed URL: {error.url}")
        print(f"Details: {error.exception!r}")
    
    if downloaded.errors:
        print(
            f"\n{len(downloaded.errors)} of "
            f"{len(query)} downloads failed:"
        )
    
        for index, error in enumerate(downloaded.errors[:10], start=1):
            print(f"\nError {index}")
    
            if hasattr(error, "url"):
                print(f"URL: {error.url}")
    
            # Different parfive versions use different attribute names
            error_details = getattr(
                error,
                "exception",
                getattr(error, "response", error),
            )
    
            print(f"Details: {error_details!r}")
    
        raise RuntimeError(
            f"COR1 download failed for {len(downloaded.errors)} files"
        )

    downloaded_paths = [
        Path(path)
        for path in downloaded
        if Path(path).is_file()
    ]

    for error in getattr(downloaded, "errors", []):
        LOGGER.error("%s: download error: %s", date_label, error)

    if not downloaded_paths:
        LOGGER.error("%s: query succeeded, but no files were downloaded", date_label)
        return []

    LOGGER.info(
        "%s: downloaded %d COR1 files",
        date_label,
        len(downloaded_paths),
    )

    for filename in os.listdir(DOWNLOAD_ROOT):
        file_path = os.path.join(DOWNLOAD_ROOT, filename)

        if not os.path.isfile(file_path):
            continue

        end_tag = "s4c1" + A_OR_B.lower() + ".fts"
        if not filename.lower().endswith(end_tag):
            os.remove(file_path)
            print(f"Deleted: {file_path}")

    return sorted(downloaded_paths)


def download_year(year: int) -> None:
    """Download the configured daily COR1 intervals for an entire year."""

    for month in range(1, 13):
        number_of_days = calendar.monthrange(year, month)[1]

        for day_number in range(1, number_of_days + 1):
            day = datetime(year, month, day_number)

            try:
                download_cor1_day(day)
            except Exception:
                LOGGER.exception(
                    "%s: unhandled download failure",
                    day.strftime("%Y%m%d"),
                )


if __name__ == "__main__":
    DOWNLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    download_year(YEAR)
    # Iterate through files in download directory
    for filename in os.listdir(DOWNLOAD_ROOT):
        # Check if the file contains the string pattern 's4c1a' (sequential polarized image from STEREO A)
        if 's4c1a' or 's4c1A' in filename:
            # Build the full paths for source and destination
            source_path = os.path.join(DOWNLOAD_ROOT, filename)
            destination_path = os.path.join(DOWNLOAD_FINAL, filename)

            # Move the file to directory A
            shutil.move(source_path, destination_path)
        # Check if the file contains the string pattern 's4c1b' (sequential polarized image from STEREO B)
        elif 's4c1b' or 's4c1B' in filename:
            # Build the full paths for source and destination
            source_path = os.path.join(DOWNLOAD_ROOT, filename)
            destination_path = os.path.join(DOWNLOAD_FINAL, filename)

            # Move the file to directory B
            shutil.move(source_path, destination_path)