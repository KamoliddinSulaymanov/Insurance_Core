import unittest

from insurance_core.eis_gateway import (
	generate_qr_svg,
	register_policy_in_eis,
)
from insurance_core.erp_sync import build_policy_accounting_entries
from insurance_core.notifications import (
	send_installment_due_reminder,
	send_policy_issued_notification,
	send_sms,
)


class TestPhase6Integrations(unittest.TestCase):
	def test_eis_gateway_registration_and_qr(self):
		policy = {
			"policy_number": "POL-2026-00099",
			"scheme": "TEST_KASKO",
			"tax_id": "31508900011234",
			"sum_assured": 150000000.0,
			"total_premium": 4500000.0,
			"start_date": "2026-10-01",
			"end_date": "2027-09-30",
		}
		res = register_policy_in_eis(policy)
		self.assertEqual(res["status"], "Registered")
		self.assertTrue(res["eois_registration_number"].startswith("UZ-EOIS-"))
		self.assertIn("https://e-polis.uz/verify", res["verification_url"])
		self.assertIn("<svg", res["qr_svg"])
		self.assertIn("ALFAINVEST", res["qr_svg"])

	def test_notifications_sms_dispatch(self):
		# Standard mock dispatch
		res = send_sms("+998 90 123-45-67", "Test message")
		self.assertTrue(res["success"])
		self.assertEqual(res["phone"], "+998901234567")

		# Invalid number
		res_bad = send_sms("123", "Test message")
		self.assertFalse(res_bad["success"])

		# Policy issued notification
		notif = send_policy_issued_notification(
			phone="901234567",
			policy_number="POL-2026-0001",
			verification_url="https://e-polis.uz/verify?p=1",
			amount=1250000.0,
		)
		self.assertTrue(notif["success"])
		self.assertIn("POL-2026-0001", notif["message"])
		self.assertIn("1,250,000 UZS", notif["message"])

		# Installment reminder notification
		rem = send_installment_due_reminder(
			phone="901234567",
			policy_number="POL-2026-0001",
			amount=625000.0,
			due_date="2026-12-01",
		)
		self.assertTrue(rem["success"])
		self.assertIn("625,000 UZS", rem["message"])

	def test_accounting_erp_sync_balanced_entries(self):
		policy = {
			"policy_number": "POL-2026-00088",
			"client": "CL-001",
			"partner": "B2B-AUTODEALER",
			"total_premium": 2000000.0,
			"commission_amount": 200000.0,
		}
		accounting = build_policy_accounting_entries(policy)
		self.assertTrue(accounting["is_balanced"])
		self.assertEqual(accounting["total_debits"], 2200000.0)
		self.assertEqual(accounting["total_credits"], 2200000.0)
		self.assertEqual(len(accounting["entries"]), 4)


if __name__ == "__main__":
	unittest.main()
