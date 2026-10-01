import json
import unittest

from insurance_core.order_engine import (
	evaluate_show_if,
	validate_order_data,
)


class TestOrderEngine(unittest.TestCase):
	def test_evaluate_show_if(self):
		data = {"car_type": "Truck", "engine_power": 150, "is_commercial": 1}

		# Equality string
		self.assertTrue(evaluate_show_if("car_type == 'Truck'", data))
		self.assertFalse(evaluate_show_if("car_type == 'Sedan'", data))

		# Numeric comparisons
		self.assertTrue(evaluate_show_if("engine_power > 100", data))
		self.assertFalse(evaluate_show_if("engine_power > 200", data))
		self.assertTrue(evaluate_show_if("engine_power <= 150", data))

		# Empty condition is always visible
		self.assertTrue(evaluate_show_if("", data))
		self.assertTrue(evaluate_show_if(None, data))

	def test_validate_order_data_basic(self):
		schema = [
			{
				"step": 1,
				"fields": [
					{"fieldname": "vehicle_name", "label": "Марка авто", "required": True},
					{
						"fieldname": "trailer_type",
						"label": "Тип прицепа",
						"required": True,
						"show_if": "has_trailer == 1",
					},
				],
			}
		]

		# Case 1: missing vehicle_name
		data_invalid = {"has_trailer": 0}
		errors = validate_order_data(schema, data_invalid)
		self.assertEqual(len(errors), 1)
		self.assertIn("Марка авто", errors[0])

		# Case 2: valid, and trailer_type skipped because has_trailer != 1
		data_valid = {"vehicle_name": "Cobalt", "has_trailer": 0}
		errors2 = validate_order_data(schema, data_valid)
		self.assertEqual(len(errors2), 0)

		# Case 3: has_trailer == 1, trailer_type required but missing
		data_trailer = {"vehicle_name": "Cobalt", "has_trailer": 1}
		errors3 = validate_order_data(schema, data_trailer)
		self.assertEqual(len(errors3), 1)
		self.assertIn("Тип прицепа", errors3[0])

	def test_validate_order_data_uzbekistan_pinfl_and_phone(self):
		schema = [
			{
				"step": 1,
				"fields": [
					{"fieldname": "pinfl", "label": "ПИНФЛ", "required": True},
					{"fieldname": "phone", "label": "Номер телефона", "type": "Phone", "required": True},
				],
			}
		]

		# Valid data
		prefix = "3150890001123"
		weights = [7, 3, 1, 7, 3, 1, 7, 3, 1, 7, 3, 1, 7]
		chk = sum(int(prefix[i]) * weights[i] for i in range(13)) % 10
		valid_pinfl = prefix + str(chk)

		data_valid = {
			"pinfl": valid_pinfl,
			"phone": "+998901234567",
		}
		self.assertEqual(len(validate_order_data(schema, data_valid)), 0)

		# Invalid PINFL and invalid phone
		data_invalid = {
			"pinfl": "12345",
			"phone": "invalid_phone",
		}
		errors = validate_order_data(schema, data_invalid)
		self.assertEqual(len(errors), 2)


if __name__ == "__main__":
	unittest.main()
