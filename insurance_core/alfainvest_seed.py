"""AlfaInvest National Seed & Demo Data Loader (Uzbekistan Context).

Sets up:
1. Provider: JSIC "ALFA INVEST" (Ташкент, лицензия, валюта UZS).
2. Tariff Factors: Мощность двигателя, Возраст, Стаж, Регион, Тип ТС.
3. Tariff Matrices: 2D матрица КАСКО (Мощность х Возраст), 1D матрица Регионов ОСАГО.
4. Product Calculation Rules: формулы, маппинги, коэффициенты и надбавки.
5. Products (Insurance Scheme): КАСКО Онлайн, ОСАГО, Несчастный случай с JSON-схемами заказов.
6. B2B Partner Credit Accounts: Автодилер, Банк-партнер (лимиты в UZS).
"""

import json
from datetime import date
from typing import Any

try:
	import frappe
	from frappe import _
except ImportError:
	class _FrappeMock:
		@staticmethod
		def whitelist(*args, **kwargs):
			return lambda fn: fn

		class db:
			@staticmethod
			def exists(doctype, name):
				return False

			@staticmethod
			def set_value(doctype, name, fieldname, value=None):
				pass

		@staticmethod
		def get_doc(data):
			class Doc:
				def __init__(self, d):
					self.__dict__.update(d)
					self.name = d.get("name") or d.get("scheme_id") or d.get("matrix_code")

				def insert(self, *args, **kwargs):
					return self

				def append(self, field, row):
					if not hasattr(self, field):
						setattr(self, field, [])
					getattr(self, field).append(row)

			return Doc(data)

	frappe = _FrappeMock()
	_ = lambda s: s  # noqa: E731


@frappe.whitelist()
def install_alfainvest_seed_data() -> dict[str, Any]:
	"""Idempotently install AlfaInvest seed data into Frappe DB."""
	created = []

	# 1. Provider: JSIC "ALFA INVEST"
	provider_id = "PROV-ALFAINVEST"
	if not frappe.db.exists("Insurance Provider", provider_id):
		prov = frappe.get_doc({
			"doctype": "Insurance Provider",
			"provider_id": provider_id,
			"legal_name": 'СП АО "ALFA INVEST"',
			"brand_name": "AlfaInvest",
			"provider_type": "Own Company",
			"license_number": "SF-00214",
			"registration_number": "200123456",
			"headquarters_address": "Узбекистан, г. Ташкент, Мирабадский р-н, ул. Мовароуннахр, 73",
			"general_email": "info@alfainvest.uz",
			"support_email": "claims@alfainvest.uz",
			"phone_number": "+998711200077",
			"website_url": "https://alfainvest.uz",
			"regulatory_body": "Национальное агентство перспективных проектов РУз (НАПП)",
			"status": "Active",
			"default_currency": "UZS",
		})
		prov.insert(ignore_permissions=True)
		created.append(f"Provider: {provider_id}")

	# 2. Tariff Factors
	factors = [
		{"factor_code": "engine_power", "factor_name": "Мощность двигателя (л.с.)", "data_type": "Number"},
		{"factor_code": "driver_age", "factor_name": "Возраст водителя", "data_type": "Number"},
		{"factor_code": "driving_experience", "factor_name": "Стаж вождения (лет)", "data_type": "Number"},
		{"factor_code": "vehicle_type", "factor_name": "Тип транспортного средства", "data_type": "Select"},
		{"factor_code": "region_code", "factor_name": "Код региона регистрации", "data_type": "Select"},
	]
	for f in factors:
		code = f["factor_code"]
		if not frappe.db.exists("Tariff Factor", code):
			doc = frappe.get_doc({"doctype": "Tariff Factor", **f})
			doc.insert(ignore_permissions=True)
			created.append(f"Factor: {code}")

	# 3. Tariff Matrices
	# KASKO 2D Matrix: Power x Age
	kasko_matrix_code = "kasko_power_age_matrix"
	if not frappe.db.exists("Tariff Matrix", kasko_matrix_code):
		mat = frappe.get_doc({
			"doctype": "Tariff Matrix",
			"matrix_code": kasko_matrix_code,
			"matrix_name": "Сетка коэффициентов КАСКО (Мощность х Возраст)",
			"dim1_factor": "engine_power",
			"dim2_factor": "driver_age",
			"is_active": 1,
		})
		# Rows: Power (0-100, 101-150, 151+), Age (18-22, 23-65)
		rows = [
			{"dim1_from": "0", "dim1_to": "100", "dim2_from": "18", "dim2_to": "22", "rate": 1.40, "note": "До 100 л.с., молодой водитель"},
			{"dim1_from": "0", "dim1_to": "100", "dim2_from": "23", "dim2_to": "99", "rate": 1.00, "note": "До 100 л.с., опытный водитель"},
			{"dim1_from": "101", "dim1_to": "150", "dim2_from": "18", "dim2_to": "22", "rate": 1.65, "note": "101-150 л.с., молодой водитель"},
			{"dim1_from": "101", "dim1_to": "150", "dim2_from": "23", "dim2_to": "99", "rate": 1.20, "note": "101-150 л.с., опытный водитель"},
			{"dim1_from": "151", "dim1_to": "999", "dim2_from": "18", "dim2_to": "22", "rate": 2.10, "note": "Свыше 150 л.с., молодой водитель"},
			{"dim1_from": "151", "dim1_to": "999", "dim2_from": "23", "dim2_to": "99", "rate": 1.50, "note": "Свыше 150 л.с., опытный водитель"},
		]
		for r in rows:
			mat.append("rows", r)
		mat.insert(ignore_permissions=True)
		created.append(f"Matrix: {kasko_matrix_code}")

	# 4. Product Calculation Rule for KASKO
	kasko_rule_name = "CALC-RULE-KASKO-2026"
	if not frappe.db.exists("Product Calculation Rule", kasko_rule_name):
		rule = frappe.get_doc({
			"doctype": "Product Calculation Rule",
			"rule_name": kasko_rule_name,
			"scheme": "KASKO_ONLINE_2026",
			"is_active": 1,
			"base_premium": 1500000.0,
			"formula": "base_premium * power_age_rate",
			"min_premium": 1000000.0,
			"max_premium": 25000000.0,
		})
		rule.append("factor_mappings", {
			"variable_name": "power_age_rate",
			"source_type": "Tariff Matrix",
			"tariff_matrix": kasko_matrix_code,
			"fallback_value": 1.0,
		})
		rule.append("surcharges", {
			"title": "Скидка за безаварийное вождение (КБМ)",
			"condition": "driving_experience > 5",
			"action_type": "Discount Percent",
			"action_value": 15.0,
		})
		rule.insert(ignore_permissions=True, ignore_links=True)
		created.append(f"Calculation Rule: {kasko_rule_name}")

	# 5. Product: KASKO Online
	kasko_scheme_id = "KASKO_ONLINE_2026"
	if not frappe.db.exists("Insurance Scheme", kasko_scheme_id):
		kasko_schema = [
			{
				"step": 1,
				"step_title": "Параметры автомобиля",
				"fields": [
					{"fieldname": "vehicle_name", "label": "Марка и модель ТС", "type": "Data", "required": True, "placeholder": "Chevrolet Cobalt"},
					{"fieldname": "engine_power", "label": "Мощность двигателя (л.с.)", "type": "Number", "required": True, "default": 106},
					{"fieldname": "sum_insured", "label": "Страховая сумма (UZS)", "type": "Number", "required": True, "default": 120000000},
				],
			},
			{
				"step": 2,
				"step_title": "Водитель и Страхователь",
				"fields": [
					{"fieldname": "full_name", "label": "ФИО страхователя", "type": "Data", "required": True, "placeholder": "Алимов Сардор Бахтиярович"},
					{"fieldname": "driver_age", "label": "Возраст водителя", "type": "Number", "required": True, "default": 28},
					{"fieldname": "driving_experience", "label": "Стаж вождения (полных лет)", "type": "Number", "required": True, "default": 6},
					{"fieldname": "pinfl", "label": "ПИНФЛ (14 знаков)", "type": "PINFL", "required": True, "placeholder": "31508900011234"},
					{"fieldname": "phone", "label": "Номер телефона", "type": "Phone", "required": True, "default": "+998"},
				],
			},
		]
		widget_cfg = {
			"title": "КАСКО Онлайн от AlfaInvest",
			"primary_color": "#D32F2F",
			"border_radius": "8px",
			"show_breakdown": True,
		}
		scheme_doc = frappe.get_doc({
			"doctype": "Insurance Scheme",
			"scheme_id": kasko_scheme_id,
			"scheme_name": "АвтоКАСКО Онлайн 2026",
			"provider": provider_id,
			"line_of_business": "Auto",
			"policy_type": "Comprehensive Motor",
			"status": "Published",
			"minimum_sum_assured": 50000000.0,
			"maximum_sum_assured": 1000000000.0,
			"calculation_rule": kasko_rule_name,
			"order_form_schema": json.dumps(kasko_schema, ensure_ascii=False),
			"widget_config": json.dumps(widget_cfg, ensure_ascii=False),
			"description": "Полная защита автомобиля от ущерба, угона и противоправных действий третьих лиц с быстрым урегулированием в Ташкенте и регионах.",
		})
		scheme_doc.insert(ignore_permissions=True, ignore_links=True)
		created.append(f"Scheme: {kasko_scheme_id}")

	# 6. B2B Partner Agents & Credit Accounts
	partner_agents = [
		{"agent_code": "AGT-ROHAT-MOTORS", "agent_name": "Автосалон Rohat Motors", "agent_type": "Corporate Agent"},
		{"agent_code": "AGT-IPOTEKA-BANK", "agent_name": "АКИБ Ипотека-Банк", "agent_type": "Corporate Agent"},
	]
	for ag in partner_agents:
		if not frappe.db.exists("Insurance Agent", {"agent_code": ag["agent_code"]}):
			frappe.get_doc({
				"doctype": "Insurance Agent",
				"agent_name": ag["agent_name"],
				"agent_code": ag["agent_code"],
				"agent_type": ag["agent_type"],
				"status": "Active",
			}).insert(ignore_permissions=True)

	partners = [
		{
			"partner": frappe.db.get_value("Insurance Agent", {"agent_code": "AGT-ROHAT-MOTORS"}, "name") or "AGT-ROHAT-MOTORS",
			"account_type": "Credit Limit",
			"status": "Active",
			"currency": "UZS",
			"sanctioned_credit_limit": 250000000.0,
			"utilized_limit": 15000000.0,
			"allow_overdraft": 1,
			"max_overdraft_amount": 50000000.0,
		},
		{
			"partner": frappe.db.get_value("Insurance Agent", {"agent_code": "AGT-IPOTEKA-BANK"}, "name") or "AGT-IPOTEKA-BANK",
			"account_type": "Hybrid",
			"status": "Active",
			"currency": "UZS",
			"sanctioned_credit_limit": 500000000.0,
			"deposit_balance": 100000000.0,
			"utilized_limit": 45000000.0,
		},
	]
	for p in partners:
		p_id = p["partner"]
		if not frappe.db.exists("Partner Credit Account", {"partner": p_id}):
			doc = frappe.get_doc({"doctype": "Partner Credit Account", **p})
			doc.insert(ignore_permissions=True, ignore_links=True)
			created.append(f"Partner Account: {p_id}")

	return {
		"status": "success",
		"created_entities": created,
	}
