# Copyright (c) 2026, Vivaswan Works and contributors
# License: MIT
"""
Policy PDF parser for insurance_core.

Extracts structured fields + large text blocks (T&Cs, claim eligibility, exclusions)
from typical Indian insurer policy schedule / wordings PDFs.

Dependencies (optional, graceful fallback):
  - pdfplumber  (preferred)
  - pypdf / PyPDF2
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from frappe.utils import getdate, flt


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def _extract_text(file_path: str) -> tuple[str, str]:
	"""Return (full_text, log_message)."""
	log_parts = []

	# 1. pdfplumber
	try:
		import pdfplumber

		pages = []
		with pdfplumber.open(file_path) as pdf:
			for i, page in enumerate(pdf.pages):
				t = page.extract_text() or ""
				pages.append(t)
				log_parts.append(f"pdfplumber page {i + 1}: {len(t)} chars")
		text = "\n\n".join(pages)
		if text.strip():
			return text, " | ".join(log_parts)
	except Exception as e:
		log_parts.append(f"pdfplumber failed: {e}")

	# 2. pypdf
	try:
		from pypdf import PdfReader

		reader = PdfReader(file_path)
		pages = []
		for i, page in enumerate(reader.pages):
			t = page.extract_text() or ""
			pages.append(t)
			log_parts.append(f"pypdf page {i + 1}: {len(t)} chars")
		text = "\n\n".join(pages)
		if text.strip():
			return text, " | ".join(log_parts)
	except Exception as e:
		log_parts.append(f"pypdf failed: {e}")

	# 3. PyPDF2
	try:
		from PyPDF2 import PdfReader as OldReader

		reader = OldReader(file_path)
		pages = []
		for i, page in enumerate(reader.pages):
			t = page.extract_text() or ""
			pages.append(t)
			log_parts.append(f"PyPDF2 page {i + 1}: {len(t)} chars")
		text = "\n\n".join(pages)
		if text.strip():
			return text, " | ".join(log_parts)
	except Exception as e:
		log_parts.append(f"PyPDF2 failed: {e}")

	return "", " | ".join(log_parts) + " | No text extracted (install pdfplumber or pypdf)"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DATE_PATTERNS = [
	# DD/MM/YYYY or DD-MM-YYYY
	r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
	# DD Mon YYYY / DD Month YYYY
	r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{2,4})",
	r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{2,4})",
]

AMOUNT_RE = re.compile(
	r"(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{1,2})?)\s*(?:/-)?",
	re.IGNORECASE,
)


def _parse_date(s: str):
	if not s:
		return None
	s = s.strip()
	for fmt in (
		"%d/%m/%Y",
		"%d-%m-%Y",
		"%d.%m.%Y",
		"%d/%m/%y",
		"%d-%m-%y",
		"%d %b %Y",
		"%d %B %Y",
		"%d %b. %Y",
	):
		try:
			return getdate(datetime.strptime(s, fmt).date())
		except Exception:
			continue
	try:
		return getdate(s)
	except Exception:
		return None


def _parse_amount(s: str) -> float | None:
	if not s:
		return None
	m = AMOUNT_RE.search(s.replace(" ", ""))
	if not m:
		# bare number with commas
		m2 = re.search(r"([\d,]+(?:\.\d{1,2})?)", s)
		if not m2:
			return None
		raw = m2.group(1)
	else:
		raw = m.group(1)
	try:
		return flt(raw.replace(",", ""))
	except Exception:
		return None


def _first_match(text: str, patterns: list[str], flags=re.IGNORECASE | re.MULTILINE) -> str | None:
	for pat in patterns:
		m = re.search(pat, text, flags)
		if m:
			val = m.group(1).strip() if m.lastindex else m.group(0).strip()
			if val:
				return val
	return None


def _section_block(text: str, start_labels: list[str], end_labels: list[str], max_chars: int = 12000) -> str:
	"""Extract text between a start heading and the next end heading."""
	lower = text
	start_idx = -1
	for lab in start_labels:
		m = re.search(re.escape(lab), lower, re.IGNORECASE)
		if m:
			start_idx = m.start()
			break
	if start_idx < 0:
		return ""

	end_idx = len(text)
	for lab in end_labels:
		m = re.search(re.escape(lab), text[start_idx + 20 :], re.IGNORECASE)
		if m:
			end_idx = start_idx + 20 + m.start()
			break

	block = text[start_idx:end_idx].strip()
	return block[:max_chars]


# ---------------------------------------------------------------------------
# Field extractors (Indian policy schedule oriented)
# ---------------------------------------------------------------------------

POLICY_NUMBER_PATTERNS = [
	r"(?:Policy\s*(?:No|Number|Num|#)\.?\s*[:\-]?\s*)([A-Z0-9][A-Z0-9\-\/]{5,})",
	r"(?:Policy\s*Schedule\s*(?:No|Number)?\.?\s*[:\-]?\s*)([A-Z0-9][A-Z0-9\-\/]{5,})",
	r"(?:Certificate\s*(?:No|Number)\.?\s*[:\-]?\s*)([A-Z0-9][A-Z0-9\-\/]{5,})",
	r"(?:Master\s*Policy\s*(?:No|Number)\.?\s*[:\-]?\s*)([A-Z0-9][A-Z0-9\-\/]{5,})",
]

INSURED_PATTERNS = [
	r"(?:Name\s*of\s*(?:the\s*)?(?:Insured|Proposer|Policyholder|Member)\s*[:\-]?\s*)([A-Za-z][A-Za-z\s\.\'\-]{2,60})",
	r"(?:Insured(?:'s)?\s*Name\s*[:\-]?\s*)([A-Za-z][A-Za-z\s\.\'\-]{2,60})",
	r"(?:Proposer(?:'s)?\s*Name\s*[:\-]?\s*)([A-Za-z][A-Za-z\s\.\'\-]{2,60})",
	r"(?:Policyholder\s*[:\-]?\s*)([A-Za-z][A-Za-z\s\.\'\-]{2,60})",
]

PROVIDER_PATTERNS = [
	r"(?:Insurer|Insurance\s*Company|Company\s*Name)\s*[:\-]?\s*([A-Za-z][A-Za-z\s&\.\-]{3,80}(?:Insurance|Assurance|General|Life|Health)[A-Za-z\s&\.\-]*)",
	r"((?:ICICI|HDFC|Bajaj|Star|Care|Niva|Max|Tata|SBI|New India|Oriental|United India|National|Reliance|Go Digit|Acko|Manipal|Aditya Birla|Cholamandalam|Magma|Future Generali|Iffco)[A-Za-z\s&\.\-]*(?:Insurance|Assurance|General|Life|Health)[A-Za-z\s&\.\-]*)",
]

SCHEME_PATTERNS = [
	r"(?:Product\s*Name|Plan\s*Name|Scheme\s*Name|Policy\s*Type)\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\s\-\/&]{2,80})",
	r"(?:Name\s*of\s*(?:the\s*)?Product)\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\s\-\/&]{2,80})",
]

SUM_ASSURED_PATTERNS = [
	r"(?:Sum\s*(?:Insured|Assured)|SI|Cover\s*Amount|Total\s*Sum\s*Insured)\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{1,2})?)",
	r"(?:Maximum\s*(?:Limit|Liability))\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{1,2})?)",
]

PREMIUM_PATTERNS = [
	r"(?:Total\s*(?:Premium|Amount\s*Payable)|Gross\s*Premium|Net\s*Premium|Premium\s*(?:Amount|Payable))\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{1,2})?)",
	r"(?:Premium)\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{1,2})?)",
]

START_DATE_PATTERNS = [
	r"(?:Risk\s*Commencement\s*Date|Period\s*of\s*Insurance\s*(?:From|Start)|Policy\s*(?:Start|Commencement)\s*Date|From\s*Date)\s*[:\-]?\s*"
	+ DATE_PATTERNS[0],
	r"(?:From)\s*[:\-]?\s*" + DATE_PATTERNS[0],
	r"(?:Start\s*Date)\s*[:\-]?\s*" + DATE_PATTERNS[0],
]

END_DATE_PATTERNS = [
	r"(?:Policy\s*(?:End|Expiry)\s*Date|Period\s*of\s*Insurance\s*(?:To|End)|To\s*Date|Valid\s*(?:Till|Upto|Until))\s*[:\-]?\s*"
	+ DATE_PATTERNS[0],
	r"(?:To)\s*[:\-]?\s*" + DATE_PATTERNS[0],
	r"(?:End\s*Date|Expiry)\s*[:\-]?\s*" + DATE_PATTERNS[0],
]

ISSUE_DATE_PATTERNS = [
	r"(?:Date\s*of\s*(?:Issue|Issuance)|Issue\s*Date|Policy\s*Issue\s*Date)\s*[:\-]?\s*" + DATE_PATTERNS[0],
]

FREQUENCY_MAP = {
	"monthly": "Monthly",
	"quarterly": "Quarterly",
	"half yearly": "Semi-Annually",
	"half-yearly": "Semi-Annually",
	"semi annual": "Semi-Annually",
	"semi-annual": "Semi-Annually",
	"semi annually": "Semi-Annually",
	"annual": "Annually",
	"annually": "Annually",
	"yearly": "Annually",
}


def _extract_frequency(text: str) -> str | None:
	m = re.search(
		r"(?:Premium\s*(?:Payment\s*)?(?:Frequency|Mode|Term)|Payment\s*Frequency)\s*[:\-]?\s*([A-Za-z\-\s]+)",
		text,
		re.IGNORECASE,
	)
	if m:
		raw = m.group(1).strip().lower()
		for k, v in FREQUENCY_MAP.items():
			if k in raw:
				return v
	# free occurrence
	for k, v in FREQUENCY_MAP.items():
		if re.search(rf"\b{re.escape(k)}\b", text, re.IGNORECASE):
			return v
	return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_pdf_file(file_path: str) -> dict[str, Any]:
	"""
	Parse a policy PDF and return a dict of extracted fields.

	Keys:
	  raw_text, log, message,
	  policy_number, provider_name, scheme_name, insured_name,
	  sum_assured, premium, premium_frequency,
	  start_date, end_date, issue_date,
	  terms_and_conditions, claim_eligibility, exclusions
	"""
	text, log = _extract_text(file_path)
	out: dict[str, Any] = {
		"raw_text": text[:50000] if text else "",
		"log": log,
		"message": "",
		"policy_number": None,
		"provider_name": None,
		"scheme_name": None,
		"insured_name": None,
		"sum_assured": None,
		"premium": None,
		"premium_frequency": None,
		"start_date": None,
		"end_date": None,
		"issue_date": None,
		"terms_and_conditions": "",
		"claim_eligibility": "",
		"exclusions": "",
	}

	if not text or not text.strip():
		out["message"] = (
			"Could not extract text from PDF. "
			"Install pdfplumber (`pip install pdfplumber`) or ensure the PDF is not image-only/scanned. "
			"You can still fill fields manually."
		)
		return out

	# Structured fields
	out["policy_number"] = _first_match(text, POLICY_NUMBER_PATTERNS)
	out["insured_name"] = _first_match(text, INSURED_PATTERNS)
	out["provider_name"] = _first_match(text, PROVIDER_PATTERNS)
	out["scheme_name"] = _first_match(text, SCHEME_PATTERNS)

	sa = _first_match(text, SUM_ASSURED_PATTERNS)
	out["sum_assured"] = _parse_amount(sa) if sa else None

	prem = _first_match(text, PREMIUM_PATTERNS)
	out["premium"] = _parse_amount(prem) if prem else None

	out["premium_frequency"] = _extract_frequency(text)

	sd = _first_match(text, START_DATE_PATTERNS)
	out["start_date"] = _parse_date(sd) if sd else None

	ed = _first_match(text, END_DATE_PATTERNS)
	out["end_date"] = _parse_date(ed) if ed else None

	# Period of Insurance: From X To Y on same line
	if not out["start_date"] or not out["end_date"]:
		m = re.search(
			r"(?:Period\s*of\s*Insurance|Policy\s*Period)\s*[:\-]?\s*"
			r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\s*(?:to|–|-|upto|until)\s*"
			r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
			text,
			re.IGNORECASE,
		)
		if m:
			if not out["start_date"]:
				out["start_date"] = _parse_date(m.group(1))
			if not out["end_date"]:
				out["end_date"] = _parse_date(m.group(2))

	iss = _first_match(text, ISSUE_DATE_PATTERNS)
	out["issue_date"] = _parse_date(iss) if iss else None

	# Large text blocks for AI / claim comparison
	out["terms_and_conditions"] = _section_block(
		text,
		start_labels=[
			"Terms and Conditions",
			"Terms & Conditions",
			"General Terms and Conditions",
			"Conditions",
			"Policy Conditions",
			"General Conditions",
		],
		end_labels=[
			"Exclusions",
			"What is not covered",
			"Claim Procedure",
			"Claim Process",
			"Grievance",
			"Schedule of Benefits",
			"Definitions",
		],
	)

	out["claim_eligibility"] = _section_block(
		text,
		start_labels=[
			"Claim Eligibility",
			"Eligibility for Claims",
			"Conditions for Claim",
			"Claim Conditions",
			"How to Claim",
			"Claim Procedure",
			"Claim Process",
			"Procedure for Claims",
			"Intimation of Claim",
		],
		end_labels=[
			"Exclusions",
			"Grievance",
			"Terms and Conditions",
			"Definitions",
			"Schedule",
		],
	)

	out["exclusions"] = _section_block(
		text,
		start_labels=[
			"Exclusions",
			"What is not covered",
			"Permanent Exclusions",
			"General Exclusions",
			"Exclusion",
		],
		end_labels=[
			"Terms and Conditions",
			"Claim Procedure",
			"Claim Process",
			"Grievance",
			"Definitions",
			"Waiting Period",
		],
	)

	# If claim eligibility empty, try waiting period / coverage conditions as fallback
	if not out["claim_eligibility"]:
		wp = _section_block(
			text,
			start_labels=["Waiting Period", "Coverage Conditions", "Benefit Conditions"],
			end_labels=["Exclusions", "Claim Procedure", "Terms and Conditions"],
			max_chars=6000,
		)
		if wp:
			out["claim_eligibility"] = wp

	filled = sum(
		1
		for k in (
			"policy_number",
			"insured_name",
			"provider_name",
			"sum_assured",
			"premium",
			"start_date",
			"end_date",
		)
		if out.get(k)
	)
	out["message"] = (
		f"Extracted {filled}/7 core fields. "
		f"T&Cs: {'yes' if out['terms_and_conditions'] else 'no'}, "
		f"Claim eligibility: {'yes' if out['claim_eligibility'] else 'no'}, "
		f"Exclusions: {'yes' if out['exclusions'] else 'no'}. "
		"Review and correct before creating the policy."
	)
	return out
