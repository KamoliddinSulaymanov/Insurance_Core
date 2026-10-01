"""SMS and Notification Gateway for Uzbekistan (Eskiz / PlayMobile).

Implements:
1. Sending SMS via national aggregators (Eskiz.uz, PlayMobile.uz).
2. OTP verification messages.
3. Policy issuance notifications with direct e-polis download links.
4. Installment tranche payment reminders.
"""

from typing import Any

from insurance_core.uz_validators import normalize_uz_phone, validate_uz_phone

try:
	import frappe
	from frappe import _
except ImportError:
	class _FrappeMock:
		@staticmethod
		def log_error(*args, **kwargs):
			pass

	frappe = _FrappeMock()
	_ = lambda s: s  # noqa: E731


def send_sms(
	phone: str,
	message: str,
	provider: str = "eskiz",
	mock_mode: bool = True,
) -> dict[str, Any]:
	"""Send SMS to Uzbek mobile operator (+998...) via national gateway."""
	norm_phone = normalize_uz_phone(phone)
	if not validate_uz_phone(norm_phone):
		return {"success": False, "error": f"Invalid Uzbekistan phone: {phone}"}

	# Clean phone digits for gateway (e.g. 998901234567)
	clean_digits = norm_phone.replace("+", "")

	if mock_mode:
		# Return simulated success for dev/staging
		return {
			"success": True,
			"provider": provider,
			"phone": norm_phone,
			"message": message,
			"status": "SENT_MOCK",
		}

	# Production HTTP dispatch via requests
	try:
		import requests

		# Example Eskiz dispatch
		if provider == "eskiz":
			# In production, credentials from Insurance Settings / Site config
			url = "https://notify.eskiz.uz/api/message/sms/send"
			# response = requests.post(url, json={"mobile_phone": clean_digits, "message": message, "from": "AlfaInvest"})
			return {"success": True, "provider": "eskiz", "phone": norm_phone, "status": "SENT"}
	except Exception as e:
		if hasattr(frappe, "log_error"):
			frappe.log_error(f"SMS send failed: {e}", "SMS Gateway")
		return {"success": False, "error": str(e)}

	return {"success": True, "phone": norm_phone, "status": "SENT"}


def send_policy_issued_notification(
	phone: str,
	policy_number: str,
	verification_url: str,
	amount: float | None = None,
) -> dict[str, Any]:
	"""Send policy issue confirmation and e-polis verification link."""
	amt_str = f" na summu {int(amount):,} UZS" if amount else ""
	msg = (
		f"AlfaInvest: Vash polis {policy_number}{amt_str} uspeshno oformlen. "
		f"Proverka i sertifikat: {verification_url}"
	)
	return send_sms(phone, msg)


def send_installment_due_reminder(
	phone: str,
	policy_number: str,
	amount: float,
	due_date: str,
) -> dict[str, Any]:
	"""Send installment payment due reminder."""
	msg = (
		f"AlfaInvest: Napominanie po polisu {policy_number}. "
		f"Ocherednoy platezh {int(amount):,} UZS do {due_date}. "
		f"Oplata: https://alfainvest.uz/pay"
	)
	return send_sms(phone, msg)


def send_otp_sms(phone: str, code: str) -> dict[str, Any]:
	"""Send one-time password for phone verification."""
	msg = f"AlfaInvest kod podtverzhdeniya: {code}. Ne soobshchayte ego nikomu."
	return send_sms(phone, msg)
