import json
from abc import ABC, abstractmethod
from pathlib import Path


class AuditExporter(ABC):
    @abstractmethod
    def export(self,*,idempotency_key,payload): ...


class LocalJSONLExporter(AuditExporter):
    """Local development/test exporter. This is not WORM storage."""
    def __init__(self,path): self.path=Path(path)
    def export(self,*,idempotency_key,payload):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        record={"idempotency_key":str(idempotency_key),"payload":payload}
        with self.path.open("a",encoding="utf-8") as stream: stream.write(json.dumps(record,sort_keys=True,ensure_ascii=False)+"\n")
        return {"accepted":True}


class ExternalSecurityLogExporter(AuditExporter):
    def __init__(self,client=None): self.client=client
    def export(self,*,idempotency_key,payload):
        if not self.client: raise RuntimeError("외부 WORM/SIEM exporter client가 구성되지 않았습니다.")
        return self.client.send(payload,idempotency_key=str(idempotency_key))
