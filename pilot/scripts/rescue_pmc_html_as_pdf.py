#!/usr/bin/env python3
"""Create an auditable local PDF print of a PMC full-text HTML article."""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

import pandas as pd
import requests
from lxml import etree
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.harvest.common import make_session, utc_now_iso
from src.harvest.fetch_articles import generate_pdf_filename, validate_pdf_file


DEFAULT_MANIFEST = (
    ROOT
    / "pilot"
    / "workspace"
    / "agentslr"
    / "harvests"
    / "lassa"
    / "pilot_sample_downloads.csv"
)
DEFAULT_PDF_DIR = DEFAULT_MANIFEST.parent / "pilot_pdfs"


def plain_text(node) -> str:
    return " ".join(" ".join(node.itertext()).split())


def escaped(text: str) -> str:
    return html.escape(text, quote=False).replace("\u00a0", " ")


def draw_page(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.drawString(18 * mm, 11 * mm, "PMC full-text local print for AgentSLR pilot")
    canvas.drawRightString(192 * mm, 11 * mm, f"Page {document.page}")
    canvas.restoreState()


def build_pdf(article, output: Path, source_url: str) -> None:
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="PilotTitle",
            parent=styles["Title"],
            alignment=TA_CENTER,
            fontSize=16,
            leading=20,
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SourceNote",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#444444"),
            backColor=colors.HexColor("#F1F5F9"),
            borderPadding=6,
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodySmall",
            parent=styles["BodyText"],
            fontSize=8.3,
            leading=11,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableCell",
            parent=styles["BodyText"],
            fontSize=6.1,
            leading=7.2,
        )
    )

    doc = BaseDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title=(
            plain_text(article.xpath(".//article-title")[0])
            if article.xpath(".//article-title")
            else "PMC article"
        ),
        author="Local print generated from PMC full-text HTML",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="article")
    doc.addPageTemplates(PageTemplate(id="article", frames=frame, onPage=draw_page))

    story = []
    story.append(
        Paragraph(
            "This is a local print generated from the complete PMC HTML full text because "
            "the publisher PDF was not available through the automated open-access endpoints. "
            f"Source: {escaped(source_url)}",
            styles["SourceNote"],
        )
    )

    nodes = article.xpath(
        ".//article-title | .//abstract/title | .//sec/title | .//p | .//table"
    )
    seen: set[str] = set()
    for node in nodes:
        if node.xpath("ancestor::table") and node.tag != "table":
            continue
        if node.tag == "table":
            rows = []
            for tr in node.xpath(".//tr"):
                cells = [plain_text(cell) for cell in tr.xpath("./th | ./td")]
                if cells:
                    rows.append(cells)
            if not rows:
                continue
            width = max(len(row) for row in rows)
            padded = [row + [""] * (width - len(row)) for row in rows]
            table_data = [
                [Paragraph(escaped(cell), styles["TableCell"]) for cell in row]
                for row in padded
            ]
            table = Table(
                table_data,
                colWidths=[doc.width / width] * width,
                repeatRows=1,
                hAlign="LEFT",
            )
            table.setStyle(
                TableStyle(
                    [
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9CA3AF")),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 3),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            story.extend([Spacer(1, 4), table, Spacer(1, 7)])
            continue

        text = plain_text(node)
        if not text:
            continue
        key = f"{node.tag}:{text}"
        if key in seen:
            continue
        seen.add(key)
        if node.tag == "article-title":
            style = styles["PilotTitle"]
        elif node.tag == "title":
            section_depth = len(node.xpath("ancestor::sec"))
            style = styles["Heading2"] if section_depth <= 1 else styles["Heading3"]
        else:
            style = styles["BodySmall"]
        story.append(Paragraph(escaped(text), style))

    doc.build(story)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--pdf-dir", type=Path, default=DEFAULT_PDF_DIR)
    parser.add_argument("--sample-id", default="LASSA-011")
    args = parser.parse_args()

    dataframe = pd.read_csv(args.manifest)
    match = dataframe.index[dataframe["sample_id"] == args.sample_id]
    if len(match) != 1:
        raise ValueError(f"Expected one row for {args.sample_id}, found {len(match)}")
    idx = match[0]
    record = dataframe.loc[idx].to_dict()
    pmcid = str(record["pmcid"])
    source_url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
    retrieval_endpoint = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    session: requests.Session = make_session()
    response = session.get(
        retrieval_endpoint,
        params={
            "db": "pmc",
            "id": pmcid.removeprefix("PMC"),
            "rettype": "full",
            "retmode": "xml",
            "tool": "AgentSLR-pilot",
            "email": "literature-review@example.org",
        },
        timeout=(10, 45),
    )
    response.raise_for_status()
    document = etree.fromstring(response.content)
    articles = document.xpath("//*[local-name()='article']")
    if not articles:
        raise RuntimeError("PMC E-utilities response did not contain a JATS article element.")
    article = articles[0]
    article_text = plain_text(article)
    expected_title = str(record["title"])
    expected_tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", expected_title.casefold())
        if len(token) >= 4
    }
    article_folded = article_text.casefold()
    matched_tokens = {token for token in expected_tokens if token in article_folded}
    title_coverage = len(matched_tokens) / max(len(expected_tokens), 1)
    if len(article_text) < 5000 or title_coverage < 0.8:
        raise RuntimeError(
            "PMC E-utilities XML did not pass length/title validation: "
            f"characters={len(article_text)}, title_token_coverage={title_coverage:.2f}."
        )

    args.pdf_dir.mkdir(parents=True, exist_ok=True)
    output = args.pdf_dir / generate_pdf_filename(record)
    build_pdf(article, output, source_url)
    valid, error = validate_pdf_file(str(output))
    if not valid:
        output.unlink(missing_ok=True)
        raise RuntimeError(f"Generated PDF failed validation: {error}")

    dataframe.loc[idx, "downloaded"] = True
    dataframe.loc[idx, "downloaded_path"] = str(output.resolve())
    dataframe.loc[idx, "download_attempted_at"] = utc_now_iso()
    dataframe.loc[idx, "download_source"] = "PMC_HTML_Local_Print"
    dataframe.loc[idx, "download_error"] = ""
    dataframe.loc[idx, "local_print_source_url"] = source_url
    dataframe.loc[idx, "local_print_retrieval_endpoint"] = retrieval_endpoint
    dataframe.to_csv(args.manifest, index=False, lineterminator="\n")
    print(
        f"Created {output} from {source_url} via {retrieval_endpoint} "
        f"({len(article_text)} text characters)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
