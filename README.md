# APA 7 Reference Agent

An evidence-bounded Web app and Python CLI for extracting academic references, verifying bibliographic metadata, checking APA 7 rules, applying high-confidence corrections, and explaining every item that still needs human review.

![Python](https://img.shields.io/badge/Python-3.10%2B-315d7c)
![FastAPI](https://img.shields.io/badge/FastAPI-Web_UI-174f3a)
![License](https://img.shields.io/badge/License-MIT-936318)

## Features

- Drag-and-drop Web UI for `.pdf`, `.docx`, `.txt`, and `.md` files.
- Automatic reference-section detection and citation splitting.
- DOI-first Crossref verification with conservative title fallback.
- Deterministic APA 7 checks and field-level metadata comparison.
- Clear `verified`, `needs_review`, and `unverifiable` states.
- JSON, Markdown, and corrected plain-text exports.
- Privacy-oriented temporary upload handling.
- The original CLI remains available for batch and automation use.

The agent never silently replaces a citation found only through fuzzy title search. Only exact DOI evidence and deterministic DOI normalization qualify for automatic correction.

## Run the Web app

Python 3.10+ is required.

```bash
git clone YOUR_REPOSITORY_URL
cd apa7-reference-agent

python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -e ".[all]"

apa7-ref-web
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Interactive API documentation is available at `/api/docs`.

You can also run the server directly:

```bash
uvicorn apa7_agent.web.app:app --reload
```

## CLI

```bash
apa7-ref check examples/sample_references.txt \
  --output-dir apa7-report \
  --mailto you@example.com
```

Offline mode does not contact metadata providers:

```bash
apa7-ref check examples/sample_references.txt --offline
```

## Output

| File / field | Purpose |
|---|---|
| `report.json` | Machine-readable audit trail |
| `report.md` | Human-readable findings and reasons |
| `corrected_references.txt` | Safe corrections applied; uncertain items preserved |
| Web exports | The same three outputs generated in the browser |

## Verification policy

| Evidence | Status | Automatic action |
|---|---|---|
| DOI resolves to a Crossref record | `verified` | Normalize/rebuild supported record types |
| High-similarity title candidate | `needs_review` | Suggest only |
| No sufficiently safe match | `needs_review` | Preserve original |
| Provider disabled/unavailable or DOI absent | `unverifiable` | Preserve original and state why |

A failed Crossref lookup does not prove that a source is invalid. Crossref coverage is not universal.

## Current APA checks

- Publication year in parentheses.
- DOI expressed as `https://doi.org/...`.
- No terminal period after a DOI URL.
- Suspicious `Retrieved from` wording.
- Suspicious `Vol.`/`Volume` labels in journal references.
- Obvious missing-author pattern.
- Year/title discrepancies against matched metadata.
- APA author rendering for common Crossref journal article and book records.

## Configuration

| Environment variable | Default | Meaning |
|---|---:|---|
| `HOST` | `127.0.0.1` | Web server host |
| `PORT` | `8000` | Web server port |
| `APA7_MAX_UPLOAD_MB` | `15` | Maximum upload size |
| `APA7_CACHE_DIR` | OS temporary folder | Crossref response cache |

## Test

```bash
pip install -e ".[all,dev]"
python -m unittest discover -s tests -v
```

## Deploy

The repository includes a production-oriented `Dockerfile`:

```bash
docker build -t apa7-reference-agent .
docker run --rm -p 8000:8000 apa7-reference-agent
```

Before publishing your repository, replace `YOUR_REPOSITORY_URL` above and the GitHub link in `src/apa7_agent/web/static/index.html` with the final repository URL.

## PoC boundaries

- Scanned PDFs require OCR, which is not yet included.
- Plain-text extraction loses italics and hanging-indent information.
- Unusual multilingual reference layouts can defeat heuristic splitting.
- The current provider and formatters do not cover every source type.
- In-text citation reconciliation is not yet implemented.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the system design and roadmap.

