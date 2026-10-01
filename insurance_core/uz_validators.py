"""Uzbekistan-specific Data Validators and Catalogs.

Implements:
1. PINFL (JShShIR / ПИНФЛ - 14 digits) validation (century, sex, birthdate, checksum)
2. INN (STIR / ИНН - 9 digits) validation (format, checksum)
3. National phone normalization (+998)
4. Catalog of Administrative Regions of the Republic of Uzbekistan
"""

import re
from datetime import date
from typing import Any

# Standard 14 regions & city of Tashkent & Republic of Karakalpakstan
UZ_REGIONS = [
	{"code": "10", "name_uz": "Toshkent shahri", "name_ru": "г. Ташкент"},
	{"code": "11", "name_uz": "Toshkent viloyati", "name_ru": "Ташкентская область"},
	{"code": "12", "name_uz": "Andijon viloyati", "name_ru": "Андижанская область"},
	{"code": "13", "name_uz": "Buxoro viloyati", "name_ru": "Бухарская область"},
	{"code": "14", "name_uz": "Jizzax viloyati", "name_ru": "Джизакская область"},
	{"code": "15", "name_uz": "Qashqadaryo viloyati", "name_ru": "Кашкадарьинская область"},
	{"code": "16", "name_uz": "Navoiy viloyati", "name_ru": "Навоийская область"},
	{"code": "17", "name_uz": "Namangan viloyati", "name_ru": "Наманганская область"},
	{"code": "18", "name_uz": "Samarqand viloyati", "name_ru": "Самаркандская область"},
	{"code": "19", "name_uz": "Surxondaryo viloyati", "name_ru": "Сурхандарьинская область"},
	{"code": "20", "name_uz": "Sirdaryo viloyati", "name_ru": "Сырдарьинская область"},
	{"code": "21", "name_uz": "Farg'ona viloyati", "name_ru": "Ферганская область"},
	{"code": "22", "name_uz": "Xorazm viloyati", "name_ru": "Хорезмская область"},
	{"code": "23", "name_uz": "Qoraqalpog'iston Respublikasi", "name_ru": "Республика Каракалпакстан"},
]


def normalize_uz_phone(phone: str | None) -> str:
	"""Normalize Uzbek phone number to standard +998XXXXXXXXX format."""
	if not phone:
		return ""
	digits = re.sub(r"\D", "", str(phone))
	if len(digits) == 9:
		return f"+998{digits}"
	if len(digits) == 12 and digits.startswith("998"):
		return f"+{digits}"
	return str(phone).strip()


def validate_uz_phone(phone: str | None) -> bool:
	"""Verify if phone is a valid 9-digit Uzbek mobile/landline number."""
	if not phone:
		return False
	norm = normalize_uz_phone(phone)
	# Valid prefixes: 998 + 2 digits (e.g. 90, 91, 93, 94, 95, 97, 98, 99, 88, 33, 71, etc.) + 7 digits
	return bool(re.match(r"^\+998\d{9}$", norm))


def validate_pinfl(pinfl: str | None) -> dict[str, Any]:
	"""Validate 14-digit Personal Identification Number of Physical Person (PINFL).

	Structure:
	- Digit 1: Gender and century:
	    1: Male (1801-1900), 2: Female (1801-1900)
	    3: Male (1901-2000), 4: Female (1901-2000)
	    5: Male (2001-2100), 6: Female (2001-2100)
	- Digits 2-7: Date of birth (DDMMYY)
	- Digits 8-10: District/region code
	- Digits 11-13: Serial ordinal index
	- Digit 14: Check digit
	"""
	if not pinfl:
		return {"is_valid": False, "error": "ПИНФЛ обязателен для заполнения"}

	cleaned = str(pinfl).strip()
	if not re.match(r"^\d{14}$", cleaned):
		return {"is_valid": False, "error": "ПИНФЛ должен состоять ровно из 14 цифр"}

	sex_century_digit = int(cleaned[0])
	if sex_century_digit not in (1, 2, 3, 4, 5, 6):
		return {"is_valid": False, "error": f"Недопустимая первая цифра ПИНФЛ: {sex_century_digit}"}

	gender = "Male" if sex_century_digit % 2 != 0 else "Female"

	day = int(cleaned[1:3])
	month = int(cleaned[3:5])
	short_year = int(cleaned[5:7])

	if sex_century_digit in (1, 2):
		full_year = 1800 + short_year
	elif sex_century_digit in (3, 4):
		full_year = 1900 + short_year
	else:
		full_year = 2000 + short_year

	try:
		birth_date = date(full_year, month, day)
	except ValueError:
		return {
			"is_valid": False,
			"error": f"Некорректная дата рождения в ПИНФЛ: {day:02d}.{month:02d}.{full_year}",
		}

	# Check digit verification (Uzbekistan weights: 7, 3, 1, 7, 3, 1, 7, 3, 1, 7, 3, 1, 7)
	weights = [7, 3, 1, 7, 3, 1, 7, 3, 1, 7, 3, 1, 7]
	weighted_sum = sum(int(cleaned[i]) * weights[i] for i in range(13))
	expected_checksum = weighted_sum % 10
	actual_checksum = int(cleaned[13])

	if expected_checksum != actual_checksum:
		return {
			"is_valid": False,
			"error": f"Неверная контрольная сумма ПИНФЛ (ожидалось {expected_checksum}, получено {actual_checksum})",
		}

	return {
		"is_valid": True,
		"pinfl": cleaned,
		"gender": gender,
		"birth_date": birth_date.isoformat(),
		"region_code": cleaned[7:10],
		"error": None,
	}


def validate_inn(inn: str | None) -> dict[str, Any]:
	"""Validate 9-digit Tax Identification Number (INN / STIR) for legal entities & sole traders."""
	if not inn:
		return {"is_valid": False, "error": "ИНН обязателен для заполнения"}

	cleaned = str(inn).strip()
	if not re.match(r"^\d{9}$", cleaned):
		return {"is_valid": False, "error": "ИНН должен состоять ровно из 9 цифр"}

	# Standard Uzbekistan INN check digit weights: [3, 7, 2, 4, 10, 3, 5, 9]
	weights = [3, 7, 2, 4, 10, 3, 5, 9]
	weighted_sum = sum(int(cleaned[i]) * weights[i] for i in range(8))
	expected_check = (weighted_sum % 11) % 10
	actual_check = int(cleaned[8])

	if expected_check != actual_check:
		return {
			"is_valid": False,
			"error": f"Неверная контрольная сумма ИНН (ожидалось {expected_check}, получено {actual_check})",
		}

	return {
		"is_valid": True,
		"inn": cleaned,
		"error": None,
	}


def get_regions_list() -> list[dict[str, str]]:
	"""Return standard list of Uzbekistan regions."""
	return list(UZ_REGIONS)
