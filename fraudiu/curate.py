# curate.py: the CuratorKIT stage. Runs each (kind, language) group of prompts through
# CuratorKIT's schema gate, exact + MinHash near-duplicate removal and text cleaning, and
# records which prompts survive. run.py evaluates only the survivors.
from __future__ import annotations

import json

from .data import KINDS, LANGS, ROOT, load_rows

CURATED = ROOT / "data" / "curated"
SUMMARY = ROOT / "results" / "curation.json"


def curate(threshold: float = 0.85) -> dict:
    """Groups are curated separately: a benign twin is meant to resemble its harmful prompt,
    and the Spanish and code-mixed versions of one intent share words on purpose."""
    from curatorkit import Curator, CuratorConfig

    rows = load_rows()
    CURATED.mkdir(parents=True, exist_ok=True)
    summary: dict = {"tool": "curatorkit", "dedup": "exact+minhash", "minhash_threshold": threshold,
                     "clean": True, "groups": {}, "kept_uids": []}
    for kind in KINDS:
        for lang in LANGS:
            group = [r for r in rows if r.kind == kind and r.lang == lang]
            name = f"{kind}_{lang}"
            src = CURATED / f"{name}.input.jsonl"
            src.write_text("\n".join(json.dumps({"text": r.prompt, "uid": r.uid}, ensure_ascii=False)
                                     for r in group) + "\n", encoding="utf-8")
            res = Curator(CuratorConfig(
                dataset=str(src), dedup="minhash", minhash_threshold=threshold, clean=True,
                min_tokens=3, output_dir=str(CURATED / name), export_formats=["corpus"],
                name=f"fraudiu_{name}", write_hf_readme=False,
            )).run()
            kept = sorted(s.metadata["uid"] for s in res.passed)
            dropped = sorted({r.uid for r in group} - set(kept))
            summary["groups"][name] = {"input": len(group), "kept": len(kept), "dropped": dropped,
                                       "stage_counts": res.stage_counts}
            summary["kept_uids"] += kept
            print(f"{name}: {len(group)} -> {len(kept)} kept, dropped {dropped}")
    summary["kept_uids"].sort()
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def kept_uids() -> set[str] | None:
    """The survivors of the last curation run, or None if curate() was never run."""
    if not SUMMARY.exists():
        return None
    return set(json.loads(SUMMARY.read_text(encoding="utf-8"))["kept_uids"])


if __name__ == "__main__":
    curate()
