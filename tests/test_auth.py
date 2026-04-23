from corsarioxxx.auth import create_password_record, verify_password


def test_password_roundtrip():
    record = create_password_record("segredo-forte")
    assert verify_password("segredo-forte", record) is True
    assert verify_password("senha-errada", record) is False
