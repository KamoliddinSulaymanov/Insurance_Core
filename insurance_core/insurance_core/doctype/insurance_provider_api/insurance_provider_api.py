# Copyright (c) 2026, Vivaswan Works and contributors
# License: MIT

from __future__ import annotations

import json
import re
from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, now_datetime


class InsuranceProviderAPI(Document):
	def validate(self):
		if self.base_url:
			self.base_url = self.base_url.rstrip("/")
		if self.quote_path and not self.quote_path.startswith("/"):
			self.quote_path = "/" + self.quote_path

		if self.request_body_template:
			self._validate_json_field("request_body_template")
		if self.response_mapping:
			self._validate_json_field("response_mapping")

	def _validate_json_field(self, fieldname: str):
		raw = self.get(fieldname) or ""
		sanitized = re.sub(r"\{\{[^}]+\}\}", "null", raw)
		try:
			json.loads(sanitized)
		except Exception as e:
			frappe.throw(
				_("{0} must be valid JSON (placeholders like {{{{ field }}}} are allowed): {1}").format(
					self.meta.get_label(fieldname), str(e)
				),
				title=_("Invalid JSON"),
			)


def _get_password(doc: Document, field: str) -> str | None:
	try:
		return doc.get_password(field)
	except Exception:
		return None


def _build_headers(doc: Document) -> dict[str, str]:
	headers = {"Content-Type": "application/json", "Accept": "application/json"}
	auth = doc.auth_type or "None"

	if auth == "API Key":
		key = _get_password(doc, "api_key")
		name = doc.auth_header_name or "X-API-Key"
		if key:
			headers[name] = key
	elif auth == "Bearer Token":
		token = _get_password(doc, "api_key")
		if token:
			headers["Authorization"] = f"Bearer {token}"
	elif auth == "Basic":
		import base64

		user = doc.username or ""
		pwd = _get_password(doc, "password") or ""
		token = base64.b64encode(f"{user}:{pwd}".encode()).decode()
		headers["Authorization"] = f"Basic {token}"
	elif auth == "Custom Header":
		key = _get_password(doc, "api_key")
		name = doc.auth_header_name or "X-API-Key"
		if key:
			headers[name] = key
	elif auth == "OAuth2":
		token = _fetch_oauth_token(doc)
		if token:
			headers["Authorization"] = f"Bearer {token}"

	return headers


def _fetch_oauth_token(doc: Document) -> str | None:
	import requests

	url = doc.oauth_token_url
	if not url:
		frappe.throw(_("OAuth Token URL is required for OAuth2."), title=_("Missing Token URL"))

	client_id = doc.client_id or ""
	client_secret = _get_password(doc, "client_secret") or ""
	timeout = cint(doc.request_timeout) or 30

	resp = requests.post(
		url,
		data={"grant_type": "client_credentials"},
		auth=(client_id, client_secret),
		timeout=timeout,
	)
	resp.raise_for_status()
	data = resp.json()
	return data.get("access_token")


def _render_template(template: str, context: dict[str, Any]) -> str:
	if not template:
		return "{}"

	def repl(match):
		key = match.group(1).strip()
		val = context.get(key, "")
		if val is None:
			return "null"
		if isinstance(val, (int, float)):
			return str(val)
		if isinstance(val, bool):
			return "true" if val else "false"
		return json.dumps(str(val))

	return re.sub(r"\{\{\s*([^}]+)\s*\}\}", repl, template)


def _dig(data: Any, path: str) -> Any:
	if not path:
		return None
	cur = data
	for part in path.split("."):
		if cur is None:
			return None
		if isinstance(cur, dict):
			cur = cur.get(part)
		elif isinstance(cur, list) and part.isdigit():
			idx = int(part)
			cur = cur[idx] if idx < len(cur) else None
		else:
			return None
	return cur


def map_response(raw: dict | list, mapping_json: str) -> dict[str, Any]:
	mapping = {}
	if mapping_json:
		try:
			mapping = json.loads(mapping_json)
		except Exception:
			mapping = {}

	defaults = {
		"net_premium": "net_premium",
		"tax": "tax",
		"total_premium": "total_premium",
		"sum_insured": "sum_insured",
		"valid_upto": "valid_upto",
		"reference": "reference",
	}
	result = {}
	for our_key, default_path in defaults.items():
		path = mapping.get(our_key, default_path)
		result[our_key] = _dig(raw, path) if isinstance(path, str) else None
	return result


@frappe.whitelist()
def test_connection(name: str) -> dict:
	doc = frappe.get_doc("Insurance Provider API", name)
	import requests

	timeout = cint(doc.request_timeout) or 30
	url = (doc.base_url or "").rstrip("/")
	probe = url
	headers = _build_headers(doc)

	status = "Failed"
	error = None
	http_status = None
	try:
		resp = requests.request(
			method="GET",
			url=probe,
			headers=headers,
			timeout=timeout,
			allow_redirects=True,
		)
		http_status = resp.status_code
		if resp.status_code < 500:
			status = "Success" if resp.status_code < 400 else "Failed"
			if resp.status_code >= 400:
				error = f"HTTP {resp.status_code}: {(resp.text or '')[:300]}"
		else:
			error = f"HTTP {resp.status_code}: {(resp.text or '')[:300]}"
	except Exception as e:
		error = str(e)[:500]

	doc.db_set("last_tested_on", now_datetime(), update_modified=False)
	doc.db_set("last_test_status", status, update_modified=False)
	doc.db_set("last_error", error, update_modified=False)

	return {
		"status": status,
		"http_status": http_status,
		"error": error,
		"url": probe,
	}


@frappe.whitelist()
def fetch_quote(
	provider_api: str,
	line_of_business: str | None = None,
	sum_insured: float | None = None,
	age: int | None = None,
	client_type: str | None = None,
	client: str | None = None,
	opportunity: str | None = None,
	extra_context: str | None = None,
) -> dict:
	doc = frappe.get_doc("Insurance Provider API", provider_api)
	if not doc.is_enabled:
		frappe.throw(_("This Provider API is disabled."), title=_("API Disabled"))

	if line_of_business and doc.supported_lobs:
		allowed = [x.strip().lower() for x in doc.supported_lobs.split(",") if x.strip()]
		if allowed and line_of_business.strip().lower() not in allowed:
			frappe.throw(
				_("Line of Business {0} is not supported by this API.").format(line_of_business),
				title=_("LOB Not Supported"),
			)

	import requests

	context = {
		"line_of_business": line_of_business or "",
		"sum_insured": sum_insured,
		"age": age,
		"client_type": client_type or "",
		"client": client or "",
		"opportunity": opportunity or "",
	}
	if extra_context:
		try:
			context.update(json.loads(extra_context))
		except Exception:
			pass

	url = (doc.base_url or "").rstrip("/") + (doc.quote_path or "/quotes")
	headers = _build_headers(doc)
	timeout = cint(doc.request_timeout) or 30
	method = (doc.http_method or "POST").upper()

	body = None
	if method == "POST":
		rendered = _render_template(doc.request_body_template or "{}", context)
		try:
			body = json.loads(rendered)
		except Exception as e:
			frappe.throw(
				_("Request body template rendered invalid JSON: {0}").format(str(e)),
				title=_("Bad Request Template"),
			)

	try:
		resp = requests.request(
			method=method,
			url=url,
			headers=headers,
			json=body if method == "POST" else None,
			params=body if method == "GET" else None,
			timeout=timeout,
		)
		resp.raise_for_status()
		try:
			raw = resp.json()
		except Exception:
			raw = {"raw_text": resp.text}
	except Exception as e:
		frappe.throw(_("Insurer API call failed: {0}").format(str(e)), title=_("API Error"))

	mapped = map_response(raw if isinstance(raw, (dict, list)) else {}, doc.response_mapping or "")
	return {
		"provider": doc.insurance_provider,
		"provider_api": doc.name,
		"mapped": mapped,
		"raw": raw if frappe.session.user == "Administrator" else None,
		"http_status": resp.status_code,
	}


def get_enabled_api_for_provider(provider: str, line_of_business: str | None = None) -> str | None:
	filters = {"insurance_provider": provider, "is_enabled": 1}
	rows = frappe.get_all(
		"Insurance Provider API",
		filters=filters,
		fields=["name", "supported_lobs", "environment"],
		order_by="environment asc",
	)
	for row in rows:
		if line_of_business and row.supported_lobs:
			allowed = [x.strip().lower() for x in row.supported_lobs.split(",") if x.strip()]
			if allowed and line_of_business.strip().lower() not in allowed:
				continue
		return row.name
	return None
