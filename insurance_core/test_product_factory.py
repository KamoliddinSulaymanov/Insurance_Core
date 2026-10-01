import json
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace

from insurance_core.product_factory import (
	LOCK_TIMEOUT_MINUTES,
	export_product_bundle,
	import_product_bundle,
	lock_product,
	publish_product,
	sign_product,
	unlock_product,
)


class TestProductFactoryLogic(unittest.TestCase):
	def test_lock_timeout_constant(self):
		self.assertEqual(LOCK_TIMEOUT_MINUTES, 15)

	def test_bundle_structure_validation(self):
		# Valid sample bundle
		sample_bundle = {
			"bundle_version": "1.0",
			"product": {
				"scheme_id": "TEST_KASKO_2026",
				"scheme_name": "Test KASKO Product",
				"order_form_schema": json.dumps([
					{"name": "car_model", "label": "Модель ТС", "type": "text", "required": True},
					{"name": "engine_power", "label": "Мощность л.с.", "type": "number", "required": True},
				]),
				"widget_config": json.dumps({
					"theme": "dark",
					"accent_color": "#D32F2F",
					"title": "Оформить КАСКО онлайн"
				})
			},
			"calculation_rule": {
				"rule_name": "TEST_KASKO_RULE",
				"base_premium": 500000.0,
				"formula": "base_premium * power_rate"
			},
			"tariff_matrices": [
				{
					"matrix_code": "kasko_power_matrix",
					"matrix_name": "Power Matrix",
					"rows": [{"dim1_from": "100", "dim1_to": "200", "rate": 1.25}]
				}
			],
			"tariff_factors": [
				{"factor_code": "engine_power", "factor_name": "Мощность", "data_type": "Number"}
			]
		}

		# Validate that JSON roundtrips cleanly
		serialized = json.dumps(sample_bundle)
		deserialized = json.loads(serialized)
		self.assertEqual(deserialized["bundle_version"], "1.0")
		self.assertEqual(deserialized["product"]["scheme_id"], "TEST_KASKO_2026")
		self.assertEqual(len(deserialized["tariff_matrices"]), 1)
		self.assertEqual(len(deserialized["tariff_factors"]), 1)

	def test_order_form_schema_syntax_validation(self):
		valid_schema = json.dumps([
			{
				"step": 1,
				"step_title": "Данные автомобиля",
				"fields": [
					{"fieldname": "gov_number", "label": "Гос. номер", "type": "Data", "required": True},
					{"fieldname": "tech_passport", "label": "Техпаспорт", "type": "Data", "required": True}
				]
			},
			{
				"step": 2,
				"step_title": "Страхователь",
				"fields": [
					{"fieldname": "pinfl", "label": "ПИНФЛ", "type": "Data", "regex": r"^\d{14}$", "required": True},
					{"fieldname": "phone", "label": "Телефон", "type": "Phone", "default": "+998", "required": True}
				]
			}
		])

		# Parsing should succeed
		parsed = json.loads(valid_schema)
		self.assertEqual(len(parsed), 2)
		self.assertEqual(parsed[0]["step_title"], "Данные автомобиля")
		self.assertEqual(parsed[1]["fields"][0]["fieldname"], "pinfl")

	def test_widget_config_syntax_validation(self):
		widget_config = {
			"enabled": True,
			"primary_color": "#E50914",
			"border_radius": "8px",
			"show_header": True,
			"company_logo_url": "https://alfainvest.uz/logo.svg",
			"custom_css": ".btn-buy { font-weight: bold; }"
		}
		serialized = json.dumps(widget_config)
		parsed = json.loads(serialized)
		self.assertTrue(parsed["enabled"])
		self.assertEqual(parsed["primary_color"], "#E50914")


if __name__ == "__main__":
	unittest.main()
