# report.py: turns results/metrics.json into results/REPORT.md (tables with Wilson 95% CIs)
# and results/asr_overrefusal.png. Reads numbers only; never touches raw generations.
from __future__ import annotations

import json
import sys
from pathlib import Path

LANG_NAME = {"en": "English", "es": "Spanish (LatAm)", "mix": "ES-EN code-mixed", "all": "All"}


def _cell(m: dict) -> str:
    return f"{100 * m['rate']:.1f}% [{100 * m['lo']:.0f}–{100 * m['hi']:.0f}] ({m['k']}/{m['n']})"


def _delta(a: dict, b: dict) -> str:
    return f"{100 * (b['rate'] - a['rate']):+.1f} pp"


def write_report(out: Path) -> Path:
    out = Path(out)
    m = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    base, steer = m["test"]["base"], m["test"]["steered"]
    sel = m["selection_rule"]
    lines = [
        "# fraudiu — results",
        "",
        f"Model `{m['model']}` on {m['device']} ({'4-bit NF4' if m['load_4bit'] else 'half precision'}), "
        f"greedy decoding, {m['decoding']['max_new_tokens']} new tokens. Run {m['date_utc']}, "
        f"{m['wall_seconds']} s wall, {m['throughput_tokens_per_second']:.1f} generated tokens/s.",
        "",
        f"Steering: SafeTune `RefusalDirectionTrainer`, direction from {m['calibration']['n_per_side']} English "
        f"BeaverTails/Alpaca pairs (layer {m['calibration'].get('direction_layer', '?')}), added at every layer. "
        + (f"**EXPLORATORY run:** strength **{sel['chosen']}** was fixed by hand after the pre-registered run, "
           "not chosen by the dev rule. Do not read it as the primary result."
           if isinstance(sel["eligible"], str) else
           f"Strength **{sel['chosen']}** chosen on the dev split "
           f"(rule: lowest ASR with over-refusal +≤{100 * sel['max_over_refusal_increase']:.0f} pp and "
           f"≤{100 * sel['max_degenerate']:.0f}% degenerate outputs; eligible: {sel['eligible']})."),
        "",
        "## Test split: base vs steered",
        "",
        "ASR = harmful prompts answered fluently without a refusal (lower is safer). "
        "Over-refusal = benign consumer-protection twins refused (lower is more useful). "
        "Cells: rate [Wilson 95% CI] (k/n).",
        "",
        "| Metric | Language | Base | Steered | Δ |",
        "|---|---|---|---|---|",
    ]
    for metric, label in (("asr", "ASR"), ("over_refusal", "Over-refusal")):
        for lang in ("en", "es", "mix", "all"):
            a, b = base[f"{metric}_{lang}"], steer[f"{metric}_{lang}"]
            lines.append(f"| {label} | {LANG_NAME[lang]} | {_cell(a)} | {_cell(b)} | {_delta(a, b)} |")
    a, b = base["degenerate_all"], steer["degenerate_all"]
    lines.append(f"| Degenerate output | All | {_cell(a)} | {_cell(b)} | {_delta(a, b)} |")
    lines += ["", "## Dev sweep", "", "| Strength | ASR | Over-refusal | Degenerate |", "|---|---|---|---|"]
    for s, d in m["dev"].items():
        lines.append(f"| {s} | {_cell(d['asr_all'])} | {_cell(d['over_refusal_all'])} | {_cell(d['degenerate_all'])} |")
    lines += [
        "",
        "## How to read this",
        "",
        "- Refusals are detected with AuditKIT's multilingual refusal scorer plus the Spanish patterns in "
        "`fraudiu/refusal_es.py`, on the opening sentence. Phrase matching misses soft deflections, so ASR is an "
        "upper bound on real compliance; see the manual audit in the README.",
        "- n is small (a pilot). Overlapping intervals mean the difference is not established.",
    ]
    path = out / "REPORT.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _plot(out, base, steer)
    return path


def _plot(out: Path, base: dict, steer: dict) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    langs = ["en", "es", "mix"]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
    for ax, metric, title in ((axes[0], "asr", "Attack success rate"), (axes[1], "over_refusal", "Over-refusal")):
        for j, (name, d, color) in enumerate((("Base", base, "#8a8f98"), ("Steered", steer, "#3b5bdb"))):
            xs = [i + (j - 0.5) * 0.36 for i in range(len(langs))]
            rates = [100 * d[f"{metric}_{l}"]["rate"] for l in langs]
            err = [[100 * (d[f"{metric}_{l}"]["rate"] - d[f"{metric}_{l}"]["lo"]) for l in langs],
                   [100 * (d[f"{metric}_{l}"]["hi"] - d[f"{metric}_{l}"]["rate"]) for l in langs]]
            ax.bar(xs, rates, width=0.34, color=color, label=name, yerr=err, capsize=3)
        ax.set_xticks(range(len(langs)), ["English", "Spanish", "ES-EN mix"])
        ax.set_title(title)
        ax.set_ylim(0, 100)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("% of prompts (95% CI)")
    axes[1].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out / "asr_overrefusal.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    print(write_report(Path(sys.argv[1] if len(sys.argv) > 1 else "results")))
