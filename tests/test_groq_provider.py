import unittest

from ai.groq_provider import DEFAULT_MODEL, GroqProvider


class GroqProviderTests(unittest.TestCase):
    def test_default_model(self):
        self.assertEqual(DEFAULT_MODEL, "openai/gpt-oss-20b")

    def test_tools_are_converted_to_chat_completions_schema(self):
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
        converted = GroqProvider.groq_tools(tools)
        self.assertEqual(converted[0]["type"], "function")
        self.assertEqual(converted[0]["function"]["name"], "lock_channel")
        self.assertTrue(converted[0]["function"]["strict"])
        self.assertEqual(
            converted[0]["function"]["parameters"]["required"],
            ["channel_id"],
        )

    def test_no_argument_tool_always_has_object_properties(self):
        tools = [{
            "type": "function",
            "name": "server_info",
            "description": "Get basic server information.",
            "parameters": {
                "type": "object",
                "required": [],
            },
            "strict": True,
        }]
        converted = GroqProvider.groq_tools(tools)
        parameters = converted[0]["function"]["parameters"]
        self.assertEqual(parameters["type"], "object")
        self.assertEqual(parameters["properties"], {})
        self.assertEqual(parameters["required"], [])
        self.assertFalse(parameters["additionalProperties"])

    def test_missing_object_schema_is_normalized(self):
        tools = [{
            "type": "function",
            "name": "server_info",
            "description": "Get basic server information.",
        }]
        converted = GroqProvider.groq_tools(tools)
        parameters = converted[0]["function"]["parameters"]
        self.assertEqual(parameters, {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        })

    def test_tool_result_message_uses_call_id(self):
        message = GroqProvider.tool_result_message(
            {"id": "call_123"},
            {"status": "success"},
        )
        self.assertEqual(message["role"], "tool")
        self.assertEqual(message["tool_call_id"], "call_123")
        self.assertIn("success", message["content"])


if __name__ == "__main__":
    unittest.main()
