"""Free local PDF text extraction using Poppler's pdftotext.

This backend is intentionally conservative: it is suitable for born-digital,
text-searchable PDFs, but it does not claim to OCR scanned image-only pages.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from src.ocr.common import (
    ensure_ocr_columns,
    load_ocr_input_dataframe,
    persist_ocr_output,
    resolve_pdf_path,
)
from src.screening.common import emit_log, save_csv


MODEL_NAME = "poppler-pdftotext-layout"
MIN_TEXT_CHARS = 500


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _candidate_binaries(configured: str | None) -> list[Path]:
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured).expanduser())
    discovered = shutil.which("pdftotext")
    if discovered:
        candidates.append(Path(discovered))
    candidates.extend(
        [
            Path.home()
            / ".cache/codex-runtimes/codex-primary-runtime/dependencies/native/"
            "poppler/poppler/bin/pdftotext",
            Path("/opt/homebrew/bin/pdftotext"),
            Path("/usr/local/bin/pdftotext"),
            Path("/usr/bin/pdftotext"),
        ]
    )
    return candidates


def resolve_pdftotext(configured: str | None = None) -> Path:
    for candidate in _candidate_binaries(configured):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()
    raise RuntimeError(
        "pdftotext was not found. Install Poppler or pass --poppler-pdftotext-bin."
    )


def _plain_text_to_markdown(text: str) -> tuple[str, int]:
    raw_pages = text.replace("\r\n", "\n").replace("\r", "\n").split("\f")
    pages = [page.strip() for page in raw_pages]
    while pages and not pages[-1]:
        pages.pop()
    markdown_pages = []
    for page_number, page in enumerate(pages, start=1):
        page = "\n".join(line.rstrip() for line in page.splitlines()).strip()
        markdown_pages.append(f"<!-- PAGE {page_number} -->\n\n{page}")
    return "\n\n---\n\n".join(markdown_pages), len(pages)


def process_pdf(
    pdftotext_bin: Path,
    pdf_path: Path,
    markdown_dir: Path,
    skip_existing: bool = True,
) -> dict:
    started = time.perf_counter()
    md_file = markdown_dir / f"{pdf_path.stem}.md"
    if skip_existing and md_file.exists():
        content = md_file.read_text(encoding="utf-8", errors="ignore")
        return {
            "status": "skipped",
            "full_markdown": content,
            "markdown_file": str(md_file.resolve()),
            "num_pages": content.count("\n\n---\n\n") + (1 if content else 0),
            "elapsed_seconds": time.perf_counter() - started,
        }

    result = subprocess.run(
        [str(pdftotext_bin), "-enc", "UTF-8", "-layout", str(pdf_path), "-"],
        capture_output=True,
        timeout=180,
    )
    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        return {
            "status": "error",
            "error": error or f"pdftotext exited with {result.returncode}",
            "elapsed_seconds": time.perf_counter() - started,
        }

    text = result.stdout.decode("utf-8", errors="replace")
    markdown, page_count = _plain_text_to_markdown(text)
    visible_chars = len("".join(markdown.split()))
    if visible_chars < MIN_TEXT_CHARS:
        return {
            "status": "error",
            "error": (
                f"Only {visible_chars} non-whitespace characters were extracted; "
                "use GLM, Paddle or Mistral OCR for a scanned PDF."
            ),
            "num_pages": page_count,
            "elapsed_seconds": time.perf_counter() - started,
        }

    md_file.write_text(markdown, encoding="utf-8")
    return {
        "status": "success",
        "full_markdown": markdown,
        "markdown_file": str(md_file.resolve()),
        "num_pages": page_count,
        "elapsed_seconds": time.perf_counter() - started,
    }


def run_ocr(config, logger=None) -> int:
    pdftotext_bin = resolve_pdftotext(
        getattr(config, "poppler_pdftotext_bin", None)
    )
    input_path, dataframe, pdf_path_column = load_ocr_input_dataframe(config, logger)
    dataframe = ensure_ocr_columns(dataframe, "poppler", MODEL_NAME)
    markdown_dir = Path(config.ocr_markdown_dir)
    markdown_dir.mkdir(parents=True, exist_ok=True)

    tasks = []
    for idx, row in dataframe.iterrows():
        pdf_path = resolve_pdf_path(row[pdf_path_column], config, input_path)
        if not pdf_path.exists():
            dataframe.at[idx, "ocr_status"] = "error"
            dataframe.at[idx, "ocr_error"] = f"PDF not found: {pdf_path}"
            dataframe.at[idx, "ocr_processed_at"] = _utc_now_iso()
            continue
        tasks.append((idx, pdf_path))

    emit_log(logger, "info", f"Running free Poppler extraction on {len(tasks)} PDFs")
    emit_log(logger, "info", f"pdftotext binary: {pdftotext_bin}")
    emit_log(logger, "info", f"Markdown directory: {markdown_dir}")

    success_count = 0
    skip_count = 0
    error_count = int((dataframe["ocr_status"] == "error").sum())
    workers = max(1, int(config.ocr_workers))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                process_pdf,
                pdftotext_bin,
                pdf_path,
                markdown_dir,
                getattr(config, "ocr_skip_existing", True),
            ): (idx, pdf_path)
            for idx, pdf_path in tasks
        }
        for counter, future in enumerate(as_completed(futures), start=1):
            idx, pdf_path = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {"status": "error", "error": str(exc)}
            status = result.get("status", "error")
            dataframe.at[idx, "ocr_status"] = status
            dataframe.at[idx, "ocr_model_name"] = MODEL_NAME
            dataframe.at[idx, "ocr_processed_at"] = _utc_now_iso()
            dataframe.at[idx, "ocr_elapsed_seconds"] = result.get("elapsed_seconds")
            dataframe.at[idx, "ocr_num_pages"] = result.get("num_pages")
            if status in {"success", "skipped"}:
                dataframe.at[idx, "markdown_content"] = result.get("full_markdown", "")
                dataframe.at[idx, "markdown_path"] = result.get("markdown_file", "")
                dataframe.at[idx, "ocr_error"] = None
                if status == "success":
                    success_count += 1
                else:
                    skip_count += 1
                message = (
                    f"[{counter}/{len(tasks)}] {status.upper()} {pdf_path.stem}: "
                    f"pages={result.get('num_pages', 0)}"
                )
            else:
                dataframe.at[idx, "ocr_error"] = result.get("error", "unknown error")
                error_count += 1
                message = f"[{counter}/{len(tasks)}] ERROR {pdf_path.stem}: {dataframe.at[idx, 'ocr_error']}"
            save_csv(dataframe, config.articles_with_markdown_path)
            emit_log(logger, "info", message)

    persist_ocr_output(dataframe, config, logger)
    emit_log(
        logger,
        "info",
        (
            f"Poppler extraction complete: total={len(dataframe)} "
            f"success={success_count} skipped={skip_count} errors={error_count}"
        ),
    )
    return 1 if error_count else 0

