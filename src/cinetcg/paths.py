from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Paths:
    repo_root: Path
    data_dir: Path
    schema_dir: Path
    assets_dir: Path
    userdata_dir: Path


def get_paths() -> Paths:
    # src/cinetcg/paths.py -> parents: [cinetcg, src, repo_root]
    repo_root = Path(__file__).resolve().parents[2]
    data_dir = repo_root / "src" / "cinetcg" / "data"
    schema_dir = data_dir / "schemas"
    assets_dir = repo_root / "assets"
    userdata_dir = repo_root / "userdata"
    return Paths(
        repo_root=repo_root,
        data_dir=data_dir,
        schema_dir=schema_dir,
        assets_dir=assets_dir,
        userdata_dir=userdata_dir,
    )
