from __future__ import annotations

import calendar
import logging
from datetime import datetime
from pathlib import Path

from sunpy.net import Fido, attrs as a


# -----------------------------------------------------------------------------
# User configuration
# -----------------------------------------------------------------------------

YEAR = 2014
SPACECRAFT = "STEREO_B"

DOWNLOAD_ROOT = Path(
    "/Volumes/Seagate/Chris/2014_Images/B"
)

PROCESS_LOG = Path(
    "/Volumes/Seagate/Chris/2014_Images/process_log_2014_B.log"
)

ERROR_LOG = Path(
    "/Volumes/Seagate/Chris/2014_Images/process_error_log_2014_B.log"
)


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


# -----------------------------------------------------------------------------
# Download functions
# -----------------------------------------------------------------------------

def download_cor1_day(day: datetime) -> list[Path]:
    """Download STEREO-B SECCHI/COR1 files for one daily time interval."""

    date_label = day.strftime("%Y%m%d")

    start_time = day.replace(
        hour=9,
        minute=35,
        second=0,
    )

    end_time = day.replace(
        hour=18,
        minute=35,
        second=25,
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

    # Do not use a.Sample() here. Sampling could remove one or more images
    # belonging to a three-image polarization sequence.
    downloaded = Fido.fetch(
        query,
        path=str(output_directory / "{file}"),
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