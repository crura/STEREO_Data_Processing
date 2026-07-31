from pathlib import Path
import os
import re

import numpy as np
from astropy.io import fits

from secchipy import (
    cor_polar_prep,
    cor_polar_sequence_prep,
    ensure_secchi_calibration_for_inputs,
)
from secchipy.calibrate.shared import get_bkgimg
from secchipy.core.models import ProcessingOptions
from secchipy.io import write_fits
import re
from secchipy.validation import compare_fits_files
from astropy.io import fits
import numpy as np
import os
from secchipy.calibrate.shared import get_bkgimg

SECCHI_BKG = Path(
    "/Users/crura/stereo/secchi/backgrounds"
).expanduser()

if not SECCHI_BKG.is_dir():
    raise NotADirectoryError(
        f"SECCHI background directory does not exist: {SECCHI_BKG}"
    )

os.environ["SECCHI_BKG"] = str(SECCHI_BKG)

print(f"SECCHI_BKG={os.environ['SECCHI_BKG']}")


def find_cor1_files(input_directory: str | Path) -> list[Path]:
    """Return the raw COR1 files directly inside one directory."""

    input_directory = Path(input_directory)

    return sorted(
        path
        for path in input_directory.iterdir()
        if path.is_file()
        and path.name.lower().endswith("s4c1b.fts")
    )


def print_raw_file_order(raw_files: list[Path]) -> None:
    """Print raw inputs chronologically and by polarization angle."""

    records = []

    for path in raw_files:
        header = fits.getheader(path)

        records.append(
            {
                "path": path,
                "date_obs": str(header.get("DATE-OBS", "<missing>")),
                "polar": float(
                    header.get("POLAR", float("nan"))
                ) % 360.0,
                "obs_id": header.get("OBS_ID", "<missing>"),
                "exptime": header.get("EXPTIME", "<missing>"),
                "crota": header.get("CROTA", "<missing>"),
                "biasmean": header.get("BIASMEAN", "<missing>"),
            }
        )

    print("\nRaw files in filename/time order")
    print("--------------------------------")

    for position, record in enumerate(records, start=1):
        print(
            f"{position}: "
            f"file={record['path'].name}, "
            f"DATE-OBS={record['date_obs']}, "
            f"POLAR={record['polar']}, "
            f"OBS_ID={record['obs_id']}, "
            f"EXPTIME={record['exptime']}, "
            f"CROTA={record['crota']}, "
            f"BIASMEAN={record['biasmean']}"
        )

    ordered = sorted(
        records,
        key=lambda record: record["polar"],
    )

    print("\nExpected polarization-angle order")
    print("---------------------------------")

    for position, record in enumerate(ordered, start=1):
        print(
            f"{position}: "
            f"POLAR={record['polar']:g} degrees, "
            f"file={record['path']}"
        )

    rounded_angles = {
        round(record["polar"])
        for record in records
    }

    if rounded_angles != {0, 120, 240}:
        raise RuntimeError(
            "The directory does not contain the expected "
            "POLAR=0, 120, and 240 measurements. "
            f"Found: {sorted(rounded_angles)}"
        )

    obs_ids = {
        record["obs_id"]
        for record in records
        if record["obs_id"] != "<missing>"
    }

    if len(obs_ids) > 1:
        print(
            "\nWARNING: The files have different OBS_ID values: "
            f"{sorted(obs_ids)}"
        )


def make_pb_filename(component_files: tuple[str, ...]) -> str:
    """Create the pB filename from the earliest triplet component."""

    filenames = [
        Path(filename).name
        for filename in component_files
    ]

    pattern = re.compile(
        r"^(?P<timestamp>\d{8}_\d{6})_s4c1"
        r"(?P<spacecraft>[AB])\.fts$",
        re.IGNORECASE,
    )

    parsed_files = []

    for filename in filenames:
        match = pattern.match(filename)

        if match is None:
            raise ValueError(
                f"Unexpected COR1 filename format: {filename}"
            )

        parsed_files.append(
            (
                match.group("timestamp"),
                match.group("spacecraft").upper(),
            )
        )

    earliest_timestamp, spacecraft = min(
        parsed_files,
        key=lambda item: item[0],
    )

    return (
        f"{earliest_timestamp}_0P4c1{spacecraft}.fts"
    )


def process_cor1_sequence(
    input_directory: str | Path,
) -> list[Path]:
    """Process all valid COR1 polarization triplets in one directory."""

    input_directory = Path(input_directory)

    output_directory = input_directory / "processed"
    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(f"\nInput directory: {input_directory}")
    print(f"Output directory: {output_directory}")

    raw_files = find_cor1_files(input_directory)

    if not raw_files:
        raise FileNotFoundError(
            f"No s4c1B.fts files found in {input_directory}"
        )

    print_raw_file_order(raw_files)

    print("\nBackground-image selection")
    print("--------------------------")

    for raw_file in raw_files:
        raw_header = fits.getheader(raw_file)

        (
            background_data,
            _background_header,
            background_name,
        ) = get_bkgimg(raw_header)

        polar = raw_header.get("POLAR", "<missing>")

        print(
            f"POLAR={polar}: "
            f"input={raw_file.name}, "
            f"background={background_name or '<not found>'}"
        )

        if background_data is None:
            raise RuntimeError(
                "No COR1 background was found for "
                f"{raw_file.name} with POLAR={polar}. "
                f"SECCHI_BKG={os.environ.get('SECCHI_BKG')}"
            )

    calibration_cache, _calibration_files = (
        ensure_secchi_calibration_for_inputs(raw_files)
    )

    options = ProcessingOptions(
        # Equivalent to /CALIMG_OFF
        calibration_image=False,

        # Equivalent to /ROTATE_ON
        rotate_north=True,

        # Closer to legacy SECCHI_PREP missing-pixel handling
        missing_data_policy="idl",

        # Calibration assets were resolved above
        auto_download_calibration=False,
        calibration_cache_dir=calibration_cache,
    )

    results = cor_polar_sequence_prep(
        raw_files,
        options=options,
    )

    if not results:
        raise RuntimeError(
            "No valid COR1 polarization triplets were found "
            f"in {input_directory}"
        )

    written_files = []

    for result_number, result in enumerate(
        results,
        start=1,
    ):
        product = result.polarized_brightness

        component_files = product.metadata.get(
            "component_files",
            (),
        )

        if len(component_files) != 3:
            raise RuntimeError(
                "Expected exactly three component files, "
                f"but found {len(component_files)}: "
                f"{component_files}"
            )

        print(
            f"\nSECCHIpy triplet {result_number} "
            "combination order"
        )
        print("--------------------------------------------")

        for position, (component, angle) in enumerate(
            zip(
                result.components,
                result.polarization_angles,
            ),
            start=1,
        ):
            component_header = component.header

            component_name = str(
                component_header.get(
                    "FILENAME",
                    component_files[position - 1],
                )
            )

            data = component.data
            finite = data[np.isfinite(data)]

            print(
                f"{position}: "
                f"POLAR={angle:g} degrees, "
                f"file={component_name}"
            )

            print(
                "   "
                f"DATE-OBS="
                f"{component_header.get('DATE-OBS', '<missing>')}, "
                f"OBS_ID="
                f"{component_header.get('OBS_ID', '<missing>')}, "
                f"EXPTIME="
                f"{component_header.get('EXPTIME', '<missing>')}, "
                f"CROTA="
                f"{component_header.get('CROTA', '<missing>')}"
            )

            history = component_header.get("HISTORY", [])

            if isinstance(history, str):
                history = [history]
            else:
                history = list(history)

            background_entries = [
                str(entry)
                for entry in history
                if "background" in str(entry).lower()
            ]

            print(
                "   CALFAC="
                f"{component_header.get('CALFAC', '<missing>')}"
            )

            if background_entries:
                print("   Background processing:")

                for entry in background_entries:
                    print(f"      {entry}")
            else:
                print(
                    "   WARNING: no background-subtraction "
                    "entry in HISTORY"
                )

            if finite.size:
                print(
                    f"   min={np.min(finite):.8g}, "
                    f"max={np.max(finite):.8g}, "
                    f"mean={np.mean(finite):.8g}, "
                    f"std={np.std(finite):.8g}"
                )

        output_name = make_pb_filename(component_files)
        output_path = output_directory / output_name

        product.header["FILENAME"] = output_name

        write_fits(
            output_path,
            product.data,
            product.header,
            overwrite=True,
        )

        written_files.append(output_path)

        print(f"Wrote: {output_path}")

    return written_files


process_cor1_sequence('/Volumes/Seagate/test/20080101Test')


python_file = Path(
    "/Volumes/Seagate/test/20080101Test/processed/20080101_093500_0P4c1B.fts"
)

idl_file = Path(
    "/Volumes/Seagate/test/20080101_IDL/processed/20080101_093500_0P4c1B.fts"
)

report = compare_fits_files(
    python_file,
    idl_file,
    atol=1e-6,
    rtol=1e-6,
)

print("Image comparison")
print("----------------")
print(f"Maximum absolute difference: {report.array.max_abs_diff}")
print(f"Mean absolute difference:    {report.array.mean_abs_diff}")
print(f"99th percentile difference:  {report.array.p99_abs_diff}")
print(f"RMSE:                        {report.array.rmse}")
print(f"Percent RMSE:                {report.array.percent_rmse}")
print(f"Finite-pixel overlap:        {report.array.finite_overlap}")
print(f"Within absolute tolerance:   {report.array.within_atol}")
print(f"Within relative tolerance:   {report.array.within_rtol}")

print("\nHeader comparison")
print("-----------------")

def process_cor1_directory_tree(
    input_root: str | Path,
    *,
    continue_on_error: bool = True,
) -> dict[Path, list[Path]]:
    """
    Recursively process every directory containing COR1 raw files.

    Generated directories named 'processed' are excluded from the
    recursive search.
    """

    input_root = Path(input_root).expanduser().resolve()

    if not input_root.is_dir():
        raise NotADirectoryError(
            f"Input root does not exist: {input_root}"
        )

    processed_directories: dict[Path, list[Path]] = {}
    failures: dict[Path, Exception] = {}

    print(f"\nSearching recursively under: {input_root}")

    for current_directory, directory_names, filenames in os.walk(
        input_root
    ):
        # Prevent os.walk from entering output directories.
        directory_names[:] = sorted(
            (
                name
                for name in directory_names
                if name.lower() != "processed"
            ),
            key=str.lower,
        )

        current_path = Path(current_directory)

        contains_cor1_files = any(
            filename.lower().endswith("s4c1b.fts")
            for filename in filenames
        )

        if not contains_cor1_files:
            continue

        print("\n" + "=" * 80)
        print(f"Processing directory: {current_path}")
        print("=" * 80)

        try:
            written_files = process_cor1_sequence(
                current_path
            )

            processed_directories[current_path] = (
                written_files
            )

        except Exception as error:
            failures[current_path] = error

            print(
                f"\nERROR processing {current_path}: "
                f"{type(error).__name__}: {error}"
            )

            if not continue_on_error:
                raise

    if not processed_directories and not failures:
        raise FileNotFoundError(
            "No directories containing s4c1B.fts files "
            f"were found under {input_root}"
        )

    print("\n" + "=" * 80)
    print("Processing summary")
    print("=" * 80)

    total_written = sum(
        len(paths)
        for paths in processed_directories.values()
    )

    print(
        f"Successful directories: "
        f"{len(processed_directories)}"
    )
    print(f"Failed directories: {len(failures)}")
    print(f"Total FITS products written: {total_written}")

    for directory, paths in processed_directories.items():
        print(
            f"\n{directory}: "
            f"{len(paths)} product(s)"
        )

        for path in paths:
            print(f"  {path}")

    if failures:
        print("\nFailures")
        print("--------")

        for directory, error in failures.items():
            print(
                f"{directory}: "
                f"{type(error).__name__}: {error}"
            )

    return processed_directories


# This should be the parent directory containing all of the
# day/subsequence directories to process.
INPUT_ROOT = Path("/Volumes/Seagate/Chris/2013_Images")

process_cor1_directory_tree(
    INPUT_ROOT,
    continue_on_error=True,
)