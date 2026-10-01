import unittest
from types import SimpleNamespace
from unittest.mock import patch

from insurance_core.widget import (
	get_widget_bundle,
	set_cors_headers,
)


class TestWidgetBackend(unittest.TestCase):
	def test_set_cors_headers_no_crash(self):
		set_cors_headers()
		# Should execute safely even without an active HTTP request context

	def test_widget_bundle_defaults(self):
		mock_scheme = SimpleNamespace(
			name="TEST_SCHEME",
			scheme_id="TEST_SCHEME",
			scheme_name="Test Scheme",
			line_of_business="General",
			provider="AlfaInvest",
			order_form_schema=None,
			widget_config=None,
		)
		with patch("insurance_core.widget.frappe.db.exists", return_value=True), \
		     patch("insurance_core.widget.frappe.get_doc", return_value=mock_scheme):
			bundle = get_widget_bundle("TEST_SCHEME")
			self.assertIn("widget_config", bundle)
			self.assertEqual(bundle["widget_config"]["primary_color"], "#D32F2F")
			self.assertIn("order_form_schema", bundle)
			self.assertIsInstance(bundle["order_form_schema"], list)


if __name__ == "__main__":
	unittest.main()
