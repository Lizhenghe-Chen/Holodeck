import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict

ASSETS_DIR = "/Volumes/DoggyChen/objathor-assets/2023_09_23/assets"
JSON_DIR = "data/scenes/a_high_school_building_with_si-2026-01-23-16-22-04-038491/a_high_school_building_with_si.json"
ASSETS_DIR = "/Volumes/DoggyChen/objathor-assets/2023_09_23/assets"
OUTPUT_DIR = "/Volumes/DoggyChen/GitProjects/Gen Scene 2.0/Assets/Resources/ExportModels"
from export_model import export_asset


def collect_asset_ids(json_path: str | Path) -> Dict[str, int]:
    """Collect all assetId values from a JSON file into a dict (assetId -> count)."""
    path = Path(json_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    counter: Counter[str] = Counter()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "assetId" and isinstance(item, str):
                    counter[item] += 1
                else:
                    walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(data)
    return dict(counter)


def match_asset_id(asset_dic: Dict[str, int]) -> list[Path]:
    """Check all id from asset_ids if they are in the ASSETS_DIR."""
    assets_root = Path(ASSETS_DIR)
    existing_ids = {p.name: p for p in assets_root.iterdir() if p.is_dir()}
    matched_dirs: list[Path] = []
    for asset_id in asset_dic:
        path = existing_ids.get(asset_id)
        if path:
            print(f"Found asset ID: {asset_id} at {path}")
            matched_dirs.append(path)
    return matched_dirs


def export_matched_assets(matched_dirs: list[Path]) -> None:
    """Export matched assets (.pkl.gz) into OUTPUT_DIR."""
    for asset_dir in matched_dirs:
        asset_id = asset_dir.name
        asset_path = asset_dir / f"{asset_id}.pkl.gz"
        if asset_path.exists():
            export_asset(str(asset_path), OUTPUT_DIR)
        else:
            print(f"Missing model file: {asset_path}")


def main() -> None:
    asset_dic = collect_asset_ids(JSON_DIR)
    print(json.dumps(asset_dic, indent=2, ensure_ascii=False))
    # Check which asset IDs exist in ASSETS_DIR
    matched_dirs = match_asset_id(asset_dic)
    export_matched_assets(matched_dirs)


if __name__ == "__main__":
	
    main()
