#!/usr/bin/env python3
"""Pilot-specific Gemini evaluation with exponent and percentage normalisation."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

from utils.schemas import PARAMETER_CLASSES_MAPPING


IMPLEMENTED_CLASSES = {
    "seroprevalence",
    "human_delay",
    "severity",
    "mutation_rate",
    "relative_contribution",
    "reproduction_number",
}
PERCENT_CLASSES = {"seroprevalence", "severity", "relative_contribution"}


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def flatten_final(path: Path) -> pd.DataFrame:
    rows = []
    for record in load_jsonl(path):
        rows.append(
            {
                "article_id": str(record["article_id"]),
                "parameter_class": record["parameter_class"],
                "aggregated": bool(record.get("aggregated", False)),
                **record.get("extraction", {}),
            }
        )
    return pd.DataFrame(rows)


def flatten_values(path: Path) -> pd.DataFrame:
    rows = []
    for record in load_jsonl(path):
        for extraction in record.get("extraction", []):
            rows.append(
                {
                    "article_id": str(record["article_id"]),
                    "parameter_class": record["parameter_class"],
                    **extraction,
                }
            )
    return pd.DataFrame(rows)


def normalise_model_value(row: pd.Series) -> float:
    value = float(row["value"])
    if row["parameter_class"] in PERCENT_CLASSES and 0 <= value <= 1:
        return value * 100
    return value


def prepare_gold(gold_path: Path, sample_path: Path, article_ids: set[str]) -> pd.DataFrame:
    sample = pd.read_csv(sample_path)
    sample["article_id"] = sample["article_id"].astype(str)
    sample = sample[sample["article_id"].isin(article_ids)][
        ["article_id", "covidence_id", "title"]
    ]

    gold = pd.read_csv(gold_path)
    gold = gold.merge(sample, on="covidence_id", how="inner")
    gold["parameter_class_raw"] = gold["parameter_class"]
    gold["parameter_class"] = (
        gold["parameter_class"].map(PARAMETER_CLASSES_MAPPING).fillna(gold["parameter_class"])
    )
    gold = gold[gold["parameter_class"].isin(IMPLEMENTED_CLASSES)].copy()
    exponent = pd.to_numeric(gold["exponent"], errors="coerce").fillna(0)
    gold["normalised_value"] = pd.to_numeric(
        gold["parameter_value"], errors="coerce"
    ) * np.power(10.0, exponent)
    return gold


def screening_eval(screening_path: Path, gold: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    screening = pd.DataFrame(load_jsonl(screening_path))
    positives = set(zip(gold["article_id"], gold["parameter_class"]))
    screening["gold_contains_parameter"] = [
        (str(article_id), parameter_class) in positives
        for article_id, parameter_class in zip(
            screening["article_id"], screening["parameter_class"]
        )
    ]
    truth = screening["gold_contains_parameter"].astype(bool)
    pred = screening["contains_parameter"].astype(bool)
    tp = int((truth & pred).sum())
    fp = int((~truth & pred).sum())
    fn = int((truth & ~pred).sum())
    tn = int((~truth & ~pred).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return screening, {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def count_eval(final: pd.DataFrame, gold: pd.DataFrame) -> dict:
    keys = set(zip(gold.article_id, gold.parameter_class)) | set(
        zip(final.article_id, final.parameter_class)
    )
    tp = fp = fn = 0
    for article_id, parameter_class in keys:
        gold_count = int(
            ((gold.article_id == article_id) & (gold.parameter_class == parameter_class)).sum()
        )
        model_count = int(
            ((final.article_id == article_id) & (final.parameter_class == parameter_class)).sum()
        )
        tp += min(gold_count, model_count)
        fp += max(0, model_count - gold_count)
        fn += max(0, gold_count - model_count)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}


def pair_cost(gold_row: pd.Series, model_row: pd.Series) -> float:
    gold_value = float(gold_row["normalised_value"])
    model_value = float(model_row["normalised_value"])
    scale = max(abs(gold_value), 1e-12)
    cost = abs(model_value - gold_value) / scale
    gold_site = gold_row.get("genome_site")
    model_site = model_row.get("genome_site")
    if pd.notna(gold_site) and pd.notna(model_site):
        if str(gold_site).strip().lower() != str(model_site).strip().lower():
            cost += 100.0
    return cost


def numeric_eval(values: pd.DataFrame, gold: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    numeric_gold = gold[gold["normalised_value"].notna()].copy()
    numeric_model = values[pd.to_numeric(values.get("value"), errors="coerce").notna()].copy()
    numeric_model["normalised_value"] = numeric_model.apply(normalise_model_value, axis=1)

    details = []
    classes = sorted(IMPLEMENTED_CLASSES)
    for article_id, parameter_class in sorted(
        set(zip(numeric_gold.article_id, numeric_gold.parameter_class))
        | set(zip(numeric_model.article_id, numeric_model.parameter_class))
    ):
        g = numeric_gold[
            (numeric_gold.article_id == article_id)
            & (numeric_gold.parameter_class == parameter_class)
        ]
        m = numeric_model[
            (numeric_model.article_id == article_id)
            & (numeric_model.parameter_class == parameter_class)
        ]
        matched_g: set[int] = set()
        matched_m: set[int] = set()
        if len(g) and len(m):
            cost = np.array([[pair_cost(gr, mr) for _, mr in m.iterrows()] for _, gr in g.iterrows()])
            gi, mi = linear_sum_assignment(cost)
            for gpos, mpos in zip(gi, mi):
                grow = g.iloc[gpos]
                mrow = m.iloc[mpos]
                is_exact = math.isclose(
                    float(grow.normalised_value),
                    float(mrow.normalised_value),
                    rel_tol=1e-6,
                    abs_tol=1e-9,
                )
                if pd.notna(grow.get("genome_site")) and pd.notna(mrow.get("genome_site")):
                    is_exact = is_exact and str(grow.genome_site).strip().lower() == str(mrow.genome_site).strip().lower()
                details.append(
                    {
                        "article_id": article_id,
                        "parameter_class": parameter_class,
                        "gold_value": grow.normalised_value,
                        "model_value": mrow.normalised_value,
                        "gold_genome_site": grow.get("genome_site"),
                        "model_genome_site": mrow.get("genome_site"),
                        "exact_match": is_exact,
                        "status": "exact" if is_exact else "mismatch",
                    }
                )
                matched_g.add(grow.name)
                matched_m.add(mrow.name)
        for idx, grow in g.iterrows():
            if idx not in matched_g:
                details.append(
                    {
                        "article_id": article_id,
                        "parameter_class": parameter_class,
                        "gold_value": grow.normalised_value,
                        "model_value": np.nan,
                        "gold_genome_site": grow.get("genome_site"),
                        "model_genome_site": np.nan,
                        "exact_match": False,
                        "status": "missed_gold",
                    }
                )
        for idx, mrow in m.iterrows():
            if idx not in matched_m:
                details.append(
                    {
                        "article_id": article_id,
                        "parameter_class": parameter_class,
                        "gold_value": np.nan,
                        "model_value": mrow.normalised_value,
                        "gold_genome_site": np.nan,
                        "model_genome_site": mrow.get("genome_site"),
                        "exact_match": False,
                        "status": "extra_model_value",
                    }
                )

    details_df = pd.DataFrame(details)
    summaries = []
    for parameter_class in classes + ["ALL"]:
        part = details_df if parameter_class == "ALL" else details_df[details_df.parameter_class == parameter_class]
        exact = int((part.status == "exact").sum())
        mismatches = int((part.status == "mismatch").sum())
        missed = int((part.status == "missed_gold").sum())
        extras = int((part.status == "extra_model_value").sum())
        gold_n = exact + mismatches + missed
        model_n = exact + mismatches + extras
        precision = exact / model_n if model_n else 0.0
        recall = exact / gold_n if gold_n else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        summaries.append(
            {
                "parameter_class": parameter_class,
                "gold_numeric_records": gold_n,
                "model_numeric_values": model_n,
                "exact_matches": exact,
                "mismatches": mismatches,
                "missed_gold": missed,
                "extra_model_values": extras,
                "precision": precision,
                "recall": recall,
                "f1": f1,
            }
        )
    return pd.DataFrame(summaries), details_df


def pct(value: float) -> str:
    return f"{100 * value:.1f}%"


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    columns = list(df.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in df.iterrows():
        rendered = []
        for column in columns:
            value = row[column]
            rendered.append(f"{value:.3f}" if isinstance(value, (float, np.floating)) else str(value))
        lines.append("| " + " | ".join(rendered) + " |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final", type=Path, required=True)
    parser.add_argument("--values", type=Path, required=True)
    parser.add_argument("--screening", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    final = flatten_final(args.final)
    values = flatten_values(args.values)
    article_ids = set(final["article_id"].astype(str))
    gold = prepare_gold(args.gold, args.sample, article_ids)
    screening, screening_metrics = screening_eval(args.screening, gold)
    count_metrics = count_eval(final, gold)
    numeric_summary, numeric_details = numeric_eval(values, gold)

    final.to_csv(args.output_dir / "gemini_final_parameters.csv", index=False)
    values.to_csv(args.output_dir / "gemini_value_stage.csv", index=False)
    gold.to_csv(args.output_dir / "perg_gold_implemented_classes.csv", index=False)
    screening.to_csv(args.output_dir / "parameter_class_screening_comparison.csv", index=False)
    numeric_summary.to_csv(args.output_dir / "numeric_value_summary.csv", index=False)
    numeric_details.to_csv(args.output_dir / "numeric_value_matches.csv", index=False)

    overall = numeric_summary[numeric_summary.parameter_class == "ALL"].iloc[0]
    per_class_markdown = dataframe_to_markdown(
        numeric_summary[numeric_summary.parameter_class != "ALL"]
    )
    report = f"""# Gemini AgentSLR pilot evaluation

## Scope

- 10 blinded Lassa papers
- Model: `gemini-3.5-flash-lite` (free tier)
- Implemented gold-relevant classes: seroprevalence, human delay, severity, mutation rate, relative contribution, reproduction number
- PERG risk-factor records are excluded because AgentSLR has no risk-factor extractor.

## Results

| Evaluation | Precision | Recall | F1 | Counts |
|---|---:|---:|---:|---|
| Parameter-class screening | {pct(screening_metrics['precision'])} | {pct(screening_metrics['recall'])} | {pct(screening_metrics['f1'])} | TP={screening_metrics['tp']}, FP={screening_metrics['fp']}, FN={screening_metrics['fn']}, TN={screening_metrics['tn']} |
| Final parameter-record count | {pct(count_metrics['precision'])} | {pct(count_metrics['recall'])} | {pct(count_metrics['f1'])} | TP={count_metrics['tp']}, FP={count_metrics['fp']}, FN={count_metrics['fn']} |
| Strict exact numeric values | {pct(overall.precision)} | {pct(overall.recall)} | {pct(overall.f1)} | exact={int(overall.exact_matches)}, gold={int(overall.gold_numeric_records)}, model={int(overall.model_numeric_values)} |

The strict numeric comparison applies PERG's exponent column and converts model proportions to percentages before matching. It still penalises every additional model value as a false positive. PERG is a curated extraction set rather than an exhaustive list of every number appearing in each paper, so `extra_model_value` rows require manual review before being labelled hallucinations.

## Per-class strict numeric results

{per_class_markdown}
"""
    (args.output_dir / "GEMINI_EVALUATION.md").write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
