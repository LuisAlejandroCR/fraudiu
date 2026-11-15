# data.py: loads data/intents.jsonl and expands each fraud intent into six prompts
# (harmful/benign x en/es/mix) with a fixed dev/test split. Prompts only: this module
# never stores or returns model completions.
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "intents.jsonl"
# The prompts are not in the public GitHub repo: they live in a gated Hugging Face dataset.
DATASET_NAME = "fraudiu-latam-fraud-safety"
LANGS = ("en", "es", "mix")
KINDS = ("harmful", "benign")
# AuditKIT refusal patterns are looked up by this tag; code-mixed text is checked as Spanish
# (AuditKIT always adds English on top of the tagged language).
PATTERN_LANG = {"en": "en", "es": "es", "mix": "es"}


@dataclass(frozen=True)
class Row:
    uid: str
    intent_id: int
    family: str
    region: str
    kind: str
    lang: str
    split: str
    prompt: str


def split_of(intent_id: int) -> str:
    """Every fifth intent (one per family) is dev, used only to pick the steering strength."""
    return "dev" if intent_id % 5 == 0 else "test"


def ensure_data(path: Path = DATA) -> Path:
    """Local file if present; otherwise download intents.jsonl from the gated HF dataset
    (FRAUDIU_DATASET=<user>/<name>, default <your HF user>/fraudiu-latam-fraud-safety).
    Needs `hf auth login` and approved access to the dataset."""
    if path.exists():
        return path
    from huggingface_hub import HfApi, hf_hub_download

    repo = os.environ.get("FRAUDIU_DATASET") or f"{HfApi().whoami()['name']}/{DATASET_NAME}"
    path.parent.mkdir(parents=True, exist_ok=True)
    got = hf_hub_download(repo, "intents.jsonl", repo_type="dataset", local_dir=str(path.parent))
    return Path(got)


def load_intents(path: Path = DATA) -> list[dict]:
    """The base file plus, if FRAUDIU_EXTRA_INTENTS names one, an extension file (v2)."""
    path = ensure_data(path)
    paths = [path]
    extra = os.environ.get("FRAUDIU_EXTRA_INTENTS")
    if extra and path == DATA:
        paths.append(Path(extra) if Path(extra).is_absolute() else ROOT / extra)
    intents = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            intents += [json.loads(line) for line in f if line.strip()]
    ids = [i["id"] for i in intents]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate intent ids across intent files")
    return intents


def load_rows(path: Path = DATA, split: str | None = None) -> list[Row]:
    rows = []
    for it in load_intents(path):
        for kind in KINDS:
            for lang in LANGS:
                rows.append(Row(
                    uid=f"{it['id']:02d}-{kind[0]}-{lang}",
                    intent_id=it["id"], family=it["family"], region=it["region"],
                    kind=kind, lang=lang, split=split_of(it["id"]),
                    prompt=it[f"{kind}_{lang}"],
                ))
    return [r for r in rows if split is None or r.split == split]


def to_records(rows: list[Row]) -> list[dict]:
    return [asdict(r) for r in rows]
