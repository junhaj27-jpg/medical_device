# PostgreSQL 동시성 테스트

연도별 관리번호의 운영 동시성 검증은 SQLite가 아닌 PostgreSQL에서 수행합니다.

```bash
pytest -m postgres tests/test_compliance_security.py
```

`DJANGO_SETTINGS_MODULE=config.settings.production`과 테스트 전용 `POSTGRES_*` 값을 설정해야 합니다. GitHub Actions의 `postgres-concurrency` job은 PostgreSQL 16 service container와 CI 전용 계정을 사용합니다. 실제 운영 계정이나 비밀값을 CI 파일에 넣지 않습니다. 로컬 DB가 PostgreSQL이 아니면 테스트는 명시적으로 skip됩니다.

검증 대상은 동일 연도 첫 카운터 행 생성 경쟁, 행 잠금, 제한된 `IntegrityError` 재시도, 순번 고유성과 최종 카운터 값입니다.
