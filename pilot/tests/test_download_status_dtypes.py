from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.harvest.fetch_articles import DownloadResult, PDFDownloader, download_articles


class DownloadStatusDtypeTest(unittest.TestCase):
    def test_all_empty_status_columns_accept_string_results(self) -> None:
        frame = pd.DataFrame(
            {
                "article_id": ["TEST_1"],
                "title": ["Test article"],
                "doi": ["10.0000/example"],
                "downloaded": [False],
                "downloaded_path": [float("nan")],
                "download_attempted_at": [float("nan")],
                "download_source": [float("nan")],
                "download_error": [float("nan")],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            progress_path = Path(temp_dir) / "progress.csv"
            with patch.object(
                PDFDownloader,
                "download_pdf",
                return_value=DownloadResult(success=False, error="test failure"),
            ):
                result = download_articles(
                    dataframe=frame,
                    pdf_dir=temp_dir,
                    max_workers=1,
                    unpaywall_email="test@example.com",
                    ncbi_tool="AgentSLR-test",
                    ncbi_email="test@example.com",
                    openalex_mailto=None,
                    openalex_api_key=None,
                    progress_path=str(progress_path),
                    progress_every=1,
                )

        self.assertEqual(result.loc[0, "download_error"], "test failure")
        self.assertIsInstance(result.loc[0, "download_attempted_at"], str)
        self.assertEqual(result["download_attempted_at"].dtype, object)
        self.assertEqual(result["download_error"].dtype, object)

    def test_identifier_resolution_replaces_stale_pmcid(self) -> None:
        downloader = PDFDownloader(
            unpaywall_email="test@example.com",
            ncbi_tool="AgentSLR-test",
            ncbi_email="test@example.com",
        )
        record = {
            "pmid": "34868582",
            "pmcid": "PMC7132387",
            "doi": "10.1177/20499361211058252",
        }
        converted = {
            "pmid": "34868582",
            "pmcid": "PMC8637796",
            "doi": "10.1177/20499361211058252",
        }
        with patch.object(downloader, "_pmc_idconv", return_value=converted):
            resolved = downloader.resolve_record_identifiers(record)

        self.assertEqual(resolved["pmcid"], "PMC8637796")


if __name__ == "__main__":
    unittest.main()
