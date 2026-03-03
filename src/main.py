import argparse
import sys
import os
from pathlib import Path
import logging
import pandas
from functools import partial

from sqlite_to_swmm import SQLitetoSWMM, assign_regenschreiber, sqlite_dump

# --- Open Source Notice -------------------------------------------------------

OPEN_SOURCE_NOTICE = """
This software uses the following open source components:

- Python (PSF License)
- pandas (BSD 3-Clause License)
- SQLite (Public Domain)
- libspatialite from https://www.gaia-gis.it/gaia-sins/
- SWMM (EPA Public Domain) (INP Format)

Please consult the respective licenses for details.
"""


def existing_dll_file(path: str) -> Path:
    p = Path(path)
    if not p.exists():
        raise argparse.ArgumentTypeError(f"DLL file does not exist: {p}")
    if p.suffix.lower() != ".dll":
        raise argparse.ArgumentTypeError(f"Expected a .dll file, got: {p.suffix}")
    return p


def folder_path_for_csv(path: str) -> Path:
    """
    Validates folder for dumping CSVs.
    - Creates it if it doesn't exist
    - Raises error if it exists but is not empty
    """
    p = Path(path)
    if p.exists():
        if any(p.iterdir()):  # folder not empty
            raise argparse.ArgumentTypeError(f"Dump folder exists and is not empty: {p}")
    else:
        p.mkdir(parents=True)
    return p


def existing_sqlite_file(path: str) -> Path:
    p = Path(path)
    if not p.exists():
        raise argparse.ArgumentTypeError(f"Input file does not exist: {p}")
    if p.suffix.lower() not in [".idbm", ".sqlite", ".db"]:
        raise argparse.ArgumentTypeError(
            f"Expected SQLite/IDBM file (.idbm/.sqlite/.db), got: {p.suffix}"
        )
    return p


def output_inp_file(path: str) -> Path:
    p = Path(path)
    if p.suffix.lower() != ".inp":
        raise argparse.ArgumentTypeError("Output file must have .inp extension")
    return p


def existing_csv_file(path: str) -> Path:
    p = Path(path)
    if not p.exists():
        raise argparse.ArgumentTypeError(f"CSV file does not exist: {p}")
    if p.suffix.lower() != ".csv":
        raise argparse.ArgumentTypeError("Regenschreiber file must be a .csv")
    return p


def setup_logging(log_path: Path | None):
    handlers = [logging.StreamHandler()]
    if log_path:
        handlers.append(logging.FileHandler(log_path))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Convert SQLite file in IDBM 8.5 Format to SWMM .inp including optional Regenschreiber assignment for subcatchments."
    )

    parser.add_argument(
        "--sqliteidbm",
        required=True,
        type=existing_sqlite_file,
        help="Path to input SQLite/IDBM file.",
    )

    parser.add_argument(
        "--output",
        required=True,
        type=output_inp_file,
        help="Output SWMM .inp file (will not overwrite unless --force is set).",
    )

    parser.add_argument(
        "--spatialite-dll",
        required=True,
        type=existing_dll_file,
        help="Path to the mod_spatialite.dll file required for spatialite operations.",
    )

    parser.add_argument(
        "--regenschreiber",
        type=existing_csv_file,
        help="Optional CSV file with Regenschreiber assignment (must contain unique SCID column and RegenschreiberID column).",
    )

    parser.add_argument(
        "--dump-csv",
        type=folder_path_for_csv,
        help="Optional folder path to dump all SQLite tables as CSVs. Folder must be empty or not exist (will be created).",
    )

    parser.add_argument(
        "--log",
        type=Path,
        help="Optional log file path.",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow overwriting existing output file.",
    )

    parser.add_argument(
        "--license",
        action="store_true",
        help="Show open source license information and exit.",
    )

    args = parser.parse_args()

    # License option
    if args.license:
        print(OPEN_SOURCE_NOTICE)
        sys.exit(0)

    # Overwrite safeguard
    if args.output.exists() and not args.force:
        parser.error(
            f"Output file already exists: {args.output}. "
            "Use --force to overwrite."
        )

    # Setup logging
    if args.log is None:
        args.log = args.output.with_name("output_errors.log") #output is a Path object
    setup_logging(args.log)

    logging.info("Starting conversion process")

    # Optional Regenschreiber handling
    pandasRS = None
    if args.regenschreiber:
        logging.info(f"Loading Regenschreiber CSV: {args.regenschreiber}")
        pandasRS = pandas.read_csv(args.regenschreiber)

        if "SCID" not in pandasRS.columns:
            parser.error("Regenschreiber CSV must contain column 'SCID'.")

        if not pandasRS["SCID"].is_unique:
            parser.error("Column 'SCID' must contain unique values.")
    
    

    converter = SQLitetoSWMM(
        sqlite_path=str(args.sqliteidbm),
        swmm_path=str(args.output),
        spatialite_dll_path=str(args.spatialite_dll),
    )

    if pandasRS is not None:
        objects = converter.object_extraction(
            individual_regenschreiber=partial(assign_regenschreiber, df=pandasRS)
        )
    else:
        objects = converter.object_extraction()

    converter.convert(write=True, object_collection=objects)

    logging.info("Conversion completed successfully")

    if args.dump_csv:
        logging.info(f"Dumping SQLite tables from {args.sqliteidbm} into folder {args.dump_csv}")
        sqlite_dump(sqlite_path=str(args.sqliteidbm), export_folder=str(args.dump_csv), spatialite_dll_path=str(args.spatialite_dll))
        logging.info("SQLite tables dumped successfully")


if __name__ == "__main__":
    main()