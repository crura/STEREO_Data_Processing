from pathlib import Path

from secchipy import (
    cor_polar_sequence_prep,
    ensure_secchi_calibration_for_inputs,
)
from secchipy.core.models import ProcessingOptions
from secchipy.io import write_fits
import re
from secchipy.validation import compare_fits_files
from astropy.io import fits
import numpy as np

def print_raw_file_order(raw_files: list[Path]) -> None:
    """Print raw inputs chronologically and by polarization angle."""

    records = []

    for path in raw_files:
        header = fits.getheader(path)

        records.append(
            {
                "path": path,
                "date_obs": str(header.get("DATE-OBS", "<missing>")),
                "polar": float(header.get("POLAR", float("nan"))) % 360.0,
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

    ordered = sorted(records, key=lambda record: record["polar"])

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
            "The triplet does not contain exactly POLAR=0, 120, and 240. "
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
    """Create the pB output filename from the earliest triplet component."""

    filenames = [Path(filename).name for filename in component_files]

    pattern = re.compile(
        r"^(?P<timestamp>\d{8}_\d{6})_s4c1(?P<spacecraft>[AB])\.fts$",
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

    # YYYYMMDD_HHMMSS sorts chronologically as a string
    earliest_timestamp, spacecraft = min(
        parsed_files,
        key=lambda item: item[0],
    )

    return f"{earliest_timestamp}_0P4c1{spacecraft}.fts"


def process_cor1_sequence(
    input_directory: str | Path,
    ) -> list[Path]:
    input_directory = Path(input_directory)

    # Create <day_directory>/processed if it does not already exist
    output_directory = input_directory / "processed"
    output_directory.mkdir(parents=True, exist_ok=True)

    print(f"Output directory: {output_directory}")

    raw_files = sorted(
    path
    for path in input_directory.iterdir()
    if path.is_file()
    and path.name.lower().endswith("s4c1b.fts"))

    if not raw_files:
        raise FileNotFoundError(
            f"No s4c1b.fts files found in {input_directory}"
        )

    print_raw_file_order(raw_files)

    # Download or locate the calibration assets required by SECCHIpy.
    calibration_cache, calibration_files = (
        ensure_secchi_calibration_for_inputs(raw_files)
    )

    options = ProcessingOptions(
        # Equivalent to /CALIMG_OFF
        calibration_image=False,

        # Equivalent to /ROTATE_ON
        rotate_north=True,

        # Closer to legacy SECCHI_PREP missing-pixel handling
        missing_data_policy="idl",

        # Calibration assets have already been resolved above
        auto_download_calibration=False,
        calibration_cache_dir=calibration_cache,
    )

    # Equivalent to /POLARIZ_ON for a sequence containing multiple triplets.
    # SECCHIpy selects valid 0/120/240-degree triplets automatically.
    results = cor_polar_sequence_prep(
        raw_files,
        options=options,
        max_triplet_span_seconds=90.0,
    )

    if not results:
        raise RuntimeError(
            "No valid COR1 polarization triplets were found"
        )

    written_files = []

    for result in results:
        product = result.polarized_brightness

    component_files = product.metadata.get("component_files", ())

    if len(component_files) != 3:
        raise RuntimeError(
            "Expected exactly three component files, "
            f"but found {len(component_files)}: {component_files}"
        )

    print(f"\nSECCHIpy triplet {result_number} combination order")
    print("------------------------------------------------")

    for position, (component, angle) in enumerate(
        zip(result.components, result.polarization_angles),
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
            f"   DATE-OBS={component_header.get('DATE-OBS', '<missing>')}, "
            f"OBS_ID={component_header.get('OBS_ID', '<missing>')}, "
            f"EXPTIME={component_header.get('EXPTIME', '<missing>')}, "
            f"CROTA={component_header.get('CROTA', '<missing>')}"
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