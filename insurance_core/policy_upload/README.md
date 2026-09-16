# Policy PDF Upload & Auto-Fill

Upload an insurer policy schedule / wordings PDF → parse → auto-fill **Insurance Client** + **Insurance Policy**, with option to use an **existing client** or **create a new one**.

**Terms & Conditions**, **Claim Eligibility**, and **Exclusions** are stored on the Policy so the AI agent can compare them when a claim is filed later.

## Features

| Feature | Detail |
|---------|--------|
| Upload form | DocType **Policy Upload** – attach PDF, choose client mode |
| Existing vs new client | Select `Existing Client` (Link) or `Create New Client` (name/email/phone/DOB/address) |
| PDF parse | Extracts policy number, insured name, provider, product, sum assured, premium, frequency, dates |
| T&Cs / eligibility | Pulls large text blocks for Terms & Conditions, Claim Eligibility, Exclusions |
| Review before create | All extracted fields are editable; map Provider + Scheme masters |
| Create | One action creates Client (if new) + Insurance Policy, attaches the PDF, sets status Active |
| AI-ready fields on Policy | `terms_and_conditions`, `claim_eligibility_rules`, `policy_exclusions`, `parsed_from_pdf`, `source_policy_upload` |

## Install

```bash
# 1. DocType
mkdir -p apps/insurance_core/insurance_core/doctype/policy_upload
cp -r policy_upload/doctype/policy_upload/* \
   apps/insurance_core/insurance_core/doctype/policy_upload/

# 2. Parser
cp policy_upload/policy_pdf_parser.py \
   apps/insurance_core/insurance_core/policy_pdf_parser.py

# 3. Installer package
mkdir -p apps/insurance_core/insurance_core/policy_upload
cp policy_upload/install_policy_upload.py \
   apps/insurance_core/insurance_core/policy_upload/
cp policy_upload/__init__.py \
   apps/insurance_core/insurance_core/policy_upload/

# 4. PDF library (recommended)
bench pip install pdfplumber

# 5. Migrate + setup
bench --site <site> migrate
bench --site <site> execute insurance_core.policy_upload.install_policy_upload.setup
bench --site <site> clear-cache
```

The installer:
- Adds custom fields on **Insurance Policy**
- Creates/updates the **Client Script** with **Parse PDF** and **Create Client & Policy** buttons

## Desk workflow

1. **New → Policy Upload**
2. Attach the policy PDF
3. Choose **Client Mode**:
   - **Existing Client** → pick from Insurance Client
   - **Create New Client** → enter name (auto-filled from PDF after parse), email, phone, etc.
4. Save → **Actions → Parse PDF**
5. Review extracted fields; map **Insurance Provider** and **Insurance Scheme** (required)
6. **Actions → Create Client & Policy**
7. You are taken to the new **Insurance Policy**; PDF is on `policy_document`

## Parser notes

- Prefer **pdfplumber**; falls back to **pypdf** / **PyPDF2**
- Image-only / scanned PDFs will not yield text unless OCR is added later
- Regex patterns target common Indian schedule labels (Policy No., Sum Insured, Period of Insurance, etc.)
- Section extraction for T&Cs / Claims / Exclusions uses heading heuristics – always review before save

## Fields added to Insurance Policy

| Field | Type | Purpose |
|-------|------|---------|
| `terms_and_conditions` | Text Editor | Full policy wordings / T&Cs |
| `claim_eligibility_rules` | Text Editor | Claim conditions, timelines, documents |
| `policy_exclusions` | Text Editor | Exclusions list |
| `parsed_from_pdf` | Check | Flag that this policy came from PDF upload |
| `source_policy_upload` | Link → Policy Upload | Traceability |

These are the fields the AI claim-comparison agent should read later.

## API (whitelist)

```python
# Parse
frappe.call("insurance_core.insurance_core.doctype.policy_upload.policy_upload.parse_policy_pdf", name="PUP-2026-00001")

# Create client + policy
frappe.call("insurance_core.insurance_core.doctype.policy_upload.policy_upload.create_client_and_policy", name="PUP-2026-00001")
```

## Optional next steps

- OCR for scanned PDFs (`pdf2image` + `pytesseract` or cloud OCR)
- LLM-assisted extraction when regex confidence is low
- Auto-create Policy Coverage / Member rows from schedule tables
- Portal page for clients to upload their existing policy PDFs
