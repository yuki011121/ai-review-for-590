#!/usr/bin/env python3
"""
Utility script to bootstrap `students.csv` and `proposal_mapping.csv`
by scanning the PDFs inside the data/ directory.

Usage examples:
    python3 generate_student_and_mapping.py
    python3 generate_student_and_mapping.py --data-dir custom_data --start-index 5
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


DEFAULT_DATA_DIR = Path("./data")
DEFAULT_STUDENTS_FILE = Path("students.csv")
DEFAULT_MAPPING_FILE = Path("proposal_mapping.csv")
DEFAULT_METADATA_CSV = Path("csv/590-F25_Thesis_Proposal_Review_Revised.csv")


@dataclass(frozen=True)
class ProposalRecord:
    student_id: str
    proposal_id: str
    filename: str
    author_name: str = ""
    proposal_title: str = ""


@dataclass(frozen=True)
class MetadataRecord:
    proposal_id: str
    author_name: str
    proposal_title: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate students.csv and proposal_mapping.csv from proposal PDFs."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing proposal PDF files (default: ./data)",
    )
    parser.add_argument(
        "--students-file",
        type=Path,
        default=DEFAULT_STUDENTS_FILE,
        help="Output path for students.csv (default: students.csv)",
    )
    parser.add_argument(
        "--mapping-file",
        type=Path,
        default=DEFAULT_MAPPING_FILE,
        help="Output path for proposal_mapping.csv (default: proposal_mapping.csv)",
    )
    parser.add_argument(
        "--metadata-csv",
        type=Path,
        default=DEFAULT_METADATA_CSV,
        help="Optional CSV file that contains proposal metadata (default: csv/590-F25_Thesis_Proposal_Review_Revised.csv)",
    )
    parser.add_argument(
        "--metadata-id-column",
        default="Proposal ID",
        help="Column name in metadata CSV for proposal IDs (default: 'Proposal ID')",
    )
    parser.add_argument(
        "--metadata-author-column",
        default="Author First Name Last Name",
        help="Column name in metadata CSV for author names (default: 'Author First Name Last Name')",
    )
    parser.add_argument(
        "--metadata-title-column",
        default="Proposal Title",
        help="Column name in metadata CSV for proposal titles (default: 'Proposal Title')",
    )
    parser.add_argument(
        "--student-prefix",
        default="S",
        help="Prefix to use when auto-generating student IDs (default: S)",
    )
    parser.add_argument(
        "--proposal-prefix",
        default="P",
        help="Prefix to use when auto-generating proposal IDs (default: P)",
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=1,
        help="Start index for generated IDs when filenames do not already contain IDs (default: 1)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing CSV files without prompting.",
    )
    return parser.parse_args()


def ensure_data_dir(data_dir: Path) -> Iterable[Path]:
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory '{data_dir}' does not exist.")
    pdfs = sorted(data_dir.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"No PDF files found in '{data_dir}'.")
    return pdfs


def normalize_value(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def load_metadata(
    csv_path: Path,
    id_column: str,
    author_column: str,
    title_column: str,
) -> Dict[str, MetadataRecord]:
    if not csv_path.exists():
        return {}

    metadata: Dict[str, MetadataRecord] = {}

    with csv_path.open("r", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            proposal_id = row.get(id_column, "").strip()
            author = row.get(author_column, "").strip()
            title = row.get(title_column, "").strip()

            if not proposal_id and not title:
                continue

            record = MetadataRecord(
                proposal_id=proposal_id,
                author_name=author,
                proposal_title=title,
            )

            if title:
                metadata.setdefault(normalize_value(title), record)
            if proposal_id:
                metadata.setdefault(f"id:{proposal_id.lower()}", record)

    return metadata


def match_metadata(stem: str, metadata: Dict[str, MetadataRecord]) -> Optional[MetadataRecord]:
    if not metadata:
        return None

    normalized_title = normalize_value(stem)
    if normalized_title in metadata:
        return metadata[normalized_title]

    match = re.search(r"(P\d+)", stem, re.IGNORECASE)
    if match:
        meta = metadata.get(f"id:{match.group(1).lower()}")
        if meta:
            return meta

    return None


def extract_student_id(filename: str, fallback: str) -> str:
    """
    Detect an existing student identifier in the filename (e.g., S01, s12, s003_H1.pdf).
    If none is found, return the provided fallback ID.
    """
    stem = Path(filename).stem
    match = re.match(r"(S\d+)", stem.upper())
    if match:
        return match.group(1)
    return fallback


def extract_proposal_id(stem: str, fallback: str) -> str:
    match = re.match(r"(P\d+)", stem.upper())
    if match:
        return match.group(1)
    return fallback


def build_records(
    pdf_files: Iterable[Path],
    student_prefix: str,
    proposal_prefix: str,
    start_index: int,
    metadata: Dict[str, MetadataRecord],
) -> List[ProposalRecord]:
    records: List[ProposalRecord] = []
    seen_students = set()
    index = start_index

    for pdf in pdf_files:
        stem = pdf.stem
        student_candidate = f"{student_prefix}{index:02d}"
        student_id = extract_student_id(pdf.name, student_candidate)

        # Ensure uniqueness even if filenames share the same detected ID
        while student_id in seen_students:
            index += 1
            student_id = f"{student_prefix}{index:02d}"

        proposal_candidate = f"{proposal_prefix}{index:03d}"
        proposal_id = extract_proposal_id(stem, proposal_candidate)

        meta = match_metadata(stem, metadata)
        author_name = meta.author_name if meta else ""
        proposal_title = meta.proposal_title if meta and meta.proposal_title else pdf.stem
        if meta and meta.proposal_id:
            proposal_id = meta.proposal_id

        records.append(
            ProposalRecord(
                student_id=student_id,
                proposal_id=proposal_id,
                filename=pdf.name,
                author_name=author_name,
                proposal_title=proposal_title,
            )
        )
        seen_students.add(student_id)
        index += 1

    return records


def write_students_csv(path: Path, records: Iterable[ProposalRecord]) -> None:
    students: Dict[str, str] = {}
    for record in records:
        if record.student_id not in students or record.author_name:
            students[record.student_id] = record.author_name

    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["student_id", "author_name"])
        for student_id in sorted(students.keys()):
            writer.writerow([student_id, students[student_id]])


def write_mapping_csv(path: Path, records: Iterable[ProposalRecord]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Proposal_ID", "Student_ID", "Author_Name", "Proposal_Title", "Proposal_Filename"])
        for record in records:
            writer.writerow(
                [
                    record.proposal_id,
                    record.student_id,
                    record.author_name,
                    record.proposal_title,
                    record.filename,
                ]
            )


def confirm_overwrite(path: Path) -> bool:
    if not path.exists():
        return True
    response = input(f"{path} already exists. Overwrite? [y/N]: ").strip().lower()
    return response == "y"


def main() -> None:
    args = parse_args()
    pdf_files = ensure_data_dir(args.data_dir)
    metadata = load_metadata(
        csv_path=args.metadata_csv,
        id_column=args.metadata_id_column,
        author_column=args.metadata_author_column,
        title_column=args.metadata_title_column,
    )
    records = build_records(
        pdf_files=pdf_files,
        student_prefix=args.student_prefix,
        proposal_prefix=args.proposal_prefix,
        start_index=args.start_index,
        metadata=metadata,
    )

    # Write students.csv
    if args.force or confirm_overwrite(args.students_file):
        write_students_csv(args.students_file, records)
        print(f"✓ Wrote {args.students_file} ({len(set(r.student_id for r in records))} students)")
    else:
        print(f"Skipped writing {args.students_file}")

    # Write proposal_mapping.csv
    if args.force or confirm_overwrite(args.mapping_file):
        write_mapping_csv(args.mapping_file, records)
        print(f"✓ Wrote {args.mapping_file} ({len(records)} rows)")
    else:
        print(f"Skipped writing {args.mapping_file}")


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)

