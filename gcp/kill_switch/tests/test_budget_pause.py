"""Exercise budget handling without modifying any real cloud service."""
import base64
import json
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from gcp.kill_switch import main
from google.cloud import run_v2

class BudgetPauseTests(unittest.TestCase):
    def event(self, cost):
        payload = base64.b64encode(json.dumps({"costAmount": cost, "budgetAmount": 1}).encode()).decode()
        return SimpleNamespace(data={"message": {"data": payload}})

    @patch.object(main.run_v2, "ServicesClient")
    def test_threshold_uses_manual_zero_and_preserves_revision_limit(self, factory):
        service = run_v2.Service(name="projects/test/locations/test/services/test")
        service.template.scaling.max_instance_count = 1
        factory.return_value.get_service.return_value = service
        main.handle_budget_alert(self.event(1))
        args = factory.return_value.update_service.call_args.kwargs
        self.assertEqual(args["service"].scaling.scaling_mode, run_v2.ServiceScaling.ScalingMode.MANUAL)
        self.assertEqual(args["service"].scaling.manual_instance_count, 0)
        self.assertEqual(args["service"].template.scaling.max_instance_count, 1)
        self.assertEqual(list(args["update_mask"].paths), ["scaling"])
        factory.return_value.update_service.return_value.result.assert_called_once_with(timeout=120)

    @patch.object(main.run_v2, "ServicesClient")
    def test_below_threshold_does_not_contact_cloud(self, factory):
        main.handle_budget_alert(self.event(0.5))
        factory.assert_not_called()

    @patch.object(main.run_v2, "ServicesClient")
    def test_transient_failure_is_raised_for_retry(self, factory):
        factory.return_value.get_service.side_effect = RuntimeError("synthetic failure")
        with self.assertRaises(RuntimeError):
            main.handle_budget_alert(self.event(1))
