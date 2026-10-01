import unittest
from types import SimpleNamespace

try:
	import frappe
	from frappe.tests.utils import FrappeTestCase
except ImportError:
	FrappeTestCase = unittest.TestCase

from insurance_core.engine import (
	_try_float,
	evaluate_surcharges,
	lookup_matrix,
	match_dimension,
	resolve_factor_value,
)


class TestCalculationEngineHelpers(unittest.TestCase):
	def test_try_float(self):
		self.assertEqual(_try_float("123.45"), 123.45)
		self.assertEqual(_try_float(100), 100.0)
		self.assertIsNone(_try_float("not_a_number"))
		self.assertIsNone(_try_float(None))
		self.assertIsNone(_try_float(""))

	def test_match_dimension_numeric_range(self):
		# Inside [18, 30]
		self.assertTrue(match_dimension(25, 18, 30))
		self.assertTrue(match_dimension(18, 18, 30))
		self.assertTrue(match_dimension(30, 18, 30))

		# Outside [18, 30]
		self.assertFalse(match_dimension(17, 18, 30))
		self.assertFalse(match_dimension(31, 18, 30))

		# Open-ended bounds
		self.assertTrue(match_dimension(50, 21, None))
		self.assertFalse(match_dimension(18, 21, None))
		self.assertTrue(match_dimension(50, None, 65))
		self.assertFalse(match_dimension(70, None, 65))

	def test_match_dimension_string_exact_and_list(self):
		self.assertTrue(match_dimension("Tashkent", "Tashkent", None))
		self.assertTrue(match_dimension("tashkent", "TASHKENT", None))
		self.assertTrue(match_dimension("Samarkand", "Tashkent, Samarkand, Bukhara", None))
		self.assertFalse(match_dimension("Andijan", "Tashkent, Samarkand", None))

	def test_lookup_matrix_1d(self):
		row1 = SimpleNamespace(dim1_from=18, dim1_to=25, dim2_from=None, dim2_to=None, dim3_val=None, rate=1.5, amount=0.0)
		row2 = SimpleNamespace(dim1_from=26, dim1_to=60, dim2_from=None, dim2_to=None, dim3_val=None, rate=1.0, amount=0.0)
		matrix = SimpleNamespace(
			matrix_name="Driver Age Coeff",
			dim1_factor="driver_age",
			dim2_factor=None,
			dim3_factor=None,
			default_rate=1.0,
			rows=[row1, row2],
		)

		rate, amt, note = lookup_matrix(matrix, {"driver_age": 20})
		self.assertEqual(rate, 1.5)

		rate, amt, note = lookup_matrix(matrix, {"driver_age": 35})
		self.assertEqual(rate, 1.0)

		# Fallback when outside matrix
		rate, amt, note = lookup_matrix(matrix, {"driver_age": 70})
		self.assertEqual(rate, 1.0)

	def test_lookup_matrix_2d(self):
		# 2D Matrix: Region x Car Type
		row1 = SimpleNamespace(
			dim1_from="Tashkent", dim1_to=None,
			dim2_from="Sedan", dim2_to=None,
			dim3_val=None, rate=1.2, amount=100000.0,
		)
		row2 = SimpleNamespace(
			dim1_from="Tashkent", dim1_to=None,
			dim2_from="SUV", dim2_to=None,
			dim3_val=None, rate=1.4, amount=150000.0,
		)
		matrix = SimpleNamespace(
			matrix_name="Region x Car Type",
			dim1_factor="region",
			dim2_factor="car_type",
			dim3_factor=None,
			default_rate=1.0,
			rows=[row1, row2],
		)

		rate, amt, note = lookup_matrix(matrix, {"region": "Tashkent", "car_type": "SUV"})
		self.assertEqual(rate, 1.4)
		self.assertEqual(amt, 150000.0)

	def test_resolve_factor_value(self):
		# Constant
		mapping_const = SimpleNamespace(
			source_type="Constant",
			constant_value=1.15,
			fallback_value=1.0,
			variable_name="tax_rate",
		)
		val, note = resolve_factor_value(mapping_const, {}, {})
		self.assertEqual(val, 1.15)

		# Input Factor
		mapping_input = SimpleNamespace(
			source_type="Input Factor",
			tariff_factor="vehicle_power",
			fallback_value=100.0,
			variable_name="power",
		)
		val, note = resolve_factor_value(mapping_input, {"vehicle_power": 150}, {})
		self.assertEqual(val, 150.0)

	def test_evaluate_surcharges(self):
		surcharge_young = SimpleNamespace(
			title="Young Driver",
			condition="driver_age < 21",
			action_type="Multiply Rate",
			action_value=1.3,
		)
		discount_alarm = SimpleNamespace(
			title="Anti-theft Alarm",
			condition="has_alarm == 1",
			action_type="Discount Percent",
			action_value=10.0,
		)
		rules = [surcharge_young, discount_alarm]

		# Case 1: Young driver with alarm (100,000 * 1.3 = 130,000 -> -10% = 117,000)
		ctx = {"driver_age": 20, "has_alarm": 1}
		prem, notes = evaluate_surcharges(rules, 100000.0, ctx)
		self.assertEqual(prem, 117000.0)
		self.assertEqual(len(notes), 2)

		# Case 2: Experienced driver without alarm (remains 100,000)
		ctx2 = {"driver_age": 30, "has_alarm": 0}
		prem2, notes2 = evaluate_surcharges(rules, 100000.0, ctx2)
		self.assertEqual(prem2, 100000.0)
		self.assertEqual(len(notes2), 0)


class TestCalculationEngineIntegration(FrappeTestCase):
	def test_engine_importable(self):
		from insurance_core.engine import calculate_premium

		self.assertTrue(callable(calculate_premium))

	def test_end_to_end_kasko_calculation(self):
		from insurance_core.engine import (
			evaluate_surcharges,
			lookup_matrix,
			resolve_factor_value,
			safe_eval,
		)

		# Simulate 1D Region Matrix
		reg_tashkent = SimpleNamespace(dim1_from="Tashkent", dim1_to=None, dim2_from=None, dim2_to=None, dim3_val=None, rate=1.2, amount=0.0)
		matrix_region = SimpleNamespace(matrix_name="Region Matrix", dim1_factor="region", dim2_factor=None, dim3_factor=None, default_rate=1.0, rows=[reg_tashkent])

		# Simulate 2D Power x Vehicle Type Matrix
		pow_sedan = SimpleNamespace(dim1_from=100, dim1_to=200, dim2_from="Sedan", dim2_to=None, dim3_val=None, rate=1.5, amount=0.0)
		matrix_power = SimpleNamespace(matrix_name="Power Matrix", dim1_factor="engine_power", dim2_factor="car_type", dim3_factor=None, default_rate=1.0, rows=[pow_sedan])

		# Factor mappings
		mapping_reg = SimpleNamespace(variable_name="region_coeff", source_type="Tariff Matrix", tariff_matrix="matrix_region", fallback_value=1.0)
		mapping_power = SimpleNamespace(variable_name="power_coeff", source_type="Tariff Matrix", tariff_matrix="matrix_power", fallback_value=1.0)
		mapping_kbm = SimpleNamespace(variable_name="kbm_discount", source_type="Input Factor", tariff_factor="kbm_discount", fallback_value=0.0)

		input_data = {
			"region": "Tashkent",
			"engine_power": 150,
			"car_type": "Sedan",
			"kbm_discount": 0.10,
			"driver_age": 19,
		}

		# Step 1: Resolve variables
		matrices = {"matrix_region": matrix_region, "matrix_power": matrix_power}
		context = {"base_premium": 500000.0, **input_data}

		for m in [mapping_reg, mapping_power, mapping_kbm]:
			if m.source_type == "Tariff Matrix":
				rate, amt, _ = lookup_matrix(matrices[m.tariff_matrix], input_data)
				context[m.variable_name] = rate
			else:
				val, _ = resolve_factor_value(m, input_data, context)
				context[m.variable_name] = val

		self.assertEqual(context["region_coeff"], 1.2)
		self.assertEqual(context["power_coeff"], 1.5)
		self.assertEqual(context["kbm_discount"], 0.10)

		# Step 2: Formula calculation
		formula = "base_premium * power_coeff * region_coeff * (1 - kbm_discount)"
		raw_premium = safe_eval(formula, None, context)
		# 500,000 * 1.5 * 1.2 * 0.9 = 810,000 UZS
		self.assertEqual(raw_premium, 810000.0)

		# Step 3: Surcharges (Young driver < 21 -> +30%)
		surcharges = [
			SimpleNamespace(title="Young Driver", condition="driver_age < 21", action_type="Multiply Rate", action_value=1.3)
		]
		final_premium, notes = evaluate_surcharges(surcharges, raw_premium, context)
		# 810,000 * 1.3 = 1,053,000 UZS
		self.assertEqual(final_premium, 1053000.0)
