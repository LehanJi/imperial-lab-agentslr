import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const repoRoot = "/Users/jilehan/Desktop/urop/AgentSLR";
const inputPath = `${repoRoot}/pilot/data/lassa_markdown_extraction_audit.json`;
const outputPath = "/Users/jilehan/Desktop/urop/lassa_markdown_extraction_audit.xlsx";
const previewPath = `${repoRoot}/pilot/data/lassa_markdown_extraction_audit_preview.png`;
const audit = JSON.parse(await fs.readFile(inputPath, "utf8"));
const rows = audit.records;

const workbook = Workbook.create();
const sheet = workbook.worksheets.add("Extraction audit");
sheet.showGridLines = false;
sheet.tabColor = "#1F4E78";

const fontName = "Arial";
const navy = "#1F4E78";
const blue = "#D9EAF7";
const line = "#D9E2F3";
const text = "#1F2937";

sheet.getRange("A1:O34").format.font = { name: fontName, size: 10, color: text };
sheet.getRange("A2").values = [["Lassa pilot Markdown extraction audit"]];
sheet.getRange("A2").format.font = { name: fontName, size: 15, bold: true, color: navy };
sheet.getRange("A3").values = [[
  "Free local Poppler extraction of 20 text-searchable PDFs. Page boundaries and approximate layout spacing are retained."
]];
sheet.getRange("A3").format.font = { name: fontName, size: 10, italic: true, color: "#4B5563" };
sheet.getRange("A3:O3").format.borders = {
  bottom: { style: "thin", color: navy },
};

const summaryLabels = [[
  "Passed", "Records", "Pages", "Words", "Numbers", "Tables"
]];
sheet.getRange("A5:F5").values = summaryLabels;
sheet.getRange("A5:F5").format = {
  fill: navy,
  font: { name: fontName, size: 10, bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  borders: { preset: "inside", style: "thin", color: "#FFFFFF" },
};
sheet.getRange("A6:F6").formulas = [[
  '=COUNTIFS(M10:M29,"PASS")',
  "=COUNTA(A10:A29)",
  "=SUM(F10:F29)",
  "=SUM(H10:H29)",
  "=SUM(I10:I29)",
  "=SUM(J10:J29)",
]];
sheet.getRange("A6:F6").format = {
  fill: blue,
  font: { name: fontName, size: 12, bold: true, color: navy },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  numberFormat: "#,##0",
  borders: { preset: "outside", style: "thin", color: navy },
};

const headers = [[
  "Sample ID",
  "Stratum",
  "Title",
  "Download source",
  "PDF pages",
  "Extracted pages",
  "Characters",
  "Words",
  "Numeric tokens",
  "Table mentions",
  "Title coverage",
  "DOI found",
  "Status",
  "Markdown file",
  "Validation note",
]];
sheet.getRange("A9:O9").values = headers;
sheet.getRange("A9:O9").format = {
  fill: navy,
  font: { name: fontName, size: 10, bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "inside", style: "thin", color: "#FFFFFF" },
};

const dataMatrix = rows.map((record) => [
  record.sample_id,
  record.stratum_code,
  record.title,
  record.download_source,
  record.pdf_pages,
  record.extracted_pages,
  record.markdown_chars,
  record.word_count,
  record.numeric_token_count,
  record.table_mentions,
  record.title_token_coverage,
  record.doi_present ? "Yes" : "No",
  record.validation_status,
  record.markdown_file,
  record.validation_note,
]);
sheet.getRange("A10:O29").values = dataMatrix;
sheet.getRange("A10:O29").format.verticalAlignment = "middle";
sheet.getRange("A10:B29").format.horizontalAlignment = "center";
sheet.getRange("D10:F29").format.horizontalAlignment = "center";
sheet.getRange("G10:J29").format.horizontalAlignment = "right";
sheet.getRange("K10:M29").format.horizontalAlignment = "center";
sheet.getRange("E10:J29").format.numberFormat = "#,##0";
sheet.getRange("K10:K29").format.numberFormat = "0.0%";
sheet.getRange("A10:O29").format.borders = {
  insideHorizontal: { style: "thin", color: line },
  bottom: { style: "thin", color: navy },
};

sheet.getRange("M10:M29").conditionalFormats.add("containsText", {
  text: "REVIEW",
  format: { fill: "#FCE8E6", font: { bold: true, color: "#B91C1C" } },
});

sheet.getRange("A31").values = [["Method"]];
sheet.getRange("B31").values = [[audit.summary.method]];
sheet.getRange("A32").values = [["Limitation"]];
sheet.getRange("B32").values = [[audit.summary.limitation]];
sheet.getRange("A33").values = [["Source"]];
sheet.getRange("B33").values = [[
  "AgentSLR pilot PDF manifest and generated articles_with_markdown.csv (2026-10-24)"
]];
sheet.getRange("A31:A33").format.font = { name: fontName, size: 10, bold: true, color: navy };
sheet.getRange("B31:O33").format.font = { name: fontName, size: 10, italic: true, color: "#4B5563" };

sheet.getRange("A1:O34").format.verticalAlignment = "middle";
sheet.getRange("A2:O2").format.rowHeight = 24;
sheet.getRange("A3:O3").format.rowHeight = 22;
sheet.getRange("A5:F6").format.rowHeight = 24;
sheet.getRange("A9:O9").format.rowHeight = 30;
sheet.getRange("A10:O29").format.rowHeight = 36;

const widths = {
  A: 12, B: 25, C: 56, D: 23, E: 11, F: 15, G: 13, H: 11,
  I: 17, J: 16, K: 14, L: 11, M: 10, N: 24, O: 46,
};
for (const [column, width] of Object.entries(widths)) {
  sheet.getRange(`${column}:${column}`).format.columnWidth = width;
}
sheet.getRange("C10:C29").format.wrapText = true;
sheet.getRange("O10:O29").format.wrapText = false;
sheet.freezePanes.freezeRows(9);
sheet.freezePanes.freezeColumns(2);

workbook.recalculate();

const inspection = await workbook.inspect({
  kind: "table",
  range: "Extraction audit!A1:O12",
  include: "values,formulas",
  tableMaxRows: 12,
  tableMaxCols: 15,
});
console.log(inspection.ndjson);

const formulaErrors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(formulaErrors.ndjson);

const preview = await workbook.render({
  sheetName: "Extraction audit",
  range: "A1:O33",
  scale: 1,
  format: "png",
});
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(JSON.stringify({ outputPath, previewPath }));
