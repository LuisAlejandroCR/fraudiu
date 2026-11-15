# publish.py: pushes the artifacts the submission form asks for to Hugging Face — a gated
# dataset with the prompts, a model repo with the steering vector and results, and one
# model collection plus one dataset collection. Raw generations are never uploaded.
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from .data import load_rows, to_records

ROOT = Path(__file__).resolve().parent.parent
BASE_MODEL = "CohereLabs/tiny-aya-global"


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser(description="Publish fraudiu artifacts to Hugging Face")
    ap.add_argument("--results", default="results")
    ap.add_argument("--dataset-name", default="fraudiu-latam-fraud-safety")
    ap.add_argument("--model-name", default="fraudiu-tiny-aya-refusal-steering")
    ap.add_argument("--github", default="", help="public GitHub URL, linked from both cards")
    ap.add_argument("--stage", choices=["dataset", "results", "all"], default="all",
                    help="dataset: upload the gated prompts (before running in Colab); "
                         "results: steering vector, metrics and collections (after the run)")
    args = ap.parse_args(argv)

    from huggingface_hub import HfApi

    api = HfApi()
    user = api.whoami()["name"]
    ds_id, model_id = f"{user}/{args.dataset_name}", f"{user}/{args.model_name}"
    results = Path(args.results)
    if args.stage in ("dataset", "all"):
        publish_dataset(api, ds_id, args.github)
    if args.stage == "dataset":
        print(f"https://huggingface.co/datasets/{ds_id}")
        return {"dataset": f"https://huggingface.co/datasets/{ds_id}"}
    if not (results / "metrics.json").exists():
        raise SystemExit(f"{results / 'metrics.json'} not found: run `python -m fraudiu.run` first")
    return publish_results(api, user, ds_id, model_id, results, args.github)


def publish_dataset(api, ds_id: str, github: str) -> None:
    """Prompts only, gated, plus CuratorKIT's manifest/provenance/checksums per group."""
    if not (ROOT / "data" / "intents.jsonl").exists():
        raise SystemExit("data/intents.jsonl is not here: the dataset stage runs on the author's machine")
    api.create_repo(ds_id, repo_type="dataset", exist_ok=True)
    # Gate first, so the prompts are never public even for a moment.
    try:
        api.update_repo_settings(ds_id, repo_type="dataset", gated="auto")
    except Exception as e:
        raise SystemExit(f"could not gate {ds_id} ({e}); not uploading prompts to an open repo")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        with open(tmp / "prompts.jsonl", "w", encoding="utf-8") as f:
            for rec in to_records(load_rows()):
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        (tmp / "intents.jsonl").write_bytes((ROOT / "data" / "intents.jsonl").read_bytes())
        card = (ROOT / "cards" / "DATASET_CARD.md").read_text(encoding="utf-8")
        (tmp / "README.md").write_text(card.replace("{{GITHUB}}", github or "see the model repo"),
                                       encoding="utf-8")
        curated = ROOT / "data" / "curated"
        for group in sorted(p for p in curated.glob("*") if p.is_dir()):
            for name in ("manifest.json", "lexsi_provenance.json", "checksums.txt"):
                if (group / name).exists():
                    dst = tmp / "curation" / group.name
                    dst.mkdir(parents=True, exist_ok=True)
                    (dst / name).write_bytes((group / name).read_bytes())
        summary = ROOT / "results" / "curation.json"
        if summary.exists():
            (tmp / "curation").mkdir(exist_ok=True)
            (tmp / "curation" / "summary.json").write_bytes(summary.read_bytes())
        api.upload_folder(repo_id=ds_id, repo_type="dataset", folder_path=str(tmp),
                          commit_message="Upload fraudiu prompts, card and CuratorKIT provenance")


def publish_results(api, user: str, ds_id: str, model_id: str, results: Path, github: str) -> dict:
    """Steering vector + metrics + per-item labels (no text) + the two collections."""
    api.create_repo(model_id, repo_type="model", exist_ok=True)
    m = json.loads((results / "metrics.json").read_text(encoding="utf-8"))
    card = (ROOT / "cards" / "MODEL_CARD.md").read_text(encoding="utf-8")
    report = (results / "REPORT.md").read_text(encoding="utf-8")
    card = (card.replace("{{REPORT}}", report).replace("{{DATASET}}", ds_id)
            .replace("{{GITHUB}}", github or "")
            .replace("{{STRENGTH}}", str(m["selection_rule"]["chosen"])))
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "README.md").write_text(card, encoding="utf-8")
        for name in ("metrics.json", "per_item.csv", "REPORT.md", "asr_overrefusal.png", "curation.json",
                     "refusal_direction.safetensors", "refusal_direction.pt",
                     "PAIRED.md", "paired.json", "RESCORED.md", "rescored.json"):
            if (results / name).exists():
                (tmp / name).write_bytes((results / name).read_bytes())
        # Replication (v1) and exploratory runs: labels and numbers only, never private/.
        runs = ROOT / "runs"
        for d in sorted(runs.glob("*")) if runs.is_dir() else []:
            if not d.is_dir() or d.name.startswith("v2"):
                continue
            for name in ("metrics.json", "per_item.csv", "REPORT.md", "PAIRED.md", "paired.json",
                         "RESCORED.md", "rescored.json", "asr_overrefusal.png"):
                if (d / name).exists():
                    (tmp / "runs" / d.name).mkdir(parents=True, exist_ok=True)
                    (tmp / "runs" / d.name / name).write_bytes((d / name).read_bytes())
        (tmp / "steering_config.json").write_text(json.dumps({
            "base_model": m["model"], "method": "safetune RefusalDirectionModel mode=steer",
            "layers": "all", "strength": m["selection_rule"]["chosen"],
            "direction_file": "refusal_direction.safetensors"}, indent=2), encoding="utf-8")
        api.upload_folder(repo_id=model_id, folder_path=str(tmp),
                          commit_message="Upload steering vector, metrics and report")

    # ---- collections (the form asks for one of models and one of datasets)
    title = "fraudiu: LatAm Spanish fraud safety for Tiny Aya"
    mc = api.create_collection(title=f"{title} (models)", namespace=user, exists_ok=True,
                               description="Steering vector and results for Tiny Aya Global")
    for item in (model_id, BASE_MODEL):
        api.add_collection_item(mc.slug, item_id=item, item_type="model", exists_ok=True)
    dc = api.create_collection(title=f"{title} (datasets)", namespace=user, exists_ok=True,
                               description="Gated prompts: fraud requests and benign twins in EN/ES/ES-EN")
    api.add_collection_item(dc.slug, item_id=ds_id, item_type="dataset", exists_ok=True)

    links = {
        "dataset": f"https://huggingface.co/datasets/{ds_id}",
        "model": f"https://huggingface.co/{model_id}",
        "model_collection": f"https://huggingface.co/collections/{mc.slug}",
        "dataset_collection": f"https://huggingface.co/collections/{dc.slug}",
    }
    print(json.dumps(links, indent=2))
    (results / "hf_links.json").write_text(json.dumps(links, indent=2), encoding="utf-8")
    return links


if __name__ == "__main__":
    main()
