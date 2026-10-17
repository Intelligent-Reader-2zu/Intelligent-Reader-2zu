# Candidate PDF Smoke Test Results

> Date: 2026-09-24
>
> Samples: project-authored `SELF-001` through `SELF-004`
>
> Status: integration smoke tests only; not an accuracy acceptance or final selection

## 1. Environment

| Item | Version/status |
|---|---|
| Windows | Windows 11 x64 |
| Python | 3.13.2 |
| pdfplumber | 0.11.10 |
| Docling | 2.130.0 |
| Unstructured | 0.27.8 |
| unstructured-inference | 1.6.13 |
| Tesseract | 5.5.3.20260724, installed via Scoop |
| Tesseract languages | `eng`, `chi_sim` from `tessdata_fast` |
| Dependency health | `pip check`: no broken requirements |

The isolated Python environment is `.venv-parser/` and is ignored by Git. Direct package pins are listed in `requirements-candidates.txt`. It is a large environment because Docling and Unstructured pull PyTorch, ONNX/OpenCV, SciPy, RapidOCR and layout dependencies. It is local-only; no cloud parser API or user account was used.

## 2. Results

### pdfplumber 0.11.10 (`fast` text extraction)

- All four PDFs completed.
- `SELF-001` and `SELF-003` returned one page; `SELF-002` returned two pages; all exposed character/word geometry and physical page numbers.
- The library found a table candidate in each text PDF, but candidate detection is not table-cell accuracy.
- `SELF-004` returned two image-only pages, no text layer and no OCR.
- The dual-column PDF text is extractable, but this smoke test did not score reading order against token-level reference labels.

Raw summaries: `results/candidate-pdf/pdfplumber-*.json` and `pdfplumber-summary.json`.

### Docling 2.130.0 (default local pipeline)

- All four PDFs completed once the child process used ASCII-only temporary/cache paths. Without this, native `docling-parse` failed with `Illegal byte sequence`, even when the input PDF itself was copied to an ASCII path.
- `SELF-001` through `SELF-003` returned page counts, structured text elements and one table each.
- `SELF-004` returned two pages and OCR-derived Chinese/English text. The sample's table was not reported as a table (`table_count=0`). OCR correctness/character error rate was not scored in this smoke test.
- `SELF-002` output includes visible column/word-order issues (for example split fragments in table cells and spacing within words); this is a concrete case for manual ordering and table metrics, not evidence that all dual-column documents fail.
- First model-backed conversion was slow on this machine: about 15-28 seconds for text PDFs and about 64 seconds for the two-page scanned sample in the recorded run. These timings are environment-specific.

Complete raw Docling JSON is saved as `results/candidate-pdf/SELF-*.docling.json`; summary records are `docling-*.json` and `docling-summary.json`.

### Unstructured 0.27.8 (`fast`)

- All four PDFs completed after installing `unstructured-inference`.
- Text PDFs returned typed elements (`Title`, `NarrativeText`, `Footer`, etc.) and physical page metadata.
- The table/measurement sample mostly emitted text elements rather than a structured table in this strategy.
- The scanned sample returned page-break elements and no recognized text. This strategy did not run OCR.

### Unstructured 0.27.8 (`hi_res` / `ocr_only`)

- Initial runs failed before OCR because Tesseract was not installed. Tesseract 5.5.3 and `eng`/`chi_sim` trained data were then installed locally; no account was needed.
- With OCR available, `hi_res` reached Tesseract but failed on both the dual-column and scanned samples in `unstructured.partition.pdf_image.ocr`: Tesseract emitted Chinese hOCR bytes without a compatible UTF-8 declaration, and lxml rejected them as `XMLSyntaxError`.
- `ocr_only` on `SELF-004` failed with the same XML encoding error. Explicit UTF-8 environment settings and `languages=['chi_sim','eng']` reproduced the same failure. Current recorded result therefore remains a failure for this Windows dependency combination. The raw failure is retained; it is not counted as a parser quality score.

Result files: `results/candidate-pdf/unstructured-hi_res-*.json`, `unstructured-hi_res-summary.json`, and `unstructured-ocr_only-summary.json`.

## 3. Interpretation and boundary

- The smoke tests prove that Java/Python experiment setup can install, invoke and record these local candidates; they do not yet establish production fitness.
- Docling's scan OCR produced content, but measured CER/WER, confidence calibration, layout order and page/bbox citation accuracy remain pending.
- Unstructured's `fast` strategy is useful for text-layer extraction and element categorization; scanned-PDF OCR was not completed by that strategy.
- Unstructured `hi_res` is currently blocked by an encoding incompatibility in the installed Windows/Tesseract path; do not describe it as tested successfully for Chinese OCR.
- pdfplumber does not OCR. For scanned documents it should remain an explicit baseline/failure comparison.
- No sample was sent to any hosted API.

## 4. Repeat commands

Install the Python candidates into the isolated environment:

```powershell
python -m venv .venv-parser
.\.venv-parser\Scripts\python.exe -m pip install -r requirements-candidates.txt
```

Run pdfplumber or Unstructured fast:

```powershell
.\.venv-parser\Scripts\python.exe scripts\run_candidate_pdf.py --parser pdfplumber
.\.venv-parser\Scripts\python.exe scripts\run_candidate_pdf.py --parser unstructured --strategy fast
```

On this machine, run Docling with ASCII-only paths for process temp and model cache:

```powershell
$env:PYTHONUTF8 = '1'
$env:TMP = 'D:\docling-cache\tmp'
$env:TEMP = 'D:\docling-cache\tmp'
$env:APPDATA = 'D:\docling-cache\appdata'
$env:LOCALAPPDATA = 'D:\docling-cache\localappdata'
$env:XDG_CACHE_HOME = 'D:\docling-cache'
$env:HF_HOME = 'D:\docling-cache\hf'
.\.venv-parser\Scripts\python.exe scripts\run_candidate_pdf.py --parser docling
```

Unstructured `hi_res` currently reproduces the recorded failure on this machine:

```powershell
.\.venv-parser\Scripts\python.exe scripts\run_candidate_pdf.py --parser unstructured --strategy hi_res --sample SELF-002 --sample SELF-004
```

The isolated environment plus downloaded model cache is approximately 0.5 GB so far; future model downloads may increase it. Exact size is machine- and cache-dependent.
