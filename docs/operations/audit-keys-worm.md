# 감사 HMAC 키와 WORM/SIEM 복제

## 키 생성·회전·보관

키는 CSPRNG로 생성하고 KMS 또는 secret manager에 보관합니다. DB, 코드, 이미지와 로그에 원문을 기록하지 않습니다. `AUDIT_HMAC_KEYS`에는 배포 시 secret manager가 제공한 `key_id: key` JSON을 주입하고 `AUDIT_ACTIVE_KEY_ID`로 활성 키를 지정합니다.

회전 절차:

1. 새 key ID와 키를 secret manager에 추가합니다.
2. 과거 키와 새 키를 모두 제공한 채 활성 ID만 새 값으로 배포합니다.
3. `python manage.py check_audit_key_rotation`을 실행합니다.
4. 새 로그가 새 ID를 사용하는지 확인합니다.
5. 과거 키는 해당 로그 보존기간 동안 검증 가능하게 보관합니다. 기존 로그는 재작성하거나 재서명하지 않습니다.
6. 키 폐기는 법무·RA·QA·보안 승인을 받은 정책에 따릅니다. 키가 없으면 검증 결과는 `KEY_UNAVAILABLE`입니다.

## 무결성 검증과 외부 복제

`python manage.py verify_audit_chain`을 정기 실행하고 결과를 별도 보안 저장소에 남깁니다. 감사 로그 생성과 같은 트랜잭션에서 outbox가 생성되며, `export_audit_outbox` 또는 별도 worker가 외부 WORM/SIEM adapter로 전송합니다. JSONL exporter는 개발·테스트용이며 WORM이 아닙니다. 운영에서는 idempotency key를 지원하는 adapter로 교체합니다.

외부 복제 실패는 원본 로그를 변경하거나 삭제하지 않습니다. `FAILED` 이벤트는 경보와 수동 재처리 대상입니다.
