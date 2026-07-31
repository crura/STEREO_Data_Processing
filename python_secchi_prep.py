from pathlib import Path

from secchipy import (
    cor_polar_sequence_prep,
    ensure_secchi_calibration_for_inputs,
)
from secchipy.core.models import ProcessingOptions
from secchipy.io import write_fits


def process_cor1_sequence(
    input_directory: str | Path,
    output_directory: str | Path,
) -> list[Path]:
    input_directory = Path(input_directory)
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    # These should be raw sequential polarization files.
    raw_files = sorted(input_directory.glob("*s4c1b.fts"))

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

    for index, result in enumerate(results):
        # Use this for the IDL behavior:
        # /POLARIZ_ON, /PB
        product = result.polarized_brightness

        date_obs = str(
            product.header.get("DATE-OBS", f"triplet_{index:04d}")
        )

        safe_date = (
            date_obs
            .replace("-", "")
            .replace(":", "")
            .replace("T", "_")
            .replace(".", "_")
        )

        output_path = output_directory / f"{safe_date}_cor1_pb.fts"

        write_fits(
            output_path,
            product.data,
            product.header,
            overwrite=True,
        )

        written_files.append(output_path)
        print(f"Wrote: {output_path}")

    return written_files