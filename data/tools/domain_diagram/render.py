from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def _load_spec(path: Path) -> dict:
    try:
        import yaml  # type: ignore
    except Exception:
        yaml = None

    if yaml is not None:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("domains.yml must define a mapping at the top level")
        return data
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("PyYAML is not installed and domains.yml is not valid JSON") from exc


def _normalize_entities(data: dict) -> list[dict]:
    entities = data.get("entities", [])
    if not isinstance(entities, list) or not entities:
        raise ValueError("No entities found in domains.yml")
    normalized = []
    for entry in entities:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not name:
            continue
        columns = []
        for column in entry.get("columns", []):
            if not isinstance(column, dict):
                continue
            col_name = column.get("name")
            if not col_name:
                continue
            columns.append(
                {
                    "name": str(col_name),
                    "type": str(column.get("type", "string")),
                    "pk": bool(column.get("pk")),
                    "fk": column.get("fk"),
                }
            )
        normalized.append(
            {
                "name": str(name),
                "domain": entry.get("domain"),
                "columns": columns,
            }
        )
    if not normalized:
        raise ValueError("No valid entities found in domains.yml")
    return normalized


def _normalize_relationships(data: dict) -> list[dict]:
    relationships = data.get("relationships", [])
    if not isinstance(relationships, list):
        return []
    cleaned = []
    for rel in relationships:
        if not isinstance(rel, dict):
            continue
        src = rel.get("from")
        dst = rel.get("to")
        if not src or not dst:
            continue
        cleaned.append(
            {
                "from": str(src),
                "to": str(dst),
                "label": rel.get("label"),
                "cardinality": rel.get("cardinality", "one_to_many"),
            }
        )
    return cleaned


def _entity_id(name: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in name).upper()


def _relationship_symbol(cardinality: str) -> str:
    return {
        "one_to_many": "||--o{",
        "many_to_one": "}o--||",
        "one_to_one": "||--||",
        "many_to_many": "}o--o{",
    }.get(cardinality, "||--o{")


def render_mermaid(entities: list[dict], relationships: list[dict]) -> str:
    lines = ["erDiagram"]
    entity_map = {entity["name"]: _entity_id(entity["name"]) for entity in entities}

    for entity in entities:
        entity_id = entity_map[entity["name"]]
        lines.append(f"    {entity_id} {{")
        for column in entity.get("columns", []):
            col_type = column.get("type", "string")
            col_name = column.get("name")
            if not col_name:
                continue
            flags = []
            if column.get("pk"):
                flags.append("PK")
            if column.get("fk"):
                flags.append("FK")
            flag_text = " ".join(flags)
            if flag_text:
                lines.append(f"        {col_type} {col_name} {flag_text}")
            else:
                lines.append(f"        {col_type} {col_name}")
        lines.append("    }")

    for rel in relationships:
        src_table, _, src_col = rel["from"].partition(".")
        dst_table, _, dst_col = rel["to"].partition(".")
        src_id = entity_map.get(src_table)
        dst_id = entity_map.get(dst_table)
        if not src_id or not dst_id:
            continue
        label = rel.get("label")
        if not label:
            if src_col and dst_col:
                label = f"{src_col} -> {dst_col}"
            elif src_col:
                label = src_col
        if label:
            lines.append(
                f"    {src_id} {_relationship_symbol(rel['cardinality'])} {dst_id} : {label}"
            )
        else:
            lines.append(
                f"    {src_id} {_relationship_symbol(rel['cardinality'])} {dst_id}"
            )
    return "\n".join(lines) + "\n"


def main() -> None:
    root = Path(__file__).resolve().parent
    spec_path = root / "domains.yml"
    out_path = root / "diagram.mmd"
    svg_path = root / "diagram.svg"
    data = _load_spec(spec_path)
    entities = _normalize_entities(data)
    relationships = _normalize_relationships(data)
    out_path.write_text(render_mermaid(entities, relationships), encoding="utf-8")
    print(f"Wrote {out_path}")
    mmdc = shutil.which("mmdc")
    if not mmdc:
        print("mmdc not found; install mermaid-cli to generate diagram.svg")
        return
    try:
        subprocess.run(
            [
                mmdc,
                "-i",
                str(out_path),
                "-o",
                str(svg_path),
                "--backgroundColor",
                "white",
            ],
            check=True,
        )
        print(f"Wrote {svg_path}")
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("Failed to render diagram.svg with mmdc") from exc


if __name__ == "__main__":
    main()
