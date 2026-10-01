import unittest
from datetime import date

from insurance_core.uz_validators import (
	get_regions_list,
	normalize_uz_phone,
	validate_inn,
	validate_pinfl,
	validate_uz_phone,
)


class TestUzValidators(unittest.TestCase):
	def test_phone_normalization_and_validation(self):
		self.assertEqual(normalize_uz_phone("901234567"), "+998901234567")
		self.assertEqual(normalize_uz_phone("+998 (90) 123-45-67"), "+998901234567")
		self.assertTrue(validate_uz_phone("+998901234567"))
		self.assertTrue(validate_uz_phone("901234567"))
		self.assertFalse(validate_uz_phone("12345"))
		self.assertFalse(validate_uz_phone("+79001234567"))

	def test_pinfl_validation(self):
		# Construct a valid PINFL:
		# Digit 1: 3 (Male born 1901-2000)
		# Digits 2-7: 15 08 90 (15 August 1990)
		# Digits 8-10: 001 (Tashkent)
		# Digits 11-13: 123 (Serial)
		prefix = "3150890001123"
		weights = [7, 3, 1, 7, 3, 1, 7, 3, 1, 7, 3, 1, 7]
		chk = sum(int(prefix[i]) * weights[i] for i in range(13)) % 10
		valid_pinfl = prefix + str(chk)

		res = validate_pinfl(valid_pinfl)
		self.assertTrue(res["is_valid"])
		self.assertEqual(res["gender"], "Male")
		self.assertEqual(res["birth_date"], "1990-08-15")

		# Invalid checksum test
		invalid_chk_pinfl = prefix + str((chk + 1) % 10)
		res_bad = validate_pinfl(invalid_chk_pinfl)
		self.assertFalse(res_bad["is_valid"])
		self.assertIn("Неверная контрольная сумма", res_bad["error"])

		# Invalid length test
		self.assertFalse(validate_pinfl("12345")["is_valid"])

		# Invalid first digit test
		res_bad_century = validate_pinfl("91508900011234")
		self.assertFalse(res_bad_century["is_valid"])

	def test_inn_validation(self):
		# Construct a valid 9-digit INN:
		# First 8 digits: 30512345
		# Weights: [3, 7, 2, 4, 10, 3, 5, 9]
		prefix = "30512345"
		weights = [3, 7, 2, 4, 10, 3, 5, 9]
		chk = (sum(int(prefix[i]) * weights[i] for i in range(8)) % 11) % 10
		valid_inn = prefix + str(chk)

		res = validate_inn(valid_inn)
		self.assertTrue(res["is_valid"])

		# Invalid check digit test
		res_bad = validate_inn(prefix + str((chk + 1) % 10))
		self.assertFalse(res_bad["is_valid"])

	def test_regions_catalog(self):
		regions = get_regions_list()
		self.assertEqual(len(regions), 14)
		codes = [r["code"] for r in regions]
		self.assertIn("10", codes)  # Tashkent city
		self.assertIn("23", codes)  # Karakalpakstan


if __name__ == "__main__":
	unittest.main()
