"""Strict YAML validation for GitHub Actions workflows.

PyYAML's default SafeLoader silently accepts duplicate mapping keys. GitHub
Actions rejects them, so this loader fails fast with the duplicate key and line.
"""
from __future__ import annotations

from pathlib import Path
import sys

import yaml


class UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader variant that rejects duplicate keys at every mapping level."""

    def construct_mapping(self, node, deep=False):
        if not isinstance(node, yaml.MappingNode):
            raise yaml.constructor.ConstructorError(
                None, None, f"expected a mapping node, got {node.id}", node.start_mark
            )
        self.flatten_mapping(node)
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in mapping
            except TypeError as exc:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found an unhashable mapping key",
                    key_node.start_mark,
                ) from exc
            if duplicate:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found duplicate key {key!r}",
                    key_node.start_mark,
                )
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def validate_workflows(workflow_dir: Path | None = None) -> list[Path]:
    """Parse every .yml/.yaml workflow and reject duplicate mapping keys."""
    root = workflow_dir or (Path(__file__).resolve().parents[1] / ".github" / "workflows")
    files = sorted([*root.glob("*.yml"), *root.glob("*.yaml")])
    if not files:
        raise RuntimeError(f"No workflow YAML files found in {root}")
    for path in files:
        try:
            yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
        except (OSError, yaml.YAMLError) as exc:
            raise RuntimeError(f"Invalid workflow YAML {path}: {exc}") from exc
        print(f"YAML OK (unique keys): {path}")
    return files


def main() -> int:
    try:
        validate_workflows()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
