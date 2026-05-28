import os
import sys
import unittest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from core.custom_test.context import ExecutionContext, StopExecution
from core.custom_test.nodes import PromptUser
from core.custom_test.validation import preflight_validate
from ui.pages.custom_test.node_metadata import STABLE, get_node_status, is_node_selectable


class PromptUserPhase4Test(unittest.TestCase):

    def test_prompt_user_is_selectable_after_ui_prompt_regularization(self):
        self.assertEqual(get_node_status("PromptUser"), STABLE)
        self.assertTrue(is_node_selectable("PromptUser"))

        result = preflight_validate([PromptUser()])

        self.assertFalse(result.has_errors)

    def test_prompt_user_uses_context_prompt_handler(self):
        context = ExecutionContext()
        context.set_prompt_handler(lambda message, timeout_s: "confirmed")
        prompt = PromptUser(result_var="answer")

        prompt.execute(context)

        self.assertEqual(context.get_variable("answer"), "confirmed")

    def test_prompt_user_without_handler_stops_execution(self):
        context = ExecutionContext()
        prompt = PromptUser()

        with self.assertRaises(StopExecution):
            prompt.execute(context)


if __name__ == "__main__":
    unittest.main()
