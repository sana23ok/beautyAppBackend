"""15120-row CSV lookup (Hair × Eye × Skin × Undertone × Torso × Body)."""

from __future__ import annotations

import csv
from pathlib import Path

from appearance_test.constants import COLOR_PALETTES

CSV_PATH = Path(__file__).resolve().parent.parent / "recommendations.csv"

_KEY_FIELDS = [
    "Hair Color",
    "Eye Color",
    "Skin Tone",
    "Under Tone",
    "Torso length",
    "Body Proportion",
]

_LOOKUP: dict[tuple[str, ...], dict[str, str]] | None = None


def _normalize(value: str) -> str:
    return (value or "").strip()


def _fallback_palette_hex(undertone: str) -> list[str]:
    u = undertone.lower()
    if u == "warm":
        return list(COLOR_PALETTES.get("Spring", {}).get("palette_hex", []))[:5]
    if u == "cool":
        return list(COLOR_PALETTES.get("Summer", {}).get("palette_hex", []))[:5]
    spring = COLOR_PALETTES.get("Spring", {}).get("palette_hex", [])
    summer = COLOR_PALETTES.get("Summer", {}).get("palette_hex", [])
    out = list(spring)[:3] + list(summer)[:2]
    return out[:5] if out else ["#E8E8E8", "#C4C4C4", "#9E9E9E", "#757575", "#616161"]


def load_lookup() -> dict[tuple[str, ...], dict[str, str]]:
    global _LOOKUP
    if _LOOKUP is not None:
        return _LOOKUP
    _LOOKUP = {}
    if not CSV_PATH.is_file():
        return _LOOKUP
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row:
                continue
            key = tuple(_normalize(row.get(k, "")) for k in _KEY_FIELDS)
            if any(not part for part in key):
                continue
            _LOOKUP[key] = {k: (v or "").strip() for k, v in row.items()}
    return _LOOKUP


def lookup_row(
    hair: str,
    eyes: str,
    skin: str,
    undertone: str,
    torso: str,
    body: str,
) -> dict[str, str] | None:
    key = (
        _normalize(hair),
        _normalize(eyes),
        _normalize(skin),
        _normalize(undertone),
        _normalize(torso),
        _normalize(body),
    )
    return load_lookup().get(key)


def split_list_field(text: str) -> list[str]:
    if not text:
        return []
    return [p.strip() for p in text.split(",") if p.strip()]


def build_api_payload(row: dict[str, str], inputs: dict[str, str]) -> dict:
    """Build JSON-serializable dict for POST /api/appearance_test/analyse/."""
    undertone = inputs["undertone"]
    palette_hex = _fallback_palette_hex(undertone)
    wheel = row.get("Recommended Clothing Color Wheel Region", "")
    season_label = row.get("Seasonal Color Type", "").strip() or undertone.title()

    best_colors = split_list_field(row.get("Recommended Clothing Colors", ""))
    avoid_colors = split_list_field(row.get("Avoid Clothing Colors", ""))

    dont_key = "Don't Exaggerate"

    summary = (
        f"{inputs['hair_color']} · {inputs['eyes_color']} · {inputs['skin_tone']} · "
        f"{undertone} · {inputs['torso_length']} · {inputs['body_proportion']}"
    )

    look_alike = (
        f"{wheel} Fabrics: {row.get('Fabric Nature', '')}. "
        f"{row.get('Do Exaggerate', '')}. {row.get(dont_key, '')}"
    ).strip()

    analysis_result = {
        "color_type": {
            "season": season_label,
            "description": wheel,
            "palette": palette_hex,
            "advice": {
                "best_colors": best_colors,
                "least_colors": avoid_colors,
            },
        },
        "body_type": {
            "shape": inputs["body_proportion"],
            "description": row.get("Recommended Fitting Style", ""),
            "advice": {
                "best_clothes": [
                    row.get("Recommended Fitting Style", ""),
                    row.get("Recommended Materials", ""),
                    row.get("Recommended Patterns", ""),
                    row.get("Recommended Jewelry Metal", ""),
                    row.get("Recommended Shoes", ""),
                    row.get("Do Exaggerate", ""),
                ],
                "avoid_clothes": [
                    row.get("Avoid Clothing Colors", ""),
                    row.get("Avoid Clothing Color Wheel Region", ""),
                    row.get(dont_key, ""),
                ],
            },
        },
    }

    extended = {
        "recommended_clothing_colors": row.get("Recommended Clothing Colors", ""),
        "avoid_clothing_colors": row.get("Avoid Clothing Colors", ""),
        "recommended_fitting_style": row.get("Recommended Fitting Style", ""),
        "recommended_materials": row.get("Recommended Materials", ""),
        "recommended_patterns": row.get("Recommended Patterns", ""),
        "recommended_jewelry_metal": row.get("Recommended Jewelry Metal", ""),
        "recommended_shoes": row.get("Recommended Shoes", ""),
        "recommended_color_wheel_region": row.get("Recommended Clothing Color Wheel Region", ""),
        "avoid_color_wheel_region": row.get("Avoid Clothing Color Wheel Region", ""),
        "fabric_nature": row.get("Fabric Nature", ""),
        "dont_exaggerate": row.get(dont_key, ""),
        "do_exaggerate": row.get("Do Exaggerate", ""),
    }

    return {
        "inputs_summary": summary,
        "analysis_result": analysis_result,
        "look_alike_style": look_alike,
        "extended_recommendations": extended,
    }
