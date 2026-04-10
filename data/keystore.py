"""
keystore.py — encrypted API key storage using Windows DPAPI.

Encryption: CryptProtectData / CryptUnprotectData (Windows built-in, no password).
Keys are tied to the current Windows user account — cannot be decrypted elsewhere.
File: data/keys.enc (binary DPAPI blob)
Dependencies: only ctypes (Python standard library)
"""

import os
import json
import ctypes
import ctypes.wintypes

_PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
KEYSTORE_PATH = os.path.join(_PROJECT_ROOT, "data", "keys.enc")

_crypt  = ctypes.windll.crypt32
_kernel = ctypes.windll.kernel32


class _BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", ctypes.wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def _dpapi_encrypt(data: bytes) -> bytes:
    blob_in  = _BLOB(len(data), ctypes.cast(ctypes.c_char_p(data), ctypes.POINTER(ctypes.c_byte)))
    blob_out = _BLOB()
    ok = _crypt.CryptProtectData(
        ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)
    )
    if not ok:
        raise RuntimeError(f"CryptProtectData failed (error {ctypes.GetLastError()})")
    result = bytes(ctypes.string_at(blob_out.pbData, blob_out.cbData))
    _kernel.LocalFree(blob_out.pbData)
    return result


def _dpapi_decrypt(data: bytes) -> bytes:
    blob_in  = _BLOB(len(data), ctypes.cast(ctypes.c_char_p(data), ctypes.POINTER(ctypes.c_byte)))
    blob_out = _BLOB()
    ok = _crypt.CryptUnprotectData(
        ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)
    )
    if not ok:
        raise RuntimeError(f"CryptUnprotectData failed (error {ctypes.GetLastError()})")
    result = bytes(ctypes.string_at(blob_out.pbData, blob_out.cbData))
    _kernel.LocalFree(blob_out.pbData)
    return result


# ── session (loaded once at startup) ─────────────────────────────────────────

_session: dict = {}


def load_if_exists() -> None:
    """Loads and decrypts keys.enc if the file exists."""
    global _session
    if not os.path.exists(KEYSTORE_PATH):
        _session = {}
        return
    with open(KEYSTORE_PATH, "rb") as f:
        blob = f.read()
    _session = json.loads(_dpapi_decrypt(blob))


def get(key: str, default: str = "") -> str:
    """Returns a key value from the current session."""
    return _session.get(key, default)


def save_all(data: dict) -> None:
    """Encrypts data and writes to keys.enc. Updates the session."""
    global _session
    _session = data
    os.makedirs(os.path.dirname(KEYSTORE_PATH), exist_ok=True)
    with open(KEYSTORE_PATH, "wb") as f:
        f.write(_dpapi_encrypt(json.dumps(data).encode()))
