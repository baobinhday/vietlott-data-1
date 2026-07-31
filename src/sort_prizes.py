"""
Script to sort prize JSONL files in data/ by draw ID in ascending order.
uv run python src/sort_prizes.py
"""

import json
from pathlib import Path
from typing import Optional

import click
from loguru import logger

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def sort_prize_file(file_path: Path) -> int:
    """
    Reads a prize JSONL file, sorts its rows by ID (numeric order),
    and overwrites the file with sorted rows.
    """
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return 0

    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                records.append(data)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error in {file_path.name} line {line_num}: {e}")

    if not records:
        logger.info(f"File {file_path.name} is empty, skipping.")
        return 0

    # Sort records by ID converting string to integer when possible for proper numeric sorting
    def get_sort_key(item: dict):
        raw_id = item.get("id", "0")
        try:
            return (0, int(raw_id))
        except (ValueError, TypeError):
            return (1, str(raw_id))

    sorted_records = sorted(records, key=get_sort_key)

    # Overwrite file with sorted records
    with open(file_path, "w", encoding="utf-8") as f:
        for item in sorted_records:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    logger.info(f"Sorted {len(sorted_records)} records in {file_path.name}.")
    return len(sorted_records)


def sort_all_prize_files():
    """
    Finds and sorts all *_prizes.jsonl files in data/ directory.
    """
    prize_files = list(DATA_DIR.glob("*_prizes.jsonl"))
    if not prize_files:
        logger.warning("No *_prizes.jsonl files found in data directory.")
        return

    for p_file in sorted(prize_files):
        sort_prize_file(p_file)


@click.command()
@click.option(
    "--file",
    "file_name",
    default=None,
    help="Specific prize file to sort (e.g. power655_prizes.jsonl). Default: sort all *_prizes.jsonl files.",
)
def main(file_name: Optional[str]):
    """
    Sort prize data JSONL files in data/ by draw ID in ascending numeric order.
    """
    if file_name:
        target_path = DATA_DIR / file_name
        sort_prize_file(target_path)
    else:
        logger.info("Sorting all prize files in data/...")
        sort_all_prize_files()


if __name__ == "__main__":
    main()
