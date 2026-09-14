import unittest

from ai.local_provider import choose_local_model, ollama_tools


class LocalAIProviderTests(unittest.TestCase):
    def test_simple_chat_uses_fast_model(self):
        self.assertEqual(choose_local_model("machan kohomada?", has_guild=True), "qwen3:1.7b")

    def test_discord_action_uses_tool_model(self):
        self.assertEqual(choose_local_model("me channel eka lock karanna", has_guild=True), "qwen2.5:7b")

    def test_dm_uses_fast_model(self):
        self.assertEqual(choose_local_model("hello", has_guild=False), "qwen3:1.7b")

    def test_tools_are_converted_to_ollama_chat_schema(self):
        tools = [{
            "type": "function",
            "name": "lock_channel",
            "description": "Lock a channel",
            "parameters": {
                "type": "object",
                "properties": {"channel_id": {"type": "integer"}},
                "required": ["channel_id"],
                "additionalProperties": False,
            },
            "strict": True,
        }]
        converted = ollama_tools(tools)
        self.assertEqual(converted[0]["type"], "function")
        self.assertEqual(converted[0]["function"]["name"], "lock_channel")
        self.assertEqual(converted[0]["function"]["parameters"]["required"], ["channel_id"])


if __name__ == "__main__":
    unittest.main()
