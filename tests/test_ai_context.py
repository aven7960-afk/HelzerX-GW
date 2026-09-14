import unittest
from types import SimpleNamespace

from ai.context import conversation_scope


class AIContextTests(unittest.TestCase):
    def test_guild_scope_isolated_by_user_and_channel(self):
        message = SimpleNamespace(
            guild=SimpleNamespace(id=10),
            channel=SimpleNamespace(id=20),
            author=SimpleNamespace(id=30),
        )
        self.assertEqual(conversation_scope(message), "guild:10:channel:20:user:30")

    def test_dm_scope_isolated_by_user(self):
        message = SimpleNamespace(
            guild=None,
            author=SimpleNamespace(id=30),
        )
        self.assertEqual(conversation_scope(message), "dm:user:30")


if __name__ == "__main__":
    unittest.main()
