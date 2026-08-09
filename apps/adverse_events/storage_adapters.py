import hashlib
import hmac
import time
from abc import ABC, abstractmethod

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse


class StorageAdapterError(RuntimeError): pass


class PrivateObjectStorage(ABC):
    @abstractmethod
    def save(self,key,file_obj,metadata=None,encryption=None): ...
    @abstractmethod
    def open(self,key): ...
    @abstractmethod
    def signed_url(self,key,*,expires_in,subject_id): ...
    @abstractmethod
    def logical_delete(self,key): ...
    @abstractmethod
    def destroy(self,key): ...
    @abstractmethod
    def exists(self,key): ...
    @abstractmethod
    def metadata(self,key): ...


class LocalPrivateStorageAdapter(PrivateObjectStorage):
    def __init__(self,attachment): self.attachment=attachment
    def save(self,key,file_obj,metadata=None,encryption=None): return self.attachment.file.storage.save(key,file_obj)
    def open(self,key): return self.attachment.file.storage.open(key,"rb")
    def signed_url(self,key,*,expires_in,subject_id):
        expires=int(time.time())+expires_in; payload=f"{key}:{subject_id}:{expires}".encode(); secret=settings.SECRET_KEY.encode(); token=hmac.new(secret,payload,hashlib.sha256).hexdigest()
        return f"{reverse('attachment_download',args=[self.attachment.pk])}?expires={expires}&subject={subject_id}&signature={token}"
    def logical_delete(self,key): return True
    def destroy(self,key): self.attachment.file.storage.delete(key)
    def exists(self,key): return self.attachment.file.storage.exists(key)
    def metadata(self,key): return {"name":key,"size":self.attachment.file.storage.size(key),"sha256":self.attachment.sha256,"mime":self.attachment.detected_mime}

    @staticmethod
    def verify_signed_request(key,*,expires,subject_id,signature):
        if int(expires)<int(time.time()): return False
        payload=f"{key}:{subject_id}:{expires}".encode(); expected=hmac.new(settings.SECRET_KEY.encode(),payload,hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected,signature)


class ExternalObjectStorageAdapter(PrivateObjectStorage):
    """Cloud-neutral contract. A deployment plugin supplies the actual SDK client."""
    def __init__(self,client=None): self.client=client
    def _client(self):
        if not self.client: raise ImproperlyConfigured("객체 저장소 client adapter가 구성되지 않았습니다.")
        return self.client
    def save(self,key,file_obj,metadata=None,encryption=None): return self._client().put(key,file_obj,bucket=settings.OBJECT_STORAGE_BUCKET,metadata=metadata or {},encryption=encryption or {"kms_key_id":settings.OBJECT_STORAGE_KMS_KEY_ID})
    def open(self,key): return self._client().open(key,bucket=settings.OBJECT_STORAGE_BUCKET)
    def signed_url(self,key,*,expires_in,subject_id): return self._client().signed_url(key,bucket=settings.OBJECT_STORAGE_BUCKET,expires_in=expires_in,subject_id=subject_id)
    def logical_delete(self,key): return self._client().tag(key,bucket=settings.OBJECT_STORAGE_BUCKET,tags={"deleted":"true"})
    def destroy(self,key): return self._client().delete(key,bucket=settings.OBJECT_STORAGE_BUCKET)
    def exists(self,key): return self._client().exists(key,bucket=settings.OBJECT_STORAGE_BUCKET)
    def metadata(self,key): return self._client().metadata(key,bucket=settings.OBJECT_STORAGE_BUCKET)
