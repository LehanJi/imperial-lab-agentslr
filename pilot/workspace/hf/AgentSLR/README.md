---
pretty_name: 'AgentSLR: Priority Pathogens Dataset'
language:
- en
viewer: true
size_categories:
- 10K<n<100K
license: cc-by-4.0
configs:
- config_name: Harvest Metadata and Screening
  default: true
  data_files:
  - split: marburg
    path: data/harvest_metadata_and_screening/marburg.parquet
  - split: ebola
    path: data/harvest_metadata_and_screening/ebola.parquet
  - split: lassa
    path: data/harvest_metadata_and_screening/lassa.parquet
  - split: sars
    path: data/harvest_metadata_and_screening/sars.parquet
  - split: zika
    path: data/harvest_metadata_and_screening/zika.parquet
  - split: mers
    path: data/harvest_metadata_and_screening/mers.parquet
  - split: nipah
    path: data/harvest_metadata_and_screening/nipah.parquet
- config_name: Parameter Extraction - Ebola
  data_files:
  - split: ebola
    path: data/parameter_extractions_ebola/ebola.parquet
- config_name: Parameter Extraction - Lassa
  data_files:
  - split: lassa
    path: data/parameter_extractions_lassa/lassa.parquet
- config_name: Parameter Extraction - SARS
  data_files:
  - split: sars
    path: data/parameter_extractions_sars/sars.parquet
- config_name: Parameter Extraction - Zika
  data_files:
  - split: zika
    path: data/parameter_extractions_zika/zika.parquet
- config_name: Transmission Model Extraction - Ebola
  data_files:
  - split: ebola
    path: data/transmission_model_extractions_ebola/ebola.parquet
- config_name: Transmission Model Extraction - Lassa
  data_files:
  - split: lassa
    path: data/transmission_model_extractions_lassa/lassa.parquet
- config_name: Transmission Model Extraction - SARS
  data_files:
  - split: sars
    path: data/transmission_model_extractions_sars/sars.parquet
- config_name: Transmission Model Extraction - Zika
  data_files:
  - split: zika
    path: data/transmission_model_extractions_zika/zika.parquet
- config_name: Outbreak Extraction - Lassa
  data_files:
  - split: lassa
    path: data/outbreak_extractions_lassa/lassa.parquet
- config_name: Outbreak Extraction - Zika
  data_files:
  - split: zika
    path: data/outbreak_extractions_zika/zika.parquet
task_categories:
- question-answering
- text-classification
- table-question-answering
tags:
- AI4Science
- Epidemiology
- Agents
- Public-Health
- Evidence-Synthesis
- Systematic-Review
---

# AgentSLR: Priority Pathogens Dataset

<p align="left">
  <a href="https://arxiv.org" style="display:inline-flex;vertical-align:top;align-items:center;gap:6px;height:38px;box-sizing:border-box;padding:0 12px;margin:0 8px 8px 0;border:1px solid #d4d4d8;border-radius:6px;text-decoration:none;color:inherit;background:#ffffff;">
    <span style="display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;line-height:1;flex:0 0 16px;">
      <img src="assets/arxiv.svg" alt="Paper" width="15" style="display:block;">
    </span>
    <strong>Paper</strong>
  </a>
  <a href="https://github.com/oxrml/AgentSLR" style="display:inline-flex;vertical-align:top;align-items:center;gap:6px;height:38px;box-sizing:border-box;padding:0 12px;margin:0 8px 8px 0;border:1px solid #d4d4d8;border-radius:6px;text-decoration:none;color:inherit;background:#ffffff;">
    <span style="display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;line-height:1;flex:0 0 16px;">
      <img src="assets/github.svg" alt="Codebase" width="15" style="display:block;">
    </span>
    <strong>Codebase</strong>
  </a>
  <a href="https://oxrml.com/agent-slr" style="display:inline-flex;vertical-align:top;align-items:center;gap:6px;height:38px;box-sizing:border-box;padding:0 12px;margin:0 8px 8px 0;border:1px solid #d4d4d8;border-radius:6px;text-decoration:none;color:inherit;background:#ffffff;">
    <span style="display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;line-height:1;flex:0 0 16px;">
      <img src="assets/website.svg" alt="Website" width="15" style="display:block;">
    </span>
    <strong>Project Website</strong>
  </a>
</p>

This dataset accompanies the paper **Evaluating AI-based Scientific Knowledge Synthesis with Epidemiological Systematic Reviews**. It provides the data component of the AgentSLR evaluation harness. This covers article metadata, human abstract and full text screening labels, and structured human data extractions for epidemiological parameters, transmission models, and outbreaks across WHO priority pathogens.

Human labels in this release come from real world reviews conducted by the Pathogen Epidemiology Review Group (PERG) at Imperial College London. These labels reflect expert review decisions rather than synthetic annotation, and they ground the evaluation of AgentSLR in operational epidemiological review workflows.

![AgentSLR overview](assets/hero.jpg)

***Figure**: Data flow through a systematic literature review: a large corpus of harvested articles is progressively filtered through abstract and full text screening to yield a relevant subset, which then undergoes structured data extraction across three output types (parameters, transmission models and outbreaks) that feed into living review generation.*

---

The released screening labels cover seven priority pathogens:

- Marburg virus
- Ebola virus
- Lassa fever
- SARS-CoV-1
- Zika virus
- MERS-CoV
- Nipah virus

This release includes `16,248` downloaded article records matched to PERG human screening labels and deduplicated by Covidence ID. It also includes `3,808` human parameter extractions, `687` human transmission model extractions and `189` human outbreak extractions.

Harvest metadata was generated on **26 January 2026 (UTC)**. The full AgentSLR workflow, covering harvesting, PDF retrieval, OCR and Markdown conversion, screening, full text processing, extraction and report generation, is available on [GitHub](https://github.com/oxrml/agentslr).

> The screening records are the matched subset for which article full texts were downloaded and converted to Markdown during the evaluation run. This release does not redistribute PDFs or OCR text.

---

## Paper Evaluation Coverage and Released Records

The table below mirrors the deduplicated review overlap summary from the paper and the released records. `AgentSLR Matched` denotes the downloaded corpus that matched with PERG labelled subset.

| Pathogen | PERG* | AgentSLR Matched |
| --- | ---: | ---: |
| <span style="color:#6aa84f;">●</span> Marburg virus | 2,593 | 801 (30.9%) |
| <span style="color:#6aa84f;">●</span> Ebola virus | 11,605 | 4,119 (35.5%) |
| <span style="color:#6aa84f;">●</span> Lassa fever | 2,131 | 667 (31.3%) |
| <span style="color:#6aa84f;">●</span> SARS-CoV-1 | 12,280 | 2,047 (16.7%) |
| <span style="color:#6aa84f;">●</span> Zika virus | 10,510 | 2,164 (20.6%) |
| <span style="color:#f1a340;">●</span> MERS-CoV | 19,656 | 5,714 (29.1%) |
| <span style="color:#f1a340;">●</span> Nipah virus | 1,458 | 736 (50.5%) |
| <span style="color:#d6604d;">●</span> Rift Valley fever virus | - | - |
| <span style="color:#d6604d;">●</span> CCHF virus | - | - |
| **Total<sup>†</sup>** | **60,233** | **16,248 (27.0%)** |

<span style="color:#6aa84f;">●</span> Published PERG review &nbsp;&nbsp; <span style="color:#f1a340;">●</span> In data extraction by PERG &nbsp;&nbsp; <span style="color:#d6604d;">●</span> Screening not yet conducted by PERG

`*` Articles post deduplication and empty abstract removal.  
`†` Excludes Rift Valley fever virus and CCHF article counts, matching the paper table.

---

## Dataset Organisation

The dataset is organised into four config types:

- **Harvest Metadata and Screening**: one config with seven pathogen splits
- **Parameter Extraction - {Pathogen}**: one config per pathogen
- **Transmission Model Extraction - {Pathogen}**: one config per pathogen
- **Outbreak Extraction - {Pathogen}**: one config per pathogen

The harvest config contains downloaded PERG matched screening rows, deduplicated by `covidence_id`. The `perg_subset` and `downloaded` columns are `True` for all released screening records. The `covidence_id` key links screened articles in the harvest table to their corresponding human extraction records.

As data extraction schemas vary by pathogen, each pathogen for which human data extraction has been concluded is published as an individual config on the Hub, covering Ebola, Lassa, SARS and Zika for parameters and transmission models, and Lassa and Zika for outbreaks.

Using `datasets`:
```python
from datasets import load_dataset

repo_id = "OxRML/AgentSLR"

marburg_harvest = load_dataset(repo_id, "Harvest Metadata and Screening", split="marburg")
ebola_parameters = load_dataset(repo_id, "Parameter Extraction - Ebola", split="ebola")
zika_models = load_dataset(repo_id, "Transmission Model Extraction - Zika")
lassa_outbreaks = load_dataset(repo_id, "Outbreak Extraction - Lassa")
```

---

## Access, Copyright and Licensing

This repository distributes structured review data, bibliographic metadata, identifiers, URLs and abstracts where present in source records. It does **not** redistribute publisher PDFs.

The legal status of underlying sources is not uniform. OpenAlex releases its data under **CC0** ([FAQ](https://docs.openalex.org/additional-help/faq)) and notes that original copyright remains with the source for PDFs ([OpenAlex PDF docs](https://docs.openalex.org/download-all-data/full-text-pdfs)). PubMed provides citations and abstracts rather than full text articles ([About PubMed](https://pubmed.ncbi.nlm.nih.gov/about/)), and NLM does not claim copyright on PubMed abstracts, though publishers or authors may retain rights in the underlying materials ([NCBI Policies](https://www.ncbi.nlm.nih.gov/home/about/policies/), [PubMed Disclaimer](https://pubmed.ncbi.nlm.nih.gov/disclaimer/)).

This release provides metadata and structured outputs only. Downstream redistribution of article text or PDFs should follow source specific rights and licences. To run the full AgentSLR pipeline, use the main codebase for PDF retrieval, OCR and Markdown conversion, full text screening and structured data extraction.

***NOTE**: This summary is provided for transparency and reproducibility and should not be treated as legal advice.*

---

## Citation

If you use the paper, dataset or codebase, please cite our paper:

```bibtex
@article{padarha2026agentslr,
  title={AgentSLR: Automating Systematic Literature Reviews in Epidemiology with Agentic AI},
  author={Padarha, Shreyansh and Kearns, Ryan Othniel and Naidoo, Tristan and Yang, Lingyi and Borchmann, {\L}ukasz and B{\l}aszczyk, Piotr and Morgenstern, Christian and McCabe, Ruth and Bhatia, Sangeeta and Torr, Philip H. and Foerster, Jakob and Hale, Scott A. and Rawson, Thomas and Cori, Anne and Semenova, Elizaveta and Mahdi, Adam},
  year={2026}
}
```

When citing our work, please also cite the `epireview` R package, which underpins the PERG manual review workflows and structured data schemas this dataset builds on:

```bibtex
@Manual{epireview2025,
  title = {epireview: Tools to update and summarise the latest pathogen data from the Pathogen Epidemiology Review Group (PERG)},
  author = {Tristan Naidoo and Rebecca Nash and Christian Morgenstern and Patrick Doohan and Ruth McCabe and Joshua Lambert and Richard Sheppard and Cosmo Santoni and Thomas Rawson and Shazia Ruybal-Pes{\'a}ntez and Juliette H Unwin and Gina Cuomo-Dannenburg and Kelly McCain and Joseph Hicks and Anne Cori and Sangeeta Bhatia},
  year = {2025},
  note = {R package version 1.4.4},
  url = {https://github.com/mrc-ide/epireview}
}
```
