import unittest

from ai.triggers import has_helzer_trigger, strip_trigger


class TriggerTests(unittest.TestCase):
    def test_trigger_word_is_case_insensitive(self):
        self.assertTrue(has_helzer_trigger("hey HELZER, help me"))

    def test_bot_mention_is_a_trigger(self):
        self.assertTrue(has_helzer_trigger("<@123456> help", 123456))

    def test_trigger_is_removed_from_prompt(self):
        self.assertEqual(strip_trigger("Helzer, mokakda meka?", None), "mokakda meka?")

    def test_unrelated_message_has_no_trigger(self):
        self.assertFalse(has_helzer_trigger("hello everyone"))


if __name__ == "__main__":
    unittest.main()
