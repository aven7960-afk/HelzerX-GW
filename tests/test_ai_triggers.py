from ai.triggers import has_helzer_trigger, strip_trigger


def test_trigger_word_is_case_insensitive():
    assert has_helzer_trigger("hey HELZER, help me")


def test_bot_mention_is_a_trigger():
    assert has_helzer_trigger("<@123456> help", 123456)


def test_trigger_is_removed_from_prompt():
    assert strip_trigger("Helzer, mokakda meka?", None) == "mokakda meka?"


def test_unrelated_message_has_no_trigger():
    assert not has_helzer_trigger("hello everyone")
