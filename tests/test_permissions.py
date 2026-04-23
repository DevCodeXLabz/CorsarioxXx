from corsarioxxx.permissions import classify_command


def test_safe_command_is_auto_allowed():
    decision = classify_command("Get-ChildItem")
    assert decision.category == "safe"
    assert decision.requires_confirmation is False


def test_sensitive_command_requires_confirmation():
    decision = classify_command("Remove-Item arquivo.txt")
    assert decision.category == "sensitive"
    assert decision.requires_confirmation is True
