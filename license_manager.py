"""
Wriggle Survey — License Manager
"""
import hashlib
import os
from pathlib import Path

SALT = "WriggleSurvey_2025_FCelik"
APP_NAME = "WriggleSurvey"

VALID_KEY_HASHES = {
    "c8cadd86354304888d1f49eccdc1ada313533b41675110b33e4733836fef412f",
    "3f1446bd5088781df8f5ac5f52259e2609528637fd2739191f9d7ed2cf6a2490",
    "b5684a76e593c1c303c369dc90c88e25b7c44133982d13553b4308d34d71b679",
    "16b0c99738211152c5949a86cc1f2fb7fae9db977fcadae8411636b12537d8a2",
    "c4064cddf370a359fd562f5a5e4f49a879901035c75446faf37ff79581e76c6f",
    "2c6c90fd74baf47b8dadc5668a9a91e656ecb649f32193de6ec7adaf6a4ab8d5",
    "6be05db95fd52a5a1c739dd1ee006ec6e1f92cb01167a9335e7ae919a0998567",
    "1e931160e045629aaebb45fe872d67d1911d397af8a19217e9e2e1a6258d48d4",
    "c1cdaa30b9a85a2b03a3756f0c65f9a16adfa1952085271c3aab460d9e78846d",
    "5328a02ca96e6748a51f1b32c6cb61199c014ee9eece7c7d7872e0e30d011f0e",
    "7305e73a329eedc1221d864d2da3e657e8ff79ff463df2f99162fbc212260130",
    "9bff3bbac431f0a50957f329d44357a3c43055177107db13ff708fdca8b7c63c",
    "ae2cd60213b1a63a4313b5968fa294ffdc3c80326b74fa7f818dba821aa4d9f4",
    "f4d4282750eff704207bbcf25b0edc190c20d6b46eb45a53c20c23e44e6965f5",
    "6fa09832b69c4db5f7e706f884be20be722be2bdf4efc617b59449e3f636c9a7",
    "6e2c1399866ef4f7e4f745e5f498b57e12002ee7ea858ef5f2bf66f0689e6579",
}


def _activation_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    folder = Path(base) / APP_NAME
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "activation.dat"


def _hash_key(key: str) -> str:
    clean = key.strip().upper().replace(" ", "")
    return hashlib.sha256((clean + SALT).encode()).hexdigest()


def validate_key(key: str) -> bool:
    return _hash_key(key) in VALID_KEY_HASHES


def is_activated() -> bool:
    try:
        p = _activation_path()
        if not p.exists():
            return False
        return p.read_text().strip() in VALID_KEY_HASHES
    except Exception:
        return False


def save_activation(key: str):
    _activation_path().write_text(_hash_key(key))
