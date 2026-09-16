# Copyright (c) 2026, Vivaswan Works and contributors
# License: MIT
"""
Bulky Indian-context demo / seed data for Insurance Core.

Install via:
  - Interactive prompt during `bench --site <site> install-app insurance_core`
  - Or later:  bench --site <site> execute insurance_core.demo_data.install_demo_data
  - Or Desk: Insurance Settings → "Install Demo Data" (calls the whitelisted method)

All inserts are idempotent (skip if unique key already exists).
"""

from __future__ import annotations

import random
from datetime import date, timedelta

import frappe
from frappe.utils import add_days, add_months, getdate, nowdate, random_string


# ---------------------------------------------------------------------------
# Indian context constants
# ---------------------------------------------------------------------------

CITIES = [
	("Mumbai", "Maharashtra"),
	("Delhi", "Delhi"),
	("Bengaluru", "Karnataka"),
	("Chennai", "Tamil Nadu"),
	("Hyderabad", "Telangana"),
	("Pune", "Maharashtra"),
	("Kolkata", "West Bengal"),
	("Ahmedabad", "Gujarat"),
	("Jaipur", "Rajasthan"),
	("Lucknow", "Uttar Pradesh"),
	("Chandigarh", "Chandigarh"),
	("Kochi", "Kerala"),
	("Indore", "Madhya Pradesh"),
	("Nagpur", "Maharashtra"),
	("Coimbatore", "Tamil Nadu"),
]

FIRST_NAMES = [
	"Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan",
	"Krishna", "Ishaan", "Shaurya", "Atharv", "Advait", "Dhruv", "Kabir",
	"Ananya", "Aadhya", "Diya", "Myra", "Sara", "Anika", "Aarohi", "Pari",
	"Anvi", "Kiara", "Prisha", "Navya", "Riya", "Saanvi", "Ira",
	"Rohan", "Rahul", "Amit", "Suresh", "Vikram", "Nikhil", "Sanjay", "Rajesh",
	"Priya", "Neha", "Pooja", "Sneha", "Kavya", "Meera", "Divya", "Shreya",
	"Deepak", "Manish", "Gaurav", "Harsh", "Yash", "Karan", "Ravi", "Sunil",
]

LAST_NAMES = [
	"Sharma", "Patel", "Singh", "Kumar", "Gupta", "Reddy", "Nair", "Iyer",
	"Joshi", "Mehta", "Shah", "Chopra", "Malhotra", "Kapoor", "Verma",
	"Agarwal", "Banerjee", "Chatterjee", "Das", "Mukherjee", "Pillai",
	"Rao", "Menon", "Desai", "Jain", "Bhat", "Shetty", "Kulkarni", "Pandey",
]

STREET_AREAS = [
	"Andheri East", "Bandra West", "Powai", "Connaught Place", "Saket",
	"Indiranagar", "Koramangala", "Whitefield", "T Nagar", "Adyar",
	"Banjara Hills", "Gachibowli", "Koregaon Park", "Hinjewadi",
	"Salt Lake", "Park Street", "Satellite", "Navrangpura", "C Scheme",
	"Hazratganj", "Sector 17", "MG Road", "Palayam", "Vijay Nagar",
]

INDIAN_PROVIDERS = [
	{
		"provider_id": "PROV-STAR",
		"legal_name": "Star Health and Allied Insurance Company Limited",
		"brand_name": "Star Health",
		"provider_type": "Private",
		"license_number": "IRDAI/HLT/SHAI/15/2006",
		"registration_number": "IRDAI/HLT/SHAI/15/2006",
		"gstin": "33AABCS1234A1Z5",
		"pan": "AABCS1234A",
		"headquarters_address": "1, New Tank Street, Valluvar Kottam High Road, Nungambakkam, Chennai 600034",
		"general_email": "support@starhealth.in",
		"support_email": "claims@starhealth.in",
		"phone_number": "+91-44-28288800",
		"toll_free_number": "1800-425-2255",
		"website_url": "https://www.starhealth.in",
		"regulatory_body": "IRDAI",
		"status": "Active",
		"credit_rating": "AA-",
		"claim_settlement_ratio": 92.5,
		"commission_rate": 15.0,
		"settlement_cycle": "Monthly",
		"default_currency": "INR",
	},
	{
		"provider_id": "PROV-HDFC",
		"legal_name": "HDFC ERGO General Insurance Company Limited",
		"brand_name": "HDFC ERGO",
		"provider_type": "Private",
		"license_number": "IRDAI/NL/HDEGI/01/2002",
		"registration_number": "IRDAI/NL/HDEGI/01/2002",
		"gstin": "27AABCH1234B1Z8",
		"pan": "AABCH1234B",
		"headquarters_address": "HDFC House, 165-166 Backbay Reclamation, H.T. Parekh Marg, Churchgate, Mumbai 400020",
		"general_email": "care@hdfcergo.com",
		"support_email": "claims@hdfcergo.com",
		"phone_number": "+91-22-66383600",
		"toll_free_number": "1800-226-226",
		"website_url": "https://www.hdfcergo.com",
		"regulatory_body": "IRDAI",
		"status": "Active",
		"credit_rating": "AAA",
		"claim_settlement_ratio": 96.2,
		"commission_rate": 12.5,
		"settlement_cycle": "Monthly",
		"default_currency": "INR",
	},
	{
		"provider_id": "PROV-ICICI",
		"legal_name": "ICICI Lombard General Insurance Company Limited",
		"brand_name": "ICICI Lombard",
		"provider_type": "Private",
		"license_number": "IRDAI/NL/ICICIL/04/2001",
		"registration_number": "IRDAI/NL/ICICIL/04/2001",
		"gstin": "27AAACI1234C1Z9",
		"pan": "AAACI1234C",
		"headquarters_address": "ICICI Lombard House, 414, Veer Savarkar Marg, Near Siddhi Vinayak Temple, Prabhadevi, Mumbai 400025",
		"general_email": "customersupport@icicilombard.com",
		"support_email": "claims@icicilombard.com",
		"phone_number": "+91-22-61984700",
		"toll_free_number": "1800-2666",
		"website_url": "https://www.icicilombard.com",
		"regulatory_body": "IRDAI",
		"status": "Active",
		"credit_rating": "AAA",
		"claim_settlement_ratio": 97.1,
		"commission_rate": 14.0,
		"settlement_cycle": "Weekly",
		"default_currency": "INR",
	},
	{
		"provider_id": "PROV-BAJAJ",
		"legal_name": "Bajaj Allianz General Insurance Company Limited",
		"brand_name": "Bajaj Allianz",
		"provider_type": "Private",
		"license_number": "IRDAI/NL/BAGIC/02/2001",
		"registration_number": "IRDAI/NL/BAGIC/02/2001",
		"gstin": "27AABCB1234D1Z2",
		"pan": "AABCB1234D",
		"headquarters_address": "Bajaj Allianz House, Airport Road, Yerawada, Pune 411006",
		"general_email": "bagichelp@bajajallianz.co.in",
		"support_email": "claims@bajajallianz.co.in",
		"phone_number": "+91-20-30305858",
		"toll_free_number": "1800-209-5858",
		"website_url": "https://www.bajajallianz.com",
		"regulatory_body": "IRDAI",
		"status": "Active",
		"credit_rating": "AA+",
		"claim_settlement_ratio": 94.8,
		"commission_rate": 13.0,
		"settlement_cycle": "Monthly",
		"default_currency": "INR",
	},
	{
		"provider_id": "PROV-NIA",
		"legal_name": "The New India Assurance Company Limited",
		"brand_name": "New India Assurance",
		"provider_type": "Public",
		"license_number": "IRDAI/NL/NIA/01/1919",
		"registration_number": "IRDAI/NL/NIA/01/1919",
		"gstin": "27AAACN1234E1Z3",
		"pan": "AAACN1234E",
		"headquarters_address": "New India Assurance Building, 87, M.G. Road, Fort, Mumbai 400001",
		"general_email": "info@newindia.co.in",
		"support_email": "claims@newindia.co.in",
		"phone_number": "+91-22-22708100",
		"toll_free_number": "1800-209-1415",
		"website_url": "https://www.newindia.co.in",
		"regulatory_body": "IRDAI",
		"status": "Active",
		"credit_rating": "AAA",
		"claim_settlement_ratio": 91.3,
		"commission_rate": 10.0,
		"settlement_cycle": "Monthly",
		"default_currency": "INR",
	},
	{
		"provider_id": "PROV-GIPSA",
		"legal_name": "GIC Re (General Insurance Corporation of India)",
		"brand_name": "GIC Re",
		"provider_type": "Reinsurer",
		"license_number": "IRDAI/RE/GIC/01/1972",
		"registration_number": "IRDAI/RE/GIC/01/1972",
		"gstin": "27AAACG1234F1Z4",
		"pan": "AAACG1234F",
		"headquarters_address": "Suraksha, 170, J. Tata Road, Churchgate, Mumbai 400020",
		"general_email": "info@gicofindia.com",
		"support_email": "reinsurance@gicofindia.com",
		"phone_number": "+91-22-22867000",
		"website_url": "https://www.gicofindia.com",
		"regulatory_body": "IRDAI",
		"status": "Active",
		"credit_rating": "AAA",
		"commission_rate": 0,
		"settlement_cycle": "Quarterly",
		"default_currency": "INR",
	},
	{
		"provider_id": "PROV-MEDI",
		"legal_name": "Medi Assist Insurance TPA Private Limited",
		"brand_name": "Medi Assist",
		"provider_type": "TPA",
		"license_number": "IRDAI/TPA/MA/01/2002",
		"registration_number": "IRDAI/TPA/MA/01/2002",
		"gstin": "29AABCM1234G1Z6",
		"pan": "AABCM1234G",
		"headquarters_address": "Tower D, 4th Floor, IBC Knowledge Park, Bannerghatta Road, Bengaluru 560029",
		"general_email": "support@mediassist.in",
		"support_email": "cashless@mediassist.in",
		"phone_number": "+91-80-41122200",
		"toll_free_number": "1800-425-2255",
		"website_url": "https://www.mediassist.in",
		"regulatory_body": "IRDAI",
		"status": "Active",
		"commission_rate": 0,
		"settlement_cycle": "Weekly",
		"default_currency": "INR",
	},
	{
		"provider_id": "PROV-PARAM",
		"legal_name": "Paramount Health Services & Insurance TPA Pvt. Ltd.",
		"brand_name": "Paramount TPA",
		"provider_type": "TPA",
		"license_number": "IRDAI/TPA/PHS/03/2001",
		"registration_number": "IRDAI/TPA/PHS/03/2001",
		"gstin": "27AABCP1234H1Z7",
		"pan": "AABCP1234H",
		"headquarters_address": "Plot No. A-3, Sector 16, Noida 201301, Uttar Pradesh",
		"general_email": "info@paramounttpa.com",
		"support_email": "claims@paramounttpa.com",
		"phone_number": "+91-120-4015000",
		"toll_free_number": "1800-102-4488",
		"website_url": "https://www.paramounttpa.com",
		"regulatory_body": "IRDAI",
		"status": "Active",
		"commission_rate": 0,
		"settlement_cycle": "Weekly",
		"default_currency": "INR",
	},
]

SCHEMES = [{'claim_process_type': 'Hybrid',
  'coverage_type': 'Indemnity',
  'free_look_period_days': 15,
  'grace_period_days': 30,
  'gst_applicable': 1,
  'line_of_business': 'Health',
  'maximum_age': 65,
  'maximum_sum_assured': 10000000,
  'minimum_age': 18,
  'minimum_sum_assured': 300000,
  'policy_term_months': 12,
  'policy_type': 'Individual / Family Floater',
  'pre_existing_waiting': 36,
  'premium_basis': 'Age Band',
  'premium_frequency': 'Annually',
  'product_category': 'Retail',
  'provider': 'PROV-STAR',
  'renewable_age_limit': 99,
  'renewal_allowed': 1,
  'scheme_code': 'STAR-HLTH-GOLD',
  'scheme_id': 'SCH-STAR-HLTH-GOLD',
  'scheme_name': 'Star Health Gold',
  'status': 'Active',
  'sum_insured_type': 'Floater',
  'target_audience': 'Families',
  'tax_gst_rate': 18,
  'waiting_period_days': 30},
 {'claim_process_type': 'Cashless',
  'coverage_type': 'Indemnity',
  'free_look_period_days': 15,
  'grace_period_days': 30,
  'gst_applicable': 1,
  'line_of_business': 'Health',
  'maximum_age': 65,
  'maximum_sum_assured': 5000000,
  'minimum_age': 18,
  'minimum_sum_assured': 200000,
  'policy_term_months': 12,
  'policy_type': 'Individual',
  'pre_existing_waiting': 36,
  'premium_basis': 'Age Band',
  'premium_frequency': 'Annually',
  'product_category': 'Retail',
  'provider': 'PROV-STAR',
  'renewable_age_limit': 99,
  'renewal_allowed': 1,
  'scheme_code': 'STAR-HLTH-SILVER',
  'scheme_id': 'SCH-STAR-HLTH-SILVER',
  'scheme_name': 'Star Health Silver',
  'status': 'Active',
  'sum_insured_type': 'Per Member',
  'target_audience': 'Individuals',
  'tax_gst_rate': 18,
  'waiting_period_days': 30},
 {'claim_process_type': 'Reimbursement',
  'coverage_type': 'Indemnity',
  'free_look_period_days': 0,
  'grace_period_days': 30,
  'gst_applicable': 1,
  'line_of_business': 'Auto',
  'maximum_age': None,
  'maximum_sum_assured': 5000000,
  'minimum_age': None,
  'minimum_sum_assured': 50000,
  'policy_term_months': 12,
  'policy_type': 'Comprehensive',
  'pre_existing_waiting': 0,
  'premium_basis': 'Sum Insured',
  'premium_frequency': 'Annually',
  'product_category': 'Retail',
  'provider': 'PROV-STAR',
  'renewable_age_limit': None,
  'renewal_allowed': 1,
  'scheme_code': 'STAR-MOTOR-COMP',
  'scheme_id': 'SCH-STAR-MOTOR-COMP',
  'scheme_name': 'Star Motor Comprehensive',
  'status': 'Active',
  'sum_insured_type': 'Fixed',
  'target_audience': 'Individuals',
  'tax_gst_rate': 18,
  'waiting_period_days': 0},
 {'claim_process_type': 'Hybrid',
  'coverage_type': 'Indemnity',
  'grace_period_days': 30,
  'gst_applicable': 1,
  'line_of_business': 'Health',
  'maximum_sum_assured': 2500000,
  'minimum_sum_assured': 100000,
  'policy_term_months': 12,
  'policy_type': 'Individual',
  'premium_basis': 'Age Band',
  'premium_frequency': 'Annually',
  'product_category': 'Retail',
  'provider': 'PROV-STAR',
  'renewal_allowed': 1,
  'scheme_code': 'STAR-SENIOR',
  'scheme_id': 'SCH-STAR-SENIOR',
  'scheme_name': 'Star Senior Citizen Red Carpet',
  'status': 'Active',
  'sum_insured_type': 'Fixed',
  'tax_gst_rate': 18},
 {'claim_process_type': 'Hybrid',
  'coverage_type': 'Indemnity',
  'free_look_period_days': 15,
  'grace_period_days': 30,
  'gst_applicable': 1,
  'line_of_business': 'Health',
  'maximum_age': 65,
  'maximum_sum_assured': 10000000,
  'minimum_age': 18,
  'minimum_sum_assured': 300000,
  'policy_term_months': 12,
  'policy_type': 'Individual / Family Floater',
  'pre_existing_waiting': 36,
  'premium_basis': 'Age Band',
  'premium_frequency': 'Annually',
  'product_category': 'Retail',
  'provider': 'PROV-HDFC',
  'renewable_age_limit': 99,
  'renewal_allowed': 1,
  'scheme_code': 'HDFC-HLTH-GOLD',
  'scheme_id': 'SCH-HDFC-HLTH-GOLD',
  'scheme_name': 'HDFC ERGO Health Gold',
  'status': 'Active',
  'sum_insured_type': 'Floater',
  'target_audience': 'Families',
  'tax_gst_rate': 18,
  'waiting_period_days': 30},
 {'claim_process_type': 'Cashless',
  'coverage_type': 'Indemnity',
  'free_look_period_days': 15,
  'grace_period_days': 30,
  'gst_applicable': 1,
  'line_of_business': 'Health',
  'maximum_age': 65,
  'maximum_sum_assured': 5000000,
  'minimum_age': 18,
  'minimum_sum_assured': 200000,
  'policy_term_months': 12,
  'policy_type': 'Individual',
  'pre_existing_waiting': 36,
  'premium_basis': 'Age Band',
  'premium_frequency': 'Annually',
  'product_category': 'Retail',
  'provider': 'PROV-HDFC',
  'renewable_age_limit': 99,
  'renewal_allowed': 1,
  'scheme_code': 'HDFC-HLTH-SILVER',
  'scheme_id': 'SCH-HDFC-HLTH-SILVER',
  'scheme_name': 'HDFC ERGO Health Silver',
  'status': 'Active',
  'sum_insured_type': 'Per Member',
  'target_audience': 'Individuals',
  'tax_gst_rate': 18,
  'waiting_period_days': 30},
 {'claim_process_type': 'Reimbursement',
  'coverage_type': 'Indemnity',
  'free_look_period_days': 0,
  'grace_period_days': 30,
  'gst_applicable': 1,
  'line_of_business': 'Auto',
  'maximum_age': None,
  'maximum_sum_assured': 5000000,
  'minimum_age': None,
  'minimum_sum_assured': 50000,
  'policy_term_months': 12,
  'policy_type': 'Comprehensive',
  'pre_existing_waiting': 0,
  'premium_basis': 'Sum Insured',
  'premium_frequency': 'Annually',
  'product_category': 'Retail',
  'provider': 'PROV-HDFC',
  'renewable_age_limit': None,
  'renewal_allowed': 1,
  'scheme_code': 'HDFC-MOTOR-COMP',
  'scheme_id': 'SCH-HDFC-MOTOR-COMP',
  'scheme_name': 'HDFC ERGO Motor Comprehensive',
  'status': 'Active',
  'sum_insured_type': 'Fixed',
  'target_audience': 'Individuals',
  'tax_gst_rate': 18,
  'waiting_period_days': 0},
 {'claim_process_type': 'Reimbursement',
  'coverage_type': 'Indemnity',
  'grace_period_days': 30,
  'gst_applicable': 1,
  'line_of_business': 'Travel',
  'maximum_sum_assured': 500000,
  'minimum_sum_assured': 50000,
  'policy_term_months': 12,
  'policy_type': 'Single Trip / Annual',
  'premium_basis': 'Flat',
  'premium_frequency': 'Annually',
  'product_category': 'Retail',
  'provider': 'PROV-HDFC',
  'renewal_allowed': 1,
  'scheme_code': 'HDFC-TRAVEL',
  'scheme_id': 'SCH-HDFC-TRAVEL',
  'scheme_name': 'HDFC ERGO Travel Insurance',
  'status': 'Active',
  'sum_insured_type': 'Fixed',
  'tax_gst_rate': 18},
 {'claim_process_type': 'Hybrid',
  'coverage_type': 'Indemnity',
  'free_look_period_days': 15,
  'grace_period_days': 30,
  'gst_applicable': 1,
  'line_of_business': 'Health',
  'maximum_age': 65,
  'maximum_sum_assured': 10000000,
  'minimum_age': 18,
  'minimum_sum_assured': 300000,
  'policy_term_months': 12,
  'policy_type': 'Individual / Family Floater',
  'pre_existing_waiting': 36,
  'premium_basis': 'Age Band',
  'premium_frequency': 'Annually',
  'product_category': 'Retail',
  'provider': 'PROV-ICICI',
  'renewable_age_limit': 99,
  'renewal_allowed': 1,
  'scheme_code': 'ICICI-HLTH-GOLD',
  'scheme_id': 'SCH-ICICI-HLTH-GOLD',
  'scheme_name': 'ICICI Lombard Health Gold',
  'status': 'Active',
  'sum_insured_type': 'Floater',
  'target_audience': 'Families',
  'tax_gst_rate': 18,
  'waiting_period_days': 30},
 {'claim_process_type': 'Cashless',
  'coverage_type': 'Indemnity',
  'free_look_period_days': 15,
  'grace_period_days': 30,
  'gst_applicable': 1,
  'line_of_business': 'Health',
  'maximum_age': 65,
  'maximum_sum_assured': 5000000,
  'minimum_age': 18,
  'minimum_sum_assured': 200000,
  'policy_term_months': 12,
  'policy_type': 'Individual',
  'pre_existing_waiting': 36,
  'premium_basis': 'Age Band',
  'premium_frequency': 'Annually',
  'product_category': 'Retail',
  'provider': 'PROV-ICICI',
  'renewable_age_limit': 99,
  'renewal_allowed': 1,
  'scheme_code': 'ICICI-HLTH-SILVER',
  'scheme_id': 'SCH-ICICI-HLTH-SILVER',
  'scheme_name': 'ICICI Lombard Health Silver',
  'status': 'Active',
  'sum_insured_type': 'Per Member',
  'target_audience': 'Individuals',
  'tax_gst_rate': 18,
  'waiting_period_days': 30},
 {'claim_process_type': 'Reimbursement',
  'coverage_type': 'Indemnity',
  'free_look_period_days': 0,
  'grace_period_days': 30,
  'gst_applicable': 1,
  'line_of_business': 'Auto',
  'maximum_age': None,
  'maximum_sum_assured': 5000000,
  'minimum_age': None,
  'minimum_sum_assured': 50000,
  'policy_term_months': 12,
  'policy_type': 'Comprehensive',
  'pre_existing_waiting': 0,
  'premium_basis': 'Sum Insured',
  'premium_frequency': 'Annually',
  'product_category': 'Retail',
  'provider': 'PROV-ICICI',
  'renewable_age_limit': None,
  'renewal_allowed': 1,
  'scheme_code': 'ICICI-MOTOR-COMP',
  'scheme_id': 'SCH-ICICI-MOTOR-COMP',
  'scheme_name': 'ICICI Lombard Motor Comprehensive',
  'status': 'Active',
  'sum_insured_type': 'Fixed',
  'target_audience': 'Individuals',
  'tax_gst_rate': 18,
  'waiting_period_days': 0},
 {'claim_process_type': 'Reimbursement',
  'coverage_type': 'Indemnity',
  'grace_period_days': 30,
  'gst_applicable': 1,
  'line_of_business': 'Property',
  'maximum_sum_assured': 50000000,
  'minimum_sum_assured': 500000,
  'policy_term_months': 12,
  'policy_type': 'Home / Dwelling',
  'premium_basis': 'Sum Insured',
  'premium_frequency': 'Annually',
  'product_category': 'Retail',
  'provider': 'PROV-ICICI',
  'renewal_allowed': 1,
  'scheme_code': 'ICICI-HOME',
  'scheme_id': 'SCH-ICICI-HOME',
  'scheme_name': 'ICICI Lombard Home Protect',
  'status': 'Active',
  'sum_insured_type': 'Fixed',
  'tax_gst_rate': 18},
 {'claim_process_type': 'Hybrid',
  'coverage_type': 'Indemnity',
  'free_look_period_days': 15,
  'grace_period_days': 30,
  'gst_applicable': 1,
  'line_of_business': 'Health',
  'maximum_age': 65,
  'maximum_sum_assured': 10000000,
  'minimum_age': 18,
  'minimum_sum_assured': 300000,
  'policy_term_months': 12,
  'policy_type': 'Individual / Family Floater',
  'pre_existing_waiting': 36,
  'premium_basis': 'Age Band',
  'premium_frequency': 'Annually',
  'product_category': 'Retail',
  'provider': 'PROV-BAJAJ',
  'renewable_age_limit': 99,
  'renewal_allowed': 1,
  'scheme_code': 'BAJAJ-HLTH-GOLD',
  'scheme_id': 'SCH-BAJAJ-HLTH-GOLD',
  'scheme_name': 'Bajaj Allianz Health Gold',
  'status': 'Active',
  'sum_insured_type': 'Floater',
  'target_audience': 'Families',
  'tax_gst_rate': 18,
  'waiting_period_days': 30},
 {'claim_process_type': 'Cashless',
  'coverage_type': 'Indemnity',
  'free_look_period_days': 15,
  'grace_period_days': 30,
  'gst_applicable': 1,
  'line_of_business': 'Health',
  'maximum_age': 65,
  'maximum_sum_assured': 5000000,
  'minimum_age': 18,
  'minimum_sum_assured': 200000,
  'policy_term_months': 12,
  'policy_type': 'Individual',
  'pre_existing_waiting': 36,
  'premium_basis': 'Age Band',
  'premium_frequency': 'Annually',
  'product_category': 'Retail',
  'provider': 'PROV-BAJAJ',
  'renewable_age_limit': 99,
  'renewal_allowed': 1,
  'scheme_code': 'BAJAJ-HLTH-SILVER',
  'scheme_id': 'SCH-BAJAJ-HLTH-SILVER',
  'scheme_name': 'Bajaj Allianz Health Silver',
  'status': 'Active',
  'sum_insured_type': 'Per Member',
  'target_audience': 'Individuals',
  'tax_gst_rate': 18,
  'waiting_period_days': 30},
 {'claim_process_type': 'Reimbursement',
  'coverage_type': 'Indemnity',
  'free_look_period_days': 0,
  'grace_period_days': 30,
  'gst_applicable': 1,
  'line_of_business': 'Auto',
  'maximum_age': None,
  'maximum_sum_assured': 5000000,
  'minimum_age': None,
  'minimum_sum_assured': 50000,
  'policy_term_months': 12,
  'policy_type': 'Comprehensive',
  'pre_existing_waiting': 0,
  'premium_basis': 'Sum Insured',
  'premium_frequency': 'Annually',
  'product_category': 'Retail',
  'provider': 'PROV-BAJAJ',
  'renewable_age_limit': None,
  'renewal_allowed': 1,
  'scheme_code': 'BAJAJ-MOTOR-COMP',
  'scheme_id': 'SCH-BAJAJ-MOTOR-COMP',
  'scheme_name': 'Bajaj Allianz Motor Comprehensive',
  'status': 'Active',
  'sum_insured_type': 'Fixed',
  'target_audience': 'Individuals',
  'tax_gst_rate': 18,
  'waiting_period_days': 0},
 {'claim_process_type': 'Reimbursement',
  'coverage_type': 'Indemnity',
  'grace_period_days': 30,
  'gst_applicable': 1,
  'line_of_business': 'Travel',
  'maximum_sum_assured': 500000,
  'minimum_sum_assured': 50000,
  'policy_term_months': 12,
  'policy_type': 'Single Trip / Annual Multi-trip',
  'premium_basis': 'Flat',
  'premium_frequency': 'Annually',
  'product_category': 'Retail',
  'provider': 'PROV-BAJAJ',
  'renewal_allowed': 1,
  'scheme_code': 'BAJAJ-TRAVEL',
  'scheme_id': 'SCH-BAJAJ-TRAVEL',
  'scheme_name': 'Bajaj Allianz Travel Elite',
  'status': 'Active',
  'sum_insured_type': 'Fixed',
  'tax_gst_rate': 18},
 {'claim_process_type': 'Hybrid',
  'coverage_type': 'Indemnity',
  'free_look_period_days': 15,
  'grace_period_days': 30,
  'gst_applicable': 1,
  'line_of_business': 'Health',
  'maximum_age': 65,
  'maximum_sum_assured': 10000000,
  'minimum_age': 18,
  'minimum_sum_assured': 300000,
  'policy_term_months': 12,
  'policy_type': 'Individual / Family Floater',
  'pre_existing_waiting': 36,
  'premium_basis': 'Age Band',
  'premium_frequency': 'Annually',
  'product_category': 'Retail',
  'provider': 'PROV-NIA',
  'renewable_age_limit': 99,
  'renewal_allowed': 1,
  'scheme_code': 'NIA-HLTH-GOLD',
  'scheme_id': 'SCH-NIA-HLTH-GOLD',
  'scheme_name': 'New India Health Gold',
  'status': 'Active',
  'sum_insured_type': 'Floater',
  'target_audience': 'Families',
  'tax_gst_rate': 18,
  'waiting_period_days': 30},
 {'claim_process_type': 'Cashless',
  'coverage_type': 'Indemnity',
  'free_look_period_days': 15,
  'grace_period_days': 30,
  'gst_applicable': 1,
  'line_of_business': 'Health',
  'maximum_age': 65,
  'maximum_sum_assured': 5000000,
  'minimum_age': 18,
  'minimum_sum_assured': 200000,
  'policy_term_months': 12,
  'policy_type': 'Individual',
  'pre_existing_waiting': 36,
  'premium_basis': 'Age Band',
  'premium_frequency': 'Annually',
  'product_category': 'Retail',
  'provider': 'PROV-NIA',
  'renewable_age_limit': 99,
  'renewal_allowed': 1,
  'scheme_code': 'NIA-HLTH-SILVER',
  'scheme_id': 'SCH-NIA-HLTH-SILVER',
  'scheme_name': 'New India Health Silver',
  'status': 'Active',
  'sum_insured_type': 'Per Member',
  'target_audience': 'Individuals',
  'tax_gst_rate': 18,
  'waiting_period_days': 30},
 {'claim_process_type': 'Reimbursement',
  'coverage_type': 'Indemnity',
  'free_look_period_days': 0,
  'grace_period_days': 30,
  'gst_applicable': 1,
  'line_of_business': 'Auto',
  'maximum_age': None,
  'maximum_sum_assured': 5000000,
  'minimum_age': None,
  'minimum_sum_assured': 50000,
  'policy_term_months': 12,
  'policy_type': 'Comprehensive',
  'pre_existing_waiting': 0,
  'premium_basis': 'Sum Insured',
  'premium_frequency': 'Annually',
  'product_category': 'Retail',
  'provider': 'PROV-NIA',
  'renewable_age_limit': None,
  'renewal_allowed': 1,
  'scheme_code': 'NIA-MOTOR-COMP',
  'scheme_id': 'SCH-NIA-MOTOR-COMP',
  'scheme_name': 'New India Motor Comprehensive',
  'status': 'Active',
  'sum_insured_type': 'Fixed',
  'target_audience': 'Individuals',
  'tax_gst_rate': 18,
  'waiting_period_days': 0},
 {'claim_process_type': 'Reimbursement',
  'coverage_type': 'Indemnity',
  'grace_period_days': 30,
  'gst_applicable': 1,
  'line_of_business': 'Property',
  'maximum_sum_assured': 50000000,
  'minimum_sum_assured': 500000,
  'policy_term_months': 12,
  'policy_type': 'Home / Dwelling',
  'premium_basis': 'Sum Insured',
  'premium_frequency': 'Annually',
  'product_category': 'Retail',
  'provider': 'PROV-NIA',
  'renewal_allowed': 1,
  'scheme_code': 'NIA-FIRE',
  'scheme_id': 'SCH-NIA-FIRE',
  'scheme_name': 'New India Bharat Griha Raksha',
  'status': 'Active',
  'sum_insured_type': 'Fixed',
  'tax_gst_rate': 18}]

AGENTS = [{'agent_code': 'AGT-MUM-001',
  'agent_name': 'Rajesh Sharma',
  'agent_type': 'Agent',
  'default_commission_rate': 12.5,
  'email': 'rajesh.sharma@vivaswan.in',
  'license_number': 'IRDAI-AG-MH-2018-04521',
  'linked_provider': 'PROV-STAR',
  'phone': '+91-98200-10001'},
 {'agent_code': 'AGT-DEL-002',
  'agent_name': 'Priya Malhotra',
  'agent_type': 'Agent',
  'default_commission_rate': 15.0,
  'email': 'priya.malhotra@vivaswan.in',
  'license_number': 'IRDAI-AG-DL-2019-07832',
  'linked_provider': 'PROV-HDFC',
  'phone': '+91-98101-20002'},
 {'agent_code': 'AGT-BLR-003',
  'agent_name': 'Suresh Nair',
  'agent_type': 'Broker',
  'default_commission_rate': 18.0,
  'email': 'suresh.nair@vivaswan.in',
  'license_number': 'IRDAI-BR-KA-2020-01245',
  'linked_provider': 'PROV-ICICI',
  'phone': '+91-98450-30003'},
 {'agent_code': 'AGT-CHN-004',
  'agent_name': 'Lakshmi Iyer',
  'agent_type': 'Agent',
  'default_commission_rate': 12.0,
  'email': 'lakshmi.iyer@vivaswan.in',
  'license_number': 'IRDAI-AG-TN-2017-03318',
  'linked_provider': 'PROV-BAJAJ',
  'phone': '+91-98400-40004'},
 {'agent_code': 'AGT-HYD-005',
  'agent_name': 'Venkat Reddy',
  'agent_type': 'Corporate Agent',
  'default_commission_rate': 10.0,
  'email': 'venkat.reddy@vivaswan.in',
  'license_number': 'IRDAI-CA-TS-2021-05677',
  'linked_provider': 'PROV-NIA',
  'phone': '+91-98490-50005'},
 {'agent_code': 'AGT-PUN-006',
  'agent_name': 'Anjali Desai',
  'agent_type': 'Agent',
  'default_commission_rate': 14.0,
  'email': 'anjali.desai@vivaswan.in',
  'license_number': 'IRDAI-AG-MH-2022-08901',
  'linked_provider': 'PROV-HDFC',
  'phone': '+91-98220-60006'},
 {'agent_code': 'AGT-KOL-007',
  'agent_name': 'Amit Banerjee',
  'agent_type': 'Agent',
  'default_commission_rate': 13.0,
  'email': 'amit.banerjee@vivaswan.in',
  'license_number': 'IRDAI-AG-WB-2018-02219',
  'linked_provider': 'PROV-STAR',
  'phone': '+91-98300-70007'},
 {'agent_code': 'AGT-AHM-008',
  'agent_name': 'Kiran Patel',
  'agent_type': 'Broker',
  'default_commission_rate': 16.0,
  'email': 'kiran.patel@vivaswan.in',
  'license_number': 'IRDAI-BR-GJ-2019-04102',
  'linked_provider': 'PROV-ICICI',
  'phone': '+91-98250-80008'},
 {'agent_code': 'AGT-JAI-009',
  'agent_name': 'Sunita Sharma',
  'agent_type': 'Agent',
  'default_commission_rate': 12.0,
  'email': 'sunita.sharma@vivaswan.in',
  'license_number': 'IRDAI-AG-RJ-2020-05512',
  'linked_provider': 'PROV-BAJAJ',
  'phone': '+91-98290-90009'},
 {'agent_code': 'AGT-LKO-010',
  'agent_name': 'Rahul Verma',
  'agent_type': 'Agent',
  'default_commission_rate': 11.5,
  'email': 'rahul.verma@vivaswan.in',
  'license_number': 'IRDAI-AG-UP-2019-03344',
  'linked_provider': 'PROV-NIA',
  'phone': '+91-94150-10010'},
 {'agent_code': 'AGT-CHD-011',
  'agent_name': 'Neha Kapoor',
  'agent_type': 'Agent',
  'default_commission_rate': 13.5,
  'email': 'neha.kapoor@vivaswan.in',
  'license_number': 'IRDAI-AG-CH-2021-06789',
  'linked_provider': 'PROV-HDFC',
  'phone': '+91-98720-11011'},
 {'agent_code': 'AGT-COK-012',
  'agent_name': 'Arun Menon',
  'agent_type': 'Broker',
  'default_commission_rate': 17.0,
  'email': 'arun.menon@vivaswan.in',
  'license_number': 'IRDAI-BR-KL-2018-02156',
  'linked_provider': 'PROV-STAR',
  'phone': '+91-98470-12012'},
 {'agent_code': 'AGT-IND-013',
  'agent_name': 'Pooja Jain',
  'agent_type': 'Agent',
  'default_commission_rate': 12.0,
  'email': 'pooja.jain@vivaswan.in',
  'license_number': 'IRDAI-AG-MP-2022-07890',
  'linked_provider': 'PROV-ICICI',
  'phone': '+91-98260-13013'},
 {'agent_code': 'AGT-NAG-014',
  'agent_name': 'Sandeep Kulkarni',
  'agent_type': 'Agent',
  'default_commission_rate': 14.5,
  'email': 'sandeep.kulkarni@vivaswan.in',
  'license_number': 'IRDAI-AG-MH-2020-04421',
  'linked_provider': 'PROV-BAJAJ',
  'phone': '+91-98230-14014'},
 {'agent_code': 'AGT-CBE-015',
  'agent_name': 'Divya Krishnan',
  'agent_type': 'Corporate Agent',
  'default_commission_rate': 10.0,
  'email': 'divya.krishnan@vivaswan.in',
  'license_number': 'IRDAI-CA-TN-2021-09123',
  'linked_provider': 'PROV-NIA',
  'phone': '+91-98420-15015'},
 {'agent_code': 'AGT-MUM-016',
  'agent_name': 'Vikram Shah',
  'agent_type': 'Agent',
  'default_commission_rate': 15.0,
  'email': 'vikram.shah@vivaswan.in',
  'license_number': 'IRDAI-AG-MH-2019-05678',
  'linked_provider': 'PROV-HDFC',
  'phone': '+91-98200-16016'},
 {'agent_code': 'AGT-DEL-017',
  'agent_name': 'Meera Chopra',
  'agent_type': 'Agent',
  'default_commission_rate': 13.0,
  'email': 'meera.chopra@vivaswan.in',
  'license_number': 'IRDAI-AG-DL-2020-03456',
  'linked_provider': 'PROV-STAR',
  'phone': '+91-98101-17017'},
 {'agent_code': 'AGT-BLR-018',
  'agent_name': 'Karthik Rao',
  'agent_type': 'Broker',
  'default_commission_rate': 16.5,
  'email': 'karthik.rao@vivaswan.in',
  'license_number': 'IRDAI-BR-KA-2022-01234',
  'linked_provider': 'PROV-ICICI',
  'phone': '+91-98450-18018'},
 {'agent_code': 'AGT-HYD-019',
  'agent_name': 'Srinivas Reddy',
  'agent_type': 'Agent',
  'default_commission_rate': 12.5,
  'email': 'srinivas.reddy@vivaswan.in',
  'license_number': 'IRDAI-AG-TS-2018-07812',
  'linked_provider': 'PROV-BAJAJ',
  'phone': '+91-98490-19019'},
 {'agent_code': 'AGT-PUN-020',
  'agent_name': 'Sneha Joshi',
  'agent_type': 'Agent',
  'default_commission_rate': 14.0,
  'email': 'sneha.joshi@vivaswan.in',
  'license_number': 'IRDAI-AG-MH-2021-04567',
  'linked_provider': 'PROV-NIA',
  'phone': '+91-98220-20020'},
 {'agent_code': 'AGT-AHM-021',
  'agent_name': 'Hardik Mehta',
  'agent_type': 'Agent',
  'default_commission_rate': 13.0,
  'email': 'hardik.mehta@vivaswan.in',
  'license_number': 'IRDAI-AG-GJ-2020-06789',
  'linked_provider': 'PROV-HDFC',
  'phone': '+91-98250-21021'},
 {'agent_code': 'AGT-KOL-022',
  'agent_name': 'Rituparna Das',
  'agent_type': 'Agent',
  'default_commission_rate': 12.0,
  'email': 'rituparna.das@vivaswan.in',
  'license_number': 'IRDAI-AG-WB-2019-02345',
  'linked_provider': 'PROV-STAR',
  'phone': '+91-98300-22022'},
 {'agent_code': 'AGT-CHN-023',
  'agent_name': 'Balaji Iyer',
  'agent_type': 'Broker',
  'default_commission_rate': 17.0,
  'email': 'balaji.iyer@vivaswan.in',
  'license_number': 'IRDAI-BR-TN-2021-05678',
  'linked_provider': 'PROV-ICICI',
  'phone': '+91-98400-23023'},
 {'agent_code': 'AGT-JAI-024',
  'agent_name': 'Asha Gupta',
  'agent_type': 'Agent',
  'default_commission_rate': 11.0,
  'email': 'asha.gupta@vivaswan.in',
  'license_number': 'IRDAI-AG-RJ-2022-08901',
  'linked_provider': 'PROV-BAJAJ',
  'phone': '+91-98290-24024'},
 {'agent_code': 'AGT-LKO-025',
  'agent_name': 'Ankit Pandey',
  'agent_type': 'Agent',
  'default_commission_rate': 12.5,
  'email': 'ankit.pandey@vivaswan.in',
  'license_number': 'IRDAI-AG-UP-2020-01234',
  'linked_provider': 'PROV-NIA',
  'phone': '+91-94150-25025'}]

HOSPITALS = [{'address': 'Road No. 72, Film Nagar, Jubilee Hills, Hyderabad 500033',
  'city': 'Hyderabad',
  'hospital_name': 'Apollo Hospitals, Jubilee Hills',
  'phone': '+91-40-23607777',
  'provider': 'PROV-STAR',
  'specialties': 'Cardiology, Oncology, Orthopaedics, Neurology, Transplant',
  'tpa': 'PROV-MEDI'},
 {'address': 'Sector 44, Opposite HUDA City Centre, Gurugram 122002',
  'city': 'Gurugram',
  'hospital_name': 'Fortis Memorial Research Institute',
  'phone': '+91-124-4962200',
  'provider': 'PROV-HDFC',
  'specialties': 'Cardiology, Oncology, Neurosciences, Organ Transplant',
  'tpa': 'PROV-MEDI'},
 {'address': '98, HAL Old Airport Road, Kodihalli, Bengaluru 560017',
  'city': 'Bengaluru',
  'hospital_name': 'Manipal Hospital, Old Airport Road',
  'phone': '+91-80-25024444',
  'provider': 'PROV-ICICI',
  'specialties': 'Cardiology, Orthopaedics, Oncology, Gastroenterology',
  'tpa': 'PROV-PARAM'},
 {'address': '1, 2, Press Enclave Road, Saket, New Delhi 110017',
  'city': 'Delhi',
  'hospital_name': 'Max Super Speciality Hospital, Saket',
  'phone': '+91-11-26515050',
  'provider': 'PROV-BAJAJ',
  'specialties': 'Cardiology, Oncology, Neurosciences, Orthopaedics',
  'tpa': 'PROV-MEDI'},
 {'address': 'A-791, Bandra Reclamation, Bandra West, Mumbai 400050',
  'city': 'Mumbai',
  'hospital_name': 'Lilavati Hospital and Research Centre',
  'phone': '+91-22-26751000',
  'provider': 'PROV-STAR',
  'specialties': 'Cardiology, Oncology, Orthopaedics, Nephrology',
  'tpa': 'PROV-PARAM'},
 {'address': 'Ida Scudder Road, Vellore 632004, Tamil Nadu',
  'city': 'Vellore',
  'hospital_name': 'Christian Medical College (CMC)',
  'phone': '+91-416-2281000',
  'provider': 'PROV-NIA',
  'specialties': 'Multi-speciality, Transplant, Oncology',
  'tpa': 'PROV-MEDI'},
 {'address': 'Rao Saheb Achutrao Patwardhan Marg, Four Bungalows, Andheri West, Mumbai 400053',
  'city': 'Mumbai',
  'hospital_name': 'Kokilaben Dhirubhai Ambani Hospital',
  'phone': '+91-22-42696969',
  'provider': 'PROV-HDFC',
  'specialties': 'Cardiology, Oncology, Neurosciences, Transplant',
  'tpa': 'PROV-MEDI'},
 {'address': 'No. 43/2, New Airport Road, NH 7, Hebbal, Bengaluru 560092',
  'city': 'Bengaluru',
  'hospital_name': 'Aster CMI Hospital',
  'phone': '+91-80-43420100',
  'provider': 'PROV-ICICI',
  'specialties': 'Cardiology, Orthopaedics, Gastroenterology, Paediatrics',
  'tpa': 'PROV-PARAM'},
 {'address': 'CH Baktawar Singh Road, Sector 38, Gurugram 122001',
  'city': 'Gurugram',
  'hospital_name': 'Medanta - The Medicity',
  'phone': '+91-124-4141414',
  'provider': 'PROV-BAJAJ',
  'specialties': 'Cardiology, Oncology, Neurosciences, Transplant, Orthopaedics',
  'tpa': 'PROV-MEDI'},
 {'address': 'Veer Savarkar Marg, Mahim, Mumbai 400016',
  'city': 'Mumbai',
  'hospital_name': 'P. D. Hinduja Hospital',
  'phone': '+91-22-24449199',
  'provider': 'PROV-STAR',
  'specialties': 'Cardiology, Oncology, Nephrology, Orthopaedics',
  'tpa': 'PROV-PARAM'},
 {'address': 'Sion-Trombay Road, Chembur, Mumbai 400071',
  'city': 'Mumbai',
  'hospital_name': 'Apollo Spectra Hospitals, Chembur',
  'phone': '+91-22-6280-4444',
  'provider': 'PROV-HDFC',
  'specialties': 'Orthopaedics, General Surgery, ENT, Gynaecology',
  'tpa': 'PROV-MEDI'},
 {'address': '258/A, Bommasandra Industrial Area, Hosur Road, Bengaluru 560099',
  'city': 'Bengaluru',
  'hospital_name': 'Narayana Health City',
  'phone': '+91-80-71222222',
  'provider': 'PROV-NIA',
  'specialties': 'Cardiac Sciences, Oncology, Neurosciences, Transplant',
  'tpa': 'PROV-MEDI'},
 {'address': 'Ansari Nagar, New Delhi 110029',
  'city': 'Delhi',
  'hospital_name': 'AIIMS New Delhi',
  'phone': '+91-11-26588500',
  'provider': 'PROV-NIA',
  'specialties': 'Multi-speciality, Trauma, Oncology, Cardiology',
  'tpa': 'PROV-MEDI'},
 {'address': 'Dr. E Borges Road, Parel, Mumbai 400012',
  'city': 'Mumbai',
  'hospital_name': 'Tata Memorial Hospital',
  'phone': '+91-22-24177000',
  'provider': 'PROV-STAR',
  'specialties': 'Oncology, Radiation, Surgical Oncology',
  'tpa': 'PROV-PARAM'},
 {'address': 'Rajinder Nagar, New Delhi 110060',
  'city': 'Delhi',
  'hospital_name': 'Sir Ganga Ram Hospital',
  'phone': '+91-11-25750000',
  'provider': 'PROV-ICICI',
  'specialties': 'Cardiology, Gastroenterology, Orthopaedics, Nephrology',
  'tpa': 'PROV-MEDI'},
 {'address': 'Ponekkara, Kochi 682041, Kerala',
  'city': 'Kochi',
  'hospital_name': 'Amrita Institute of Medical Sciences',
  'phone': '+91-484-2851234',
  'provider': 'PROV-BAJAJ',
  'specialties': 'Cardiology, Transplant, Oncology, Neurosciences',
  'tpa': 'PROV-PARAM'},
 {'address': 'Plot No. 30-C, Erandwane, Karve Road, Pune 411004',
  'city': 'Pune',
  'hospital_name': 'Sahyadri Super Speciality Hospital',
  'phone': '+91-20-67213000',
  'provider': 'PROV-HDFC',
  'specialties': 'Cardiology, Orthopaedics, Neurology, Oncology',
  'tpa': 'PROV-MEDI'},
 {'address': '40, Sassoon Road, Pune 411001',
  'city': 'Pune',
  'hospital_name': 'Ruby Hall Clinic',
  'phone': '+91-20-26123391',
  'provider': 'PROV-ICICI',
  'specialties': 'Cardiology, Oncology, Orthopaedics, IVF',
  'tpa': 'PROV-PARAM'},
 {'address': '21, Greams Lane, Off Greams Road, Chennai 600006',
  'city': 'Chennai',
  'hospital_name': 'Apollo Hospitals, Greams Road',
  'phone': '+91-44-28290200',
  'provider': 'PROV-STAR',
  'specialties': 'Cardiology, Oncology, Transplant, Orthopaedics',
  'tpa': 'PROV-MEDI'},
 {'address': '154/9, Bannerghatta Road, Opposite IIM-B, Bengaluru 560076',
  'city': 'Bengaluru',
  'hospital_name': 'Fortis Hospital, Bannerghatta Road',
  'phone': '+91-80-66214444',
  'provider': 'PROV-BAJAJ',
  'specialties': 'Cardiology, Orthopaedics, Neurosciences, Oncology',
  'tpa': 'PROV-PARAM'},
 {'address': 'Road No. 1, Banjara Hills, Hyderabad 500034',
  'city': 'Hyderabad',
  'hospital_name': 'Care Hospitals, Banjara Hills',
  'phone': '+91-40-30418888',
  'provider': 'PROV-NIA',
  'specialties': 'Cardiology, Critical Care, Orthopaedics, Nephrology',
  'tpa': 'PROV-MEDI'},
 {'address': 'Near Maharaja Agrasen Road, Memnagar, Ahmedabad 380052',
  'city': 'Ahmedabad',
  'hospital_name': 'Sterling Hospital',
  'phone': '+91-79-40011111',
  'provider': 'PROV-HDFC',
  'specialties': 'Cardiology, Oncology, Orthopaedics, Gastroenterology',
  'tpa': 'PROV-PARAM'},
 {'address': '360, Panchasayar, Kolkata 700094',
  'city': 'Kolkata',
  'hospital_name': 'Peerless Hospital',
  'phone': '+91-33-40111222',
  'provider': 'PROV-STAR',
  'specialties': 'Cardiology, Oncology, Orthopaedics, Neurology',
  'tpa': 'PROV-MEDI'},
 {'address': '15, Dr. G. Deshmukh Marg, Pedder Road, Mumbai 400026',
  'city': 'Mumbai',
  'hospital_name': 'Jaslok Hospital',
  'phone': '+91-22-66573333',
  'provider': 'PROV-ICICI',
  'specialties': 'Cardiology, Oncology, Neurosciences, Transplant',
  'tpa': 'PROV-PARAM'},
 {'address': '26/4, Brigade Gateway, Beside Metro, Malleshwaram West, Bengaluru 560055',
  'city': 'Bengaluru',
  'hospital_name': 'Columbia Asia Hospital, Yeshwanthpur',
  'phone': '+91-80-39898969',
  'provider': 'PROV-BAJAJ',
  'specialties': 'Orthopaedics, Maternity, Paediatrics, General Surgery',
  'tpa': 'PROV-MEDI'},
 {'address': '1-8-31/1, Minister Road, Secunderabad 500003',
  'city': 'Hyderabad',
  'hospital_name': 'KIMS Hospitals, Secunderabad',
  'phone': '+91-40-44885000',
  'provider': 'PROV-NIA',
  'specialties': 'Cardiology, Orthopaedics, Oncology, Neurosciences',
  'tpa': 'PROV-PARAM'},
 {'address': '35, Dr. E. Borges Road, Hospital Avenue, Parel, Mumbai 400012',
  'city': 'Mumbai',
  'hospital_name': 'Global Hospitals, Parel',
  'phone': '+91-22-67676767',
  'provider': 'PROV-STAR',
  'specialties': 'Liver Transplant, Gastroenterology, Oncology',
  'tpa': 'PROV-MEDI'},
 {'address': 'Pusa Road, Rajendra Place, New Delhi 110005',
  'city': 'Delhi',
  'hospital_name': 'BLK-Max Super Speciality Hospital',
  'phone': '+91-11-30403040',
  'provider': 'PROV-HDFC',
  'specialties': 'Cardiology, Oncology, Neurosciences, Orthopaedics',
  'tpa': 'PROV-PARAM'},
 {'address': 'Raj Bhavan Road, Somajiguda, Hyderabad 500082',
  'city': 'Hyderabad',
  'hospital_name': 'Yashoda Hospitals, Somajiguda',
  'phone': '+91-40-45674567',
  'provider': 'PROV-ICICI',
  'specialties': 'Cardiology, Oncology, Orthopaedics, Transplant',
  'tpa': 'PROV-MEDI'},
 {'address': 'No.1, Jawaharlal Nehru Salai, Vadapalani, Chennai 600026',
  'city': 'Chennai',
  'hospital_name': 'SRM Institutes for Medical Science (SIMS)',
  'phone': '+91-44-30603060',
  'provider': 'PROV-BAJAJ',
  'specialties': 'Cardiology, Orthopaedics, Neurosciences, Oncology',
  'tpa': 'PROV-PARAM'}]


DIAGNOSES = [
	"Acute Myocardial Infarction (I21.9)",
	"Type 2 Diabetes Mellitus with complications (E11.9)",
	"Fracture of shaft of femur (S72.3)",
	"Acute Appendicitis (K35.8)",
	"Pneumonia, unspecified organism (J18.9)",
	"Cholelithiasis with acute cholecystitis (K80.0)",
	"Cataract, unspecified (H26.9)",
	"Hypertensive heart disease (I11.9)",
	"Chronic kidney disease, stage 4 (N18.4)",
	"Road traffic accident - multiple injuries",
	"Dengue fever (A90)",
	"COVID-19, virus identified (U07.1)",
	"Osteoarthritis of knee (M17.9)",
	"Normal delivery (O80)",
	"Hernia, inguinal (K40.9)",
]


def _exists(doctype: str, filters: dict) -> bool:
	return bool(frappe.db.exists(doctype, filters))


def _insert(doctype: str, data: dict, unique_filters: dict | None = None) -> str | None:
	"""Insert if not exists. Returns name or None if skipped."""
	if unique_filters and _exists(doctype, unique_filters):
		return frappe.db.get_value(doctype, unique_filters, "name")
	doc = frappe.get_doc({"doctype": doctype, **data})
	doc.insert(ignore_permissions=True, ignore_mandatory=True)
	return doc.name


def _random_name() -> str:
	return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def _random_address() -> str:
	city, state = random.choice(CITIES)
	area = random.choice(STREET_AREAS)
	flat = random.randint(1, 40)
	building = random.randint(1, 200)
	return f"Flat {flat}, Building {building}, {area}, {city}, {state} - {random.randint(110000, 600000)}"


def _random_phone() -> str:
	return f"+91-{random.randint(70000, 99999)}-{random.randint(10000, 99999)}"


def _random_email(name: str) -> str:
	slug = name.lower().replace(" ", ".")
	domains = ["gmail.com", "yahoo.co.in", "outlook.com", "rediffmail.com", "hotmail.com"]
	return f"{slug}{random.randint(1, 99)}@{random.choice(domains)}"


def _date_between(start: date, end: date) -> str:
	delta = (end - start).days
	return str(start + timedelta(days=random.randint(0, max(delta, 0))))


def _commit_every(n: int, counter: list):
	"""counter is a 1-element list used as mutable int."""
	counter[0] += 1
	if counter[0] % n == 0:
		frappe.db.commit()


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------

def seed_providers():
	created = 0
	for row in INDIAN_PROVIDERS:
		name = _insert(
			"Insurance Provider",
			row,
			{"provider_id": row["provider_id"]},
		)
		if name:
			created += 1
	return created


def seed_schemes():
	"""2–4 schemes per underwriting provider (skip pure TPA/Reinsurer)."""
	created = 0
	for row in SCHEMES:
		if not _exists("Insurance Provider", {"provider_id": row["provider"]}):
			continue
		# strip None values that would fail insert
		clean = {k: v for k, v in row.items() if v is not None}
		name = _insert(
			"Insurance Scheme",
			clean,
			{"scheme_id": row["scheme_id"]},
		)
		if name:
			created += 1
	return created


def seed_agents():
	created = 0
	for row in AGENTS:
		data = dict(row)
		data["status"] = "Active"
		data["license_valid_upto"] = str(add_months(getdate(nowdate()), 24))
		name = _insert(
			"Insurance Agent",
			data,
			{"agent_code": row["agent_code"]},
		)
		if name:
			created += 1
	return created


def seed_hospitals():
	created = 0
	for row in HOSPITALS:
		data = dict(row)
		data["cashless"] = 1
		data["status"] = "Active"
		data["empanelment_from"] = "2022-01-01"
		data["empanelment_to"] = "2028-12-31"
		if _exists("Network Hospital", {"hospital_name": row["hospital_name"], "city": row["city"]}):
			continue
		_insert("Network Hospital", data)
		created += 1
	return created


def seed_clients(count: int = 800):
	"""Create Indian clients across lifecycle stages (default 800 = 20× original 40)."""
	stages = [
		"Prospect", "Qualified", "Quoted", "Policyholder", "Active",
		"At Risk", "Renewal Due", "Lapsed", "Advocate",
	]
	sources = ["CRM Lead", "Walk-in", "Referral", "Website", "Partner"]
	created = 0
	batch = [0]
	for i in range(1, count + 1):
		client_id = f"CLT-DEMO-{i:04d}"
		if _exists("Insurance Client", {"client_id": client_id}):
			continue
		full_name = _random_name()
		stage = stages[i % len(stages)]
		data = {
			"client_id": client_id,
			"full_name": full_name,
			"client_type": random.choice(["Individual", "Individual", "Family", "Corporate"]),
			"email": _random_email(full_name),
			"phone": _random_phone(),
			"date_of_birth": _date_between(date(1960, 1, 1), date(2000, 12, 31)),
			"address": _random_address(),
			"lifecycle_stage": stage,
			"source": random.choice(sources),
			"agent": random.choice(AGENTS)["agent_code"],
			"kyc_status": random.choice(["Pending", "Submitted", "Verified", "Verified", "Verified"]),
			"risk_category": random.choice(["Low", "Medium", "High"]),
			"high_value": 1 if i % 7 == 0 else 0,
			"email_opt_in": 1,
			"sms_opt_in": 1,
			"whatsapp_opt_in": 1 if i % 3 == 0 else 0,
			"consent_data_processing": 1,
			"consent_marketing": 1 if i % 2 == 0 else 0,
			"consent_share_tpa": 1,
			"notes": f"Demo client seeded for Indian market testing. City context: {random.choice(CITIES)[0]}.",
		}
		_insert("Insurance Client", data, {"client_id": client_id})
		created += 1
		_commit_every(100, batch)
	return created


def seed_policies(count: int = 600):
	"""Policies distributed across schemes (~75% of client base)."""
	clients = frappe.get_all(
		"Insurance Client",
		filters={"client_id": ["like", "CLT-DEMO-%"]},
		fields=["name", "client_id", "full_name", "agent"],
		limit=count + 50,
	)
	schemes = frappe.get_all(
		"Insurance Scheme",
		filters={"scheme_id": ["like", "SCH-%"]},
		fields=["name", "scheme_id", "provider", "scheme_name", "line_of_business"],
	)
	if not clients or not schemes:
		return 0

	statuses = ["Active", "Active", "Active", "Active", "Grace Period", "Lapsed", "Expired", "Draft"]
	levels = ["Basic", "Standard", "Premium", "Platinum"]
	freqs = ["Annually", "Semi-Annually", "Quarterly", "Monthly"]
	created = 0
	batch = [0]

	for i in range(1, count + 1):
		policy_number = f"POL-DEMO-2024-{i:04d}"
		if _exists("Insurance Policy", {"policy_number": policy_number}):
			continue
		client = clients[i % len(clients)]
		# Round-robin schemes so distribution is even across products
		scheme = schemes[i % len(schemes)]
		start = getdate(_date_between(date(2023, 1, 1), date(2025, 6, 1)))
		end = add_months(start, 12)
		sum_assured = random.choice([300000, 500000, 750000, 1000000, 1500000, 2000000, 5000000])
		premium = round(sum_assured * random.uniform(0.008, 0.035), 0)
		gst = round(premium * 0.18, 0)
		comm_rate = random.choice([10, 12, 12.5, 15, 18])
		data = {
			"policy_number": policy_number,
			"client": client.name,
			"scheme": scheme.name,
			"provider": scheme.provider,
			"policy_type": random.choice(["New Business", "New", "Renewal"]),
			"coverage_level": random.choice(levels),
			"sum_assured": sum_assured,
			"premium_amount": premium,
			"premium_frequency": random.choice(freqs),
			"start_date": str(start),
			"end_date": str(end),
			"renewal_date": str(end),
			"status": statuses[i % len(statuses)],
			"agent": client.agent or random.choice(AGENTS)["agent_code"],
			"commission_rate": comm_rate,
			"commission_amount": round(premium * comm_rate / 100, 0),
			"issue_date": str(start),
			"tax_amount": gst,
			"total_premium": premium + gst,
			"next_premium_due": str(add_months(start, random.choice([1, 3, 6, 12]))),
			"payment_status": random.choice(["Paid", "Paid", "Partially Paid", "Unpaid", "Overdue"]),
			"notes": f"Demo policy – {scheme.scheme_name} for {client.full_name}.",
		}
		if i % 5 == 0 and _exists("Insurance Provider", {"provider_id": "PROV-GIPSA"}):
			data["reinsurance_type"] = "Treaty"
			data["reinsurer"] = "PROV-GIPSA"
			data["cession_percentage"] = random.choice([20, 25, 30, 40])
		_insert("Insurance Policy", data, {"policy_number": policy_number})
		created += 1
		_commit_every(100, batch)
	return created


def seed_claims(count: int = 150):
	"""~25% of policies have claims."""
	policies = frappe.get_all(
		"Insurance Policy",
		filters={"policy_number": ["like", "POL-DEMO-%"], "status": ["in", ["Active", "Grace Period", "Claimed"]]},
		fields=["name", "policy_number", "client", "provider", "scheme", "agent", "sum_assured"],
		limit=count + 50,
	)
	hospitals = frappe.get_all("Network Hospital", fields=["name", "hospital_name"], limit=50)
	if not policies:
		return 0

	claim_types = ["Cashless", "Reimbursement", "Hospitalization", "Accident", "Other"]
	statuses = [
		"Draft", "Submitted", "Under Review", "Documents Pending",
		"Approved", "Partially Approved", "Rejected", "Settled", "Closed",
	]
	created = 0
	batch = [0]

	for i in range(1, count + 1):
		claim_number = f"CLM-DEMO-2025-{i:04d}"
		if _exists("Insurance Claim", {"claim_number": claim_number}):
			continue
		pol = policies[i % len(policies)]
		claimed = round(random.uniform(15000, min(float(pol.sum_assured or 500000), 400000)), 0)
		status = statuses[i % len(statuses)]
		approved = 0
		settled = 0
		if status in ("Approved", "Settled", "Closed"):
			approved = round(claimed * random.uniform(0.7, 1.0), 0)
			settled = approved if status in ("Settled", "Closed") else 0
		elif status == "Partially Approved":
			approved = round(claimed * random.uniform(0.4, 0.7), 0)
		elif status == "Rejected":
			approved = 0

		incident = getdate(_date_between(date(2024, 6, 1), date(2026, 8, 1)))
		submission = add_days(incident, random.randint(1, 14))

		data = {
			"claim_number": claim_number,
			"policy_source": "Internal",
			"policy": pol.name,
			"client": pol.client,
			"provider": pol.provider,
			"scheme": pol.scheme,
			"claim_type": random.choice(claim_types),
			"incident_date": str(incident),
			"submission_date": str(submission),
			"reported_date": str(add_days(incident, random.randint(0, 3))),
			"claimed_amount": claimed,
			"approved_amount": approved,
			"settled_amount": settled,
			"status": status,
			"agent": pol.agent,
			"adjuster": random.choice(["Anil Kumar", "Sneha Gupta", "Vikram Singh", "Meera Joshi"]),
			"intimation_mode": random.choice(["Portal", "Phone", "Email", "TPA", "Branch"]),
			"description": f"Demo claim for incident on {incident}. Diagnosis: {random.choice(DIAGNOSES)}.",
			"diagnosis": random.choice(DIAGNOSES),
			"deductible": random.choice([0, 0, 5000, 10000]),
			"co_pay": 0,
			"currency": "INR",
			"settlement_mode": "Bank Transfer" if settled else None,
			"settlement_reference": f"UTR{random.randint(100000000, 999999999)}" if settled else None,
			"settlement_date": str(add_days(submission, random.randint(7, 45))) if settled else None,
		}
		if hospitals and random.random() > 0.3:
			h = random.choice(hospitals)
			data["hospital"] = h.name
			data["admission_date"] = str(incident)
			data["discharge_date"] = str(add_days(incident, random.randint(1, 8)))
		if status == "Rejected":
			data["rejection_reason"] = random.choice([
				"Pre-existing condition not disclosed",
				"Waiting period not completed",
				"Documents incomplete / not submitted in time",
				"Treatment not covered under policy terms",
				"Policy not active on date of incident",
			])
			data["decision"] = "Reject"
		elif status in ("Approved", "Settled", "Closed"):
			data["decision"] = "Approve"
		elif status == "Partially Approved":
			data["decision"] = "Partial Approve"

		_insert("Insurance Claim", data, {"claim_number": claim_number})
		created += 1
		_commit_every(50, batch)
	return created


def seed_opportunities_and_quotations(count: int = 200):
	"""Seed opportunities + quotations proportional to client volume."""
	created_opp = 0
	created_quo = 0
	if not frappe.db.exists("DocType", "Insurance Opportunity"):
		return 0, 0

	clients = frappe.get_all(
		"Insurance Client",
		filters={"client_id": ["like", "CLT-DEMO-%"]},
		fields=["name", "full_name", "agent"],
		limit=count + 20,
	)
	schemes = frappe.get_all(
		"Insurance Scheme",
		filters={"scheme_id": ["like", "SCH-%"]},
		fields=["name", "scheme_id", "provider", "scheme_name"],
		limit=50,
	)
	if not clients or not schemes:
		return 0, 0

	stages = ["Open", "Qualified", "Proposal", "Negotiation", "Won", "Lost"]
	batch = [0]
	for i in range(1, count + 1):
		client = clients[i % len(clients)]
		scheme = schemes[i % len(schemes)]
		opp_name = f"OPP-DEMO-{i:04d}"
		if not _exists("Insurance Opportunity", {"name": opp_name}):
			try:
				opp = frappe.get_doc({
					"doctype": "Insurance Opportunity",
					"name": opp_name,
					"client": client.name,
					"scheme": scheme.name,
					"provider": scheme.provider,
					"status": stages[i % len(stages)],
					"expected_premium": random.choice([15000, 25000, 40000, 60000, 100000]),
					"notes": f"Demo opportunity for {client.full_name} – {scheme.scheme_name}",
					"agent": client.agent,
				})
				opp.insert(ignore_permissions=True, ignore_mandatory=True)
				created_opp += 1
			except Exception:
				pass

		if frappe.db.exists("DocType", "Insurance Quotation"):
			quo_no = f"QUO-DEMO-{i:04d}"
			if not _exists("Insurance Quotation", {"name": quo_no}) and not _exists(
				"Insurance Quotation", {"quotation_number": quo_no}
			):
				try:
					quo = frappe.get_doc({
						"doctype": "Insurance Quotation",
						"quotation_number": quo_no,
						"client": client.name,
						"scheme": scheme.name,
						"provider": scheme.provider,
						"sum_assured": random.choice([500000, 1000000, 2000000]),
						"premium_amount": random.choice([12000, 18000, 28000, 45000]),
						"status": random.choice(["Draft", "Sent", "Accepted", "Rejected", "Expired"]),
						"valid_till": str(add_days(getdate(nowdate()), 30)),
						"agent": client.agent,
					})
					quo.insert(ignore_permissions=True, ignore_mandatory=True)
					created_quo += 1
				except Exception:
					pass
		_commit_every(50, batch)
	return created_opp, created_quo


def seed_grievances(count: int = 50):
	if not frappe.db.exists("DocType", "Insurance Grievance"):
		return 0
	clients = frappe.get_all(
		"Insurance Client",
		filters={"client_id": ["like", "CLT-DEMO-%"]},
		fields=["name", "full_name"],
		limit=count + 20,
	)
	if not clients:
		return 0
	created = 0
	subjects = [
		"Delay in claim settlement",
		"Incorrect premium deduction",
		"Network hospital cashless denial",
		"Policy document not received",
		"Agent mis-selling complaint",
		"KYC update pending for long",
		"Renewal notice not sent",
		"Partial claim amount without explanation",
	]
	for i in range(1, count + 1):
		client = clients[i % len(clients)]
		try:
			doc = frappe.get_doc({
				"doctype": "Insurance Grievance",
				"client": client.name,
				"subject": subjects[i % len(subjects)],
				"description": f"Demo grievance from {client.full_name}. Customer requested resolution within IRDAI TAT.",
				"status": random.choice(["Open", "In Progress", "Resolved", "Closed"]),
				"priority": random.choice(["Low", "Medium", "High"]),
				"source": random.choice(["Portal", "Email", "Phone", "Branch", "IRDAI"]),
			})
			doc.insert(ignore_permissions=True, ignore_mandatory=True)
			created += 1
		except Exception:
			pass
	return created


def seed_commission_rules():
	if not frappe.db.exists("DocType", "Commission Rule"):
		return 0
	created = 0
	rules = [
		{"rule_name": "Health New Business – Standard", "event": "Issue", "line_of_business": "Health", "rate": 15.0},
		{"rule_name": "Health Renewal", "event": "Renewal", "line_of_business": "Health", "rate": 7.5},
		{"rule_name": "Motor Comprehensive", "event": "Issue", "line_of_business": "Auto", "rate": 12.0},
		{"rule_name": "Collection Incentive", "event": "Collection", "line_of_business": "Health", "rate": 2.0},
		{"rule_name": "Travel New Business", "event": "Issue", "line_of_business": "Travel", "rate": 20.0},
		{"rule_name": "Property New Business", "event": "Issue", "line_of_business": "Property", "rate": 10.0},
	]
	for r in rules:
		try:
			if _exists("Commission Rule", {"rule_name": r["rule_name"]}):
				continue
			doc = frappe.get_doc({"doctype": "Commission Rule", **r, "status": "Active"})
			doc.insert(ignore_permissions=True, ignore_mandatory=True)
			created += 1
		except Exception:
			pass
	return created


def seed_reinsurance_treaty():
	if not frappe.db.exists("DocType", "Reinsurance Treaty"):
		return 0
	if _exists("Reinsurance Treaty", {"name": ["like", "%GIC%"]}) or _exists(
		"Reinsurance Treaty", {"treaty_name": "GIC Quota Share Health 2025"}
	):
		return 0
	try:
		doc = frappe.get_doc({
			"doctype": "Reinsurance Treaty",
			"treaty_name": "GIC Quota Share Health 2025",
			"treaty_type": "Quota Share",
			"reinsurer": "PROV-GIPSA",
			"cession_percentage": 25,
			"effective_from": "2025-01-01",
			"effective_to": "2025-12-31",
			"status": "Active",
			"notes": "Demo treaty – 25% quota share with GIC Re for health portfolio.",
		})
		doc.insert(ignore_permissions=True, ignore_mandatory=True)
		return 1
	except Exception:
		return 0


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

# Scale factors relative to original 40 clients
CLIENT_COUNT = 800          # 20 × 40
POLICY_COUNT = 600          # ~75% of clients
CLAIM_COUNT = 150           # ~25% of policies
OPP_QUO_COUNT = 200         # ~25% of clients
GRIEVANCE_COUNT = 50        # ~6% of clients


def install_demo_data(force: bool = False) -> dict:
	"""
	Install bulky Indian-context demo data.

	Volumes (defaults):
	  - ~20 schemes (2–4 per underwriting provider)
	  - 800 clients, 600 policies, 150 claims
	  - 200 opportunities/quotations, 50 grievances
	  - 25 agents, 30 network hospitals

	Idempotent: skips existing unique keys.
	"""
	frappe.flags.in_import = True
	summary = {}

	try:
		summary["providers"] = seed_providers()
		summary["schemes"] = seed_schemes()
		summary["agents"] = seed_agents()
		summary["hospitals"] = seed_hospitals()
		summary["clients"] = seed_clients(CLIENT_COUNT)
		summary["policies"] = seed_policies(POLICY_COUNT)
		summary["claims"] = seed_claims(CLAIM_COUNT)
		opp, quo = seed_opportunities_and_quotations(OPP_QUO_COUNT)
		summary["opportunities"] = opp
		summary["quotations"] = quo
		summary["grievances"] = seed_grievances(GRIEVANCE_COUNT)
		summary["commission_rules"] = seed_commission_rules()
		summary["reinsurance_treaties"] = seed_reinsurance_treaty()

		frappe.db.commit()
	finally:
		frappe.flags.in_import = False

	return summary


@frappe.whitelist()
def install_demo_data_from_ui():
	"""Whitelisted entry for Desk / portal prompt."""
	if not frappe.has_permission("Insurance Settings", "write") and "System Manager" not in frappe.get_roles():
		frappe.throw("Not permitted to install demo data", frappe.PermissionError)
	summary = install_demo_data()
	frappe.msgprint(
		title="Demo Data Installed",
		msg=(
			"<p>Indian-context demo data has been seeded (scaled volumes).</p>"
			f"<ul>"
			f"<li>Providers: {summary.get('providers', 0)}</li>"
			f"<li>Schemes: {summary.get('schemes', 0)} (2–4 per underwriting provider)</li>"
			f"<li>Agents: {summary.get('agents', 0)}</li>"
			f"<li>Network Hospitals: {summary.get('hospitals', 0)}</li>"
			f"<li>Clients: {summary.get('clients', 0)}</li>"
			f"<li>Policies: {summary.get('policies', 0)} (distributed across schemes)</li>"
			f"<li>Claims: {summary.get('claims', 0)}</li>"
			f"<li>Opportunities: {summary.get('opportunities', 0)}</li>"
			f"<li>Quotations: {summary.get('quotations', 0)}</li>"
			f"<li>Grievances: {summary.get('grievances', 0)}</li>"
			f"</ul>"
		),
		indicator="green",
	)
	return summary


def maybe_prompt_and_install():
	"""
	Called from after_install. If running in an interactive CLI, ask the user.
	Non-interactive (CI / silent) installs skip demo data.
	"""
	try:
		import click
	except ImportError:
		return

	import sys
	if not sys.stdin.isatty():
		return

	try:
		if click.confirm(
			"\\n  Install Indian-context demo / sample data for Insurance Core?\\n"
			"  (~800 clients, 600 policies, 150 claims, 20 schemes across providers)\\n"
			"  You can also install later via: bench execute insurance_core.demo_data.install_demo_data",
			default=False,
		):
			click.echo("  Seeding demo data (this may take a few minutes)…")
			summary = install_demo_data()
			click.echo(f"  Done. Summary: {summary}")
		else:
			click.echo("  Skipping demo data.")
	except Exception as e:
		try:
			frappe.logger("insurance_core").warning(f"Demo data prompt/install skipped: {e}")
		except Exception:
			pass
