from pathlib import Path

from secchipy import (
    cor_polar_sequence_prep,
    ensure_secchi_calibration_for_inputs,
)
from secchipy.core.models import ProcessingOptions
from secchipy.io import write_fits
import re

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

        output_name = make_pb_filename(component_files)
        output_path = output_directory / output_name

        # Keep the FITS header consistent with the actual output filename
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


process_cor1_sequence('/Volumes/Seagate/test/20080101')