# src/extraction/common.py
from __future__ import annotations

import base64
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Any, Callable, TypeVar

import pandas as pd
from tqdm import tqdm

from src.screening.common import apply_sample
from src.ocr.common import get_pdf_path_column, resolve_pdf_path

T = TypeVar("T")
R = TypeVar("R")


def _emit_log(logger: Any, level: str, message: str) -> None:
    if logger is not None and hasattr(logger, level):
        getattr(logger, level)(message)


def _ensure_article_id(dataframe: pd.DataFrame) -> pd.DataFrame:
    if "article_id" in dataframe.columns:
        dataframe["article_id"] = dataframe["article_id"].astype(str)
        return dataframe

    if "covidence_id" in dataframe.columns:
        dataframe["article_id"] = dataframe["covidence_id"].astype(str)
        return dataframe

    dataframe = dataframe.reset_index(drop=False).rename(columns={"index": "article_id"})
    dataframe["article_id"] = dataframe["article_id"].astype(str)
    return dataframe


def load_extraction_input_dataframe(config, logger: Any = None) -> pd.DataFrame:
    input_path = Path(config.fulltext_screening_path)
    dataframe = pd.read_csv(input_path)

    if getattr(config, "perg_subset", False):
        if "perg_fulltext_result" not in dataframe.columns:
            raise ValueError(
                "--perg-subset requires 'perg_fulltext_result' in the fulltext screening output."
            )
        dataframe = dataframe[
            dataframe["perg_fulltext_result"].astype(str).str.upper() == "INCLUDE"
        ].copy()
        _emit_log(
            logger,
            "info",
            f"Filtered to {len(dataframe)} articles based on PERG fulltext screening results.",
        )

    return _ensure_article_id(dataframe)


def prepare_article_fulltext_dataframe(config, logger: Any = None) -> pd.DataFrame:
    dataframe = load_extraction_input_dataframe(config, logger=logger)

    if getattr(config, "fulltext_input_mode", "markdown") == "pdf":
        pdf_path_column = get_pdf_path_column(dataframe)
        dataframe["pdf_path"] = dataframe[pdf_path_column].apply(
            lambda value: str(resolve_pdf_path(value, config, Path(config.fulltext_screening_path)))
            if pd.notna(value) and str(value).strip()
            else None
        )
        dataframe = dataframe[
            dataframe["pdf_path"].notna()
            & dataframe["pdf_path"].apply(lambda value: Path(str(value)).exists())
        ].copy()
        dataframe["fulltext"] = "PDF supplied directly to the model."
        return dataframe

    if "markdown_content" in dataframe.columns:
        dataframe = dataframe.rename(columns={"markdown_content": "fulltext"})
    elif "fulltext" not in dataframe.columns:
        raise ValueError(
            "Expected 'markdown_content' or 'fulltext' column in the fulltext screening file."
        )

    return dataframe


def apply_extraction_sample(dataframe: pd.DataFrame, config, logger: Any = None) -> pd.DataFrame:
    return apply_sample(
        dataframe,
        getattr(config, "sample_size", None),
        getattr(config, "sample_seed", 7),
        logger=logger,
        label="articles for extraction",
    )


def get_data_extraction_concurrency(config: Any) -> int:
    concurrency = int(getattr(config, "data_extraction_concurrency", 1) or 1)
    if concurrency < 1:
        raise ValueError("--data-extraction-concurrency must be at least 1.")
    return concurrency


def append_jsonl(path: str, obj: dict, lock: Lock | None = None) -> None:
    line = json.dumps(obj) + "\n"
    if lock is None:
        with open(path, "a") as handle:
            handle.write(line)
        return

    with lock:
        with open(path, "a") as handle:
            handle.write(line)


def run_with_optional_thread_pool(
    items: list[T],
    worker_fn: Callable[[T], R],
    concurrency: int,
    desc: str = "Processing articles",
):
    if concurrency <= 1 or len(items) <= 1:
        for item in tqdm(items, total=len(items), desc=desc):
            yield worker_fn(item)
        return

    with ThreadPoolExecutor(max_workers=min(concurrency, len(items))) as executor:
        futures = [executor.submit(worker_fn, item) for item in items]
        for future in tqdm(as_completed(futures), total=len(futures), desc=desc):
            yield future.result()


def get_chat_reasoning_kwargs(
    model_name: str,
    uses_tools: bool = False,
    reasoning_enabled: bool = True,
    reasoning_effort: str = "high",
) -> dict[str, str]:
    if not reasoning_enabled:
        return {}
    lowered = model_name.lower()
    if uses_tools and (lowered.startswith("gpt-5") or lowered.startswith("o")):
        return {}
    return {"reasoning_effort": reasoning_effort}


def upload_pdf_for_chat(
    client: Any,
    pdf_path: str | None,
    cache: dict[str, dict[str, str]],
) -> dict[str, str] | None:
    if not pdf_path:
        return None
    resolved = str(Path(pdf_path).expanduser().resolve())
    if resolved not in cache:
        try:
            with open(resolved, "rb") as handle:
                uploaded = client.files.create(file=handle, purpose="user_data")
            cache[resolved] = {"file_id": uploaded.id}
        except Exception:
            encoded = base64.b64encode(Path(resolved).read_bytes()).decode("ascii")
            cache[resolved] = {
                "filename": Path(resolved).name,
                "file_data": f"data:application/pdf;base64,{encoded}",
            }
    return cache[resolved]


def build_user_content(user_prompt: str, file_id: dict[str, str] | None = None):
    if not file_id:
        return user_prompt
    return [
        {"type": "file", "file": file_id},
        {"type": "text", "text": user_prompt},
    ]


def redact_file_data(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: (
                f"<redacted file_data length={len(item)}>"
                if key == "file_data" and isinstance(item, str)
                else redact_file_data(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_file_data(item) for item in value]
    return value
