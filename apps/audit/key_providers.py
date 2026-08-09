import json
from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


@dataclass(frozen=True)
class KeyMaterial:
    key_id: str
    value: bytes


class HMACKeyProvider:
    def active(self): raise NotImplementedError
    def get(self,key_id): raise NotImplementedError


class EnvironmentHMACKeyProvider(HMACKeyProvider):
    def __init__(self):
        raw=getattr(settings,"AUDIT_HMAC_KEYS","")
        try: self.keys=json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc: raise ImproperlyConfigured("AUDIT_HMAC_KEYS는 JSON 객체여야 합니다.") from exc
        legacy=getattr(settings,"AUDIT_HMAC_KEY","")
        if legacy and "legacy" not in self.keys: self.keys["legacy"]=legacy
        if settings.DEBUG and not self.keys: self.keys["development"]=settings.SECRET_KEY
        self.active_id=getattr(settings,"AUDIT_ACTIVE_KEY_ID","") or (next(iter(self.keys),""))

    def active(self):
        value=self.keys.get(self.active_id)
        if not value: raise ImproperlyConfigured("활성 감사 HMAC 키를 사용할 수 없습니다.")
        return KeyMaterial(self.active_id,value.encode())

    def get(self,key_id):
        value=self.keys.get(key_id)
        return KeyMaterial(key_id,value.encode()) if value else None


def get_key_provider(): return EnvironmentHMACKeyProvider()
