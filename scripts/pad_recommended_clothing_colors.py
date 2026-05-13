"""Pad Recommended Clothing Colors to at least MIN_COLORS comma-separated entries per row."""
from __future__ import annotations

import csv
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = [ROOT / "recommendations_final.csv", ROOT / "recommendations.csv"]

MIN_COLORS = 6

JEWEL_5 = "Jewel Tones, Icy Blue, Lavender, Silver, Emerald"
SOFT_4 = "Soft Pinks, Plums, Teal, Neutral Beige"

# One extra color for the shared 5-color cool/jewel row, by season (color analysis conventions).
EXTRA_FOR_JEWEL_ROW: dict[str, str] = {
    "Bright Winter": "Fuchsia",
    "Clear Winter": "True Red",
    "Cool Summer": "Soft Periwinkle",
    "Deep Winter": "Black",
    "Light Summer": "Powder Blue",
    "Soft Summer": "Mauve",
    "True Summer": "Soft Rose",
    "True Winter": "True Red",
}

# Two extras for the shared 4-color soft row, by season.
EXTRA_FOR_SOFT_ROW: dict[str, list[str]] = {
    "Light Summer": ["Powder Blue", "Dusty Rose"],
    "Soft Summer": ["Dusty Blue", "Soft Sage"],
    "Soft Autumn": ["Olive", "Dusty Terracotta"],
}


def normalize(s: str) -> str:
    return " ".join((s or "").split()).strip()


def split_colors(cell: str) -> list[str]:
    return [p.strip() for p in str(cell or "").split(",") if p.strip()]


def join_colors(parts: list[str]) -> str:
    return ", ".join(parts)


def pad_cell(season: str, cell: str) -> tuple[str, bool]:
    parts = split_colors(cell)
    if len(parts) >= MIN_COLORS:
        return cell, False

    norm = normalize(cell)
    seen = {p.lower() for p in parts}

    if norm == JEWEL_5:
        extra = EXTRA_FOR_JEWEL_ROW.get(season)
        if extra and extra.lower() not in seen:
            parts.append(extra)
            seen.add(extra.lower())
    elif norm == SOFT_4:
        for extra in EXTRA_FOR_SOFT_ROW.get(season, []):
            if extra.lower() not in seen:
                parts.append(extra)
                seen.add(extra.lower())
    else:
        raise ValueError(f"Unexpected short row: season={season!r}, cell={cell!r}")

    if len(parts) < MIN_COLORS:
        raise ValueError(
            f"Still short after pad: season={season!r}, n={len(parts)}, {parts!r}"
        )

    return join_colors(parts), True


def process(path: Path) -> int:
    tmp = path.with_suffix(path.suffix + ".tmp")
    updated = 0
    with path.open(encoding="utf-8", newline="") as fin, tmp.open(
        "w", encoding="utf-8", newline=""
    ) as fout:
        reader = csv.DictReader(fin)
        if not reader.fieldnames:
            raise SystemExit(f"Empty or invalid CSV: {path}")
        writer = csv.DictWriter(fout, fieldnames=reader.fieldnames, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for row in reader:
            season = (row.get("Seasonal Color Type") or "").strip()
            col = "Recommended Clothing Colors"
            new_val, changed = pad_cell(season, row[col])
            if changed:
                row[col] = new_val
                updated += 1
            writer.writerow(row)
    shutil.move(tmp, path)
    return updated


def main() -> None:
    for path in FILES:
        n = process(path)
        print(f"{path.name}: updated {n} rows (min {MIN_COLORS} recommended colors)")


if __name__ == "__main__":
    main()
