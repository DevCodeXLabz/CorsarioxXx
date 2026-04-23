from __future__ import annotations

import hashlib
import hmac
import os


def create_password_record(password: str) -> dict[str, str]:
    if not password:
        raise ValueError("A senha mestra nao pode ser vazia.")

    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return {
        "salt": salt.hex(),
        "hash": digest.hex(),
        "iterations": "200000",
    }


def verify_password(password: str, record: dict[str, str]) -> bool:
    salt = bytes.fromhex(record["salt"])
    iterations = int(record["iterations"])
    expected = bytes.fromhex(record["hash"])
    current = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(current, expected)
