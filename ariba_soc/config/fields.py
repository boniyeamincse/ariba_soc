"""Encryption-at-rest for model fields, backed directly by `cryptography`'s
Fernet (actively maintained by pyca) instead of django-cryptography, which
is unofficially abandoned upstream and hard-incompatible with Django 5.x
(imports django.utils.baseconv, removed in Django 5.0). Ciphertext is stored
as base64 text, so the underlying DB column stays a plain varchar -- no
custom column type.
"""
import base64
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings
from django.db import models
from django.utils.encoding import force_bytes


@lru_cache(maxsize=1)
def _fernet_key():
    # PBKDF2 (390k iterations) turns settings.CRYPTOGRAPHY_KEY -- an arbitrary
    # length string -- into the 32 url-safe-base64 bytes Fernet requires.
    # Cached: settings.CRYPTOGRAPHY_KEY is fixed for the process lifetime, and
    # this KDF is deliberately slow, so re-deriving on every field read/write
    # would be a real cost at Wazuh-sync/API-call frequency.
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'ariba-soc-field-encryption-v1',
        iterations=390000,
    )
    return base64.urlsafe_b64encode(kdf.derive(force_bytes(settings.CRYPTOGRAPHY_KEY)))


class EncryptedCharField(models.CharField):
    """Transparent encrypt-on-write / decrypt-on-read CharField. Values can't
    be filtered/looked-up on -- Fernet ciphertext is non-deterministic per
    encryption, the same limitation the django-cryptography fields it
    replaces had."""

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if not value:
            return value
        return Fernet(_fernet_key()).encrypt(force_bytes(value)).decode('ascii')

    def from_db_value(self, value, expression, connection):
        if not value:
            return value
        try:
            return Fernet(_fernet_key()).decrypt(force_bytes(value)).decode('utf-8')
        except InvalidToken as e:
            raise ValueError(
                f"Could not decrypt field '{self.name}': wrong DJANGO_CRYPTOGRAPHY_KEY or corrupted data"
            ) from e
