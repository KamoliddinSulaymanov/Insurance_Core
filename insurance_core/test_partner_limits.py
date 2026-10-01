import unittest
from datetime import date
from types import SimpleNamespace

from insurance_core.partner_limits import (
	calculate_available_balance,
	generate_installment_schedule,
)


class TestPartnerLimits(unittest.TestCase):
	def test_calculate_available_balance(self):
		# Case 1: Standard Credit + Deposit - Utilized
		acc = SimpleNamespace(
			sanctioned_credit_limit=10000000.0,
			deposit_balance=5000000.0,
			utilized_limit=3000000.0,
			allow_overdraft=0,
			max_overdraft_amount=0.0,
		)
		avail = calculate_available_balance(acc)
		# 10M + 5M - 3M = 12M
		self.assertEqual(avail, 12000000.0)

		# Case 2: With Overdraft
		acc_overdraft = SimpleNamespace(
			sanctioned_credit_limit=10000000.0,
			deposit_balance=0.0,
			utilized_limit=10000000.0,
			allow_overdraft=1,
			max_overdraft_amount=2000000.0,
		)
		avail2 = calculate_available_balance(acc_overdraft)
		# 10M - 10M + 2M = 2M
		self.assertEqual(avail2, 2000000.0)

	def test_installment_schedule_full_payment(self):
		total = 1500000.0
		schedule = generate_installment_schedule(total, "100% Full Payment", date(2026, 1, 1))
		self.assertEqual(len(schedule), 1)
		self.assertEqual(schedule[0]["amount"], 1500000.0)
		self.assertEqual(schedule[0]["due_date"], "2026-01-01")

	def test_installment_schedule_50_50(self):
		total = 1000001.0  # odd number to verify penny rounding
		schedule = generate_installment_schedule(total, "50/50 Split", date(2026, 1, 15))
		self.assertEqual(len(schedule), 2)
		self.assertEqual(sum(s["amount"] for s in schedule), total)
		self.assertEqual(schedule[0]["amount"], 500000.5)
		self.assertEqual(schedule[1]["amount"], 500000.5)

	def test_installment_schedule_quarterly(self):
		total = 1234567.89
		schedule = generate_installment_schedule(total, "Quarterly (4x25%)", date(2026, 3, 1))
		self.assertEqual(len(schedule), 4)
		# Sum of installments must match total exactly to the cent/tiyin
		total_sum = round(sum(s["amount"] for s in schedule), 2)
		self.assertEqual(total_sum, 1234567.89)

	def test_installment_schedule_monthly(self):
		total = 10000000.0
		schedule = generate_installment_schedule(total, "Monthly (12x)", date(2026, 1, 1))
		self.assertEqual(len(schedule), 12)
		total_sum = round(sum(s["amount"] for s in schedule), 2)
		self.assertEqual(total_sum, 10000000.0)
		# Verify dates sequence
		self.assertEqual(schedule[0]["due_date"], "2026-01-01")
		self.assertEqual(schedule[11]["due_date"], "2026-12-01")


if __name__ == "__main__":
	unittest.main()
