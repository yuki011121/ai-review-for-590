# AI Review Automation System for Thesis Proposals

An end-to-end automation pipeline for the **Randomized Hybrid Thesis Review Process**.  
The system blends human peer feedback and AI-generated reviews, randomizes their order, and anonymizes distribution so students cannot tell the original source.

---

## Key Capabilities
- **AI review generation** — read proposal PDFs in `data/`, call GPT-4o + Llama 3.3 on Azure, and render text output as PDFs in `reviews_original/`.
- **Human review ingestion** — convert Google Sheets / CSV exports into `*_H1.pdf` and `*_H2.pdf` with matching formatting.
- **Randomization & anonymization** — build `Master_Key.csv`, remap filenames to `Review_1…Review_4`, and produce blinded packages.
- **Distribution & analysis** — zip four anonymous reviews per student for Canvas delivery; optionally analyze quiz predictions vs. ground truth sources.

---

## Repository Layout
```
ai-review-for-590/
├── data/                         # Input proposals (PDF)
├── reviews_original/             # Human + AI reviews before anonymization
├── reviews_blinded/              # Renamed reviews after randomization
├── feedback_packages/            # ZIP bundles per student
├── csv/                          # Source metadata (e.g., Google Sheets export)
├── generate_ai_reviews.py        # GPT-4o + Llama review generator
├── generate_student_and_mapping.py# Bootstrap students.csv & proposal_mapping.csv
├── process_peer_reviews_from_csv.py # Convert CSV peer reviews into PDF
├── generate_master_key.py        # Validate files + randomize Review_1..4
├── rename_and_distribute.sh      # Copy/rename per Master Key
├── create_packages.sh            # Zip blinded reviews for Canvas
├── analyze_quiz_results.py       # Optional accuracy analysis after Canvas quiz
├── students.csv                  # Student_ID → Author name (auto-filled)
├── proposal_mapping.csv          # Proposal_ID → Student_ID + filename/title
├── .env                          # Azure API endpoints/keys (not committed)
├── requirements.txt              # Python dependencies
└── Dockerfile                    # Reproducible runtime with pandoc + TeX
```

---

## Prerequisites
| Component | Notes |
| --- | --- |
| Azure OpenAI / AI Foundry | Provide GPT-4o + Llama deployments + API keys via `.env`. |
| System packages | `pandoc`, `texlive`, `zip`, etc. (auto-installed in Docker). |
| Python 3.11 | Use repo `venv/` or the Docker image. |
| Pandoc PDF engine | Included via TeX packages; ReportLab fallback inside script if pandoc unavailable. |

---

## Data Inputs
1. **Proposal PDFs** (`data/`) – any filenames are accepted.
2. **Metadata CSV** (`csv/590-F25_Thesis_Proposal_Review_Revised.csv`) – contains `Proposal ID`, `Author First Name Last Name`, `Proposal Title`.  
   Run `generate_student_and_mapping.py` to sync:
   ```bash
   ./venv/bin/python3 generate_student_and_mapping.py --start-index 1 --force
   ```
   This populates:
   - `students.csv` → `student_id,author_name`
   - `proposal_mapping.csv` → `Proposal_ID,Student_ID,Author_Name,Proposal_Title,Proposal_Filename`

3. **Human reviews** – produced via `process_peer_reviews_from_csv.py` or manually dropped into `reviews_original/` as `SXX_H1.pdf` / `SXX_H2.pdf`.

---

## Manual Workflow (local venv)
1. **Install deps**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Generate metadata from CSV + PDFs**
   ```bash
   python3 generate_student_and_mapping.py --start-index 1
   ```
   This inspects `data/` and `csv/..Revised.csv`, then writes `students.csv` and `proposal_mapping.csv`.
3. **Convert human peer reviews**
   ```bash
   python3 process_peer_reviews_from_csv.py
   ```
   - Reads the Google Sheets export in `csv/` (looks for "Reviewer: First Name Last Name" column).
   - Uses both `Proposal ID` and (if needed) proposal titles to map each review to the correct student.
   - Renders `SXX_H1.pdf` + `SXX_H2.pdf` in `reviews_original/` (uses pandoc/TeX or ReportLab fallback). If a proposal only has one peer review submission, the script duplicates it for `H2` and adds a note so the downstream pipeline still has four total reviews.
   - Automatically updates `proposal_mapping.csv` with reviewer names in `H1_Reviewer` and `H2_Reviewer` columns.
4. **Generate AI reviews**
   ```bash
   python3 generate_ai_reviews.py
   ```
   - Reads every PDF in `data/`, extracts text, prompts GPT-4o (AI1) and Llama 3.3 (AI2), writes `SXX_AI1.pdf` / `SXX_AI2.pdf`.
   - Automatically updates `proposal_mapping.csv` with AI reviewer names in `AI1_Reviewer` and `AI2_Reviewer` columns (GPT-4o and Llama-3.3-70B).
5. **Randomize + anonymize**
   ```bash
   python3 generate_master_key.py
   ./rename_and_distribute.sh
   ./create_packages.sh
   ```
   - Validates each student has H1/H2/AI1/AI2.
   - Randomizes `Review_1–Review_4`, copies into `reviews_blinded/`.
   - Populates `Reviewer_Name` column in `Master_Key.csv`: for H1/H2 files, reads reviewer names from `proposal_mapping.csv`; for AI1 files, sets to "gpt"; for AI2 files, sets to "llama".
   - Zips `feedback_packages/SXX_Feedback_Package.zip`.
6. **Distribute** – upload each ZIP to Canvas or email via `Message Students Who…`.
7. **(Optional) Quiz accuracy analysis**
   ```bash
   python3 analyze_quiz_results.py
   ```

---

## Docker Workflow
The Docker image bundles Python + pandoc + TeX + dependencies, so instructors only provide data and `.env`.

### Build locally
```bash
docker build -t ai-review .
```
> Resulting image is large (~2.5 GB) because of TeX fonts, but portable.

### Run full pipeline inside container
Starting from only `data/` + `csv/`:
```bash
docker run --rm --env-file .env -v "$(pwd):/app" ai-review bash -c "set -euo pipefail && python3 generate_student_and_mapping.py --start-index 1 --force && python3 process_peer_reviews_from_csv.py && printf 'y\n' | python3 generate_ai_reviews.py && python3 generate_master_key.py && ./rename_and_distribute.sh && ./create_packages.sh"
```
This one-liner reproduces the entire pipeline: metadata → human PDFs → AI PDFs → Master Key → rename → ZIPs. The host folders `reviews_original/`, `reviews_blinded/`, and `feedback_packages/` must already exist (empty is fine); the command overwrites `students.csv`, `proposal_mapping.csv`, and `Master_Key.csv`.

If you already have human + AI PDFs and only need the anonymization stage, mount the individual directories instead:
```bash
docker run --rm \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/reviews_original:/app/reviews_original \
  -v $(pwd)/reviews_blinded:/app/reviews_blinded \
  -v $(pwd)/feedback_packages:/app/feedback_packages \
  -v $(pwd)/students.csv:/app/students.csv \
  -v $(pwd)/proposal_mapping.csv:/app/proposal_mapping.csv \
  -v $(pwd)/Master_Key.csv:/app/Master_Key.csv \
  ai-review bash -c \
  "python3 generate_master_key.py && ./rename_and_distribute.sh && ./create_packages.sh"
```

### Run only AI generation in the container
```bash
docker run --rm \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/reviews_original:/app/reviews_original \
  ai-review python3 generate_ai_reviews.py
```

---

## Output Files
| File | Description |
| --- | --- |
| `students.csv` | `student_id,author_name` (auto-filled from metadata). |
| `proposal_mapping.csv` | Links `Proposal_ID`, `Student_ID`, names, titles, filenames. Also includes `H1_Reviewer`, `H2_Reviewer`, `AI1_Reviewer`, `AI2_Reviewer` columns that track who wrote each review. Human reviewers are automatically populated from the CSV's "Reviewer: First Name Last Name" column when running `process_peer_reviews_from_csv.py`. |
| `master_key.csv` | Randomized mapping of `Internal_Name` to public `Review_x`, including `Reviewer_Name` column. For human reviews (H1/H2), `Reviewer_Name` is read from `proposal_mapping.csv`. For AI reviews, `Reviewer_Name` is "gpt" (AI1) or "llama" (AI2). Keep confidential. |
| `reviews_blinded/SXX_Review_#.pdf` | Student-facing review files after shuffling. |
| `feedback_packages/SXX_Feedback_Package.zip` | Deliverable ZIP containing four blinded PDFs. |
| `rename_success.log` / `rename_errors.log` | Audit log for any missing files or rename issues. |

---

## Tips & Gotchas
1. **Filename discipline** — every source review must be named `SXX_{H1,H2,AI1,AI2}.pdf`. The scripts fail fast if something is missing.
2. **Master key secrecy** — do not share `Master_Key.csv` with students until the class reveals the sources.
3. **PDF text extraction** — install either `PyPDF2` (default) or `pdfplumber`. Already in `requirements`.
4. **Pandoc fallback** — if pandoc/TeX is unavailable, `generate_ai_reviews.py` will keep `.txt` versions so you can convert manually.
5. **Docker volumes** — always mount host directories; otherwise container changes disappear on exit.

---

## Troubleshooting
| Symptom | Fix |
| --- | --- |
| `Need either PyPDF2 or pdfplumber` | `pip install PyPDF2 pdfplumber` (already in requirements). |
| `rename_and_distribute.sh` says “Successfully processed: 0” | Cosmetic bug in script counter; check `rename_success.log` for actual list. |
| `zip: command not found` inside Docker | Rebuild image (Dockerfile already installs `zip`). |
| AI API errors | Double-check `.env` for `AZURE_ENDPOINT_1/2`, `AZURE_API_KEY_1/2`, `AZURE_DEPLOYMENT_1/2`. |
| Canvas quiz column names differ | Edit `analyze_quiz_results.py` to match exported CSV header names. |

---

## License
Educational / research use only. Contact the course staff before adapting for other classes.
