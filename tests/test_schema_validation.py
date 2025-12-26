from __future__ import annotations

from cinetcg.paths import get_paths
from cinetcg.services.content import ContentService


def test_content_schemas_validate() -> None:
    paths = get_paths()
    content = ContentService(paths.data_dir, paths.schema_dir)
    content.validate_all()
