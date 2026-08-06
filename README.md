# MDSafe — 의료기기 이상사례 및 추적성 관리 시스템

의료기기 회사의 RA·QA 업무를 위한 포트폴리오 웹 애플리케이션입니다. 이상사례 접수, 제품/LOT 추적, 조사, CAPA, 승인, 규제 보고서, DOCX 생성과 감사 로그를 한 흐름으로 관리합니다. 의료 진단이나 환자 대상 의학적 판단은 제공하지 않습니다.

## 주요 기능과 역할

- STAFF: 신규 접수, 제품/LOT 조회, 본인이 접수한 사례 조회
- RA_QA: 검토·분류, 조사와 CAPA, 승인 요청, DOCX 보고서
- ADMIN: 전체 데이터, 사용자, 최종 승인·종료, 감사 로그
- 서비스 계층의 순차 상태 전환, 조사/CAPA 없는 승인 요청 차단, 미승인 종료 차단
- 기한 7일/3일/당일/초과 표시 및 `check_overdue_events`
- DRF API 및 Swagger, Chart.js 대시보드, CSV 내보내기
- 확장자 화이트리스트와 20MB 업로드 제한, 익명 환자 정보만 저장
- 외부 LLM 없이 동작하는 규칙 기반 AI 보조 인터페이스(기본 비활성)

기술 스택은 Python 3.11+, Django 5, DRF, SQLite/PostgreSQL, Django Templates, 직접 작성 CSS, Chart.js, python-docx, pytest, Ruff/Black, Docker입니다. 구조도와 데이터 관계는 [architecture.md](docs/architecture.md), [erd.md](docs/erd.md), [workflow.md](docs/workflow.md)를 참고하세요.

## 로컬 설치

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```

첫 화면은 `http://127.0.0.1:8000/` 로그인 페이지이며 API 문서는 `/api/docs/`입니다. 테스트는 `pytest`, 코드 검사는 `ruff check .`, 포맷은 `black .`로 실행합니다. 기한 초과 점검은 `python manage.py check_overdue_events`입니다.

## Docker

```bash
docker compose up --build
```

Docker 구성은 PostgreSQL 16을 사용합니다. 운영에서는 `.env`의 강력한 `SECRET_KEY`, 실제 호스트, DB 비밀번호를 지정하고 `config.settings.production`을 사용하세요. 이 설정은 HTTPS 강제, Secure 쿠키와 HSTS를 활성화합니다.

## 데모 계정

| 사용자 | 비밀번호 | 역할 |
|---|---|---|
| admin | Admin1234! | ADMIN |
| rauser | Rauser1234! | RA_QA |
| staff | Staff1234! | STAFF |

이 계정은 테스트 전용입니다. 운영 배포 전 반드시 삭제하거나 비밀번호를 변경하세요.

## 폴더 구조

`config/settings`는 local/production 설정을, `apps`는 accounts, devices, adverse_events, investigations, capa, approvals, reports, audit, dashboard, ai_assistant 업무 경계를 담습니다. `templates`, `static`, `media`, `tests`, `docs`는 각각 UI, 자산, 업로드, 자동화 테스트, Mermaid 문서를 담습니다.

## 화면과 보안

로그인 후 역할 범위의 대시보드, 이상사례 검색/CSV/등록/상세, 제품과 LOT, CAPA, API 문서를 이용할 수 있습니다. ADMIN에는 사용자 관리와 감사 로그가 추가됩니다. Django CSRF와 템플릿 자동 이스케이프를 유지하며 서버 측 폼 검증, 역할별 queryset 제한, 해시 비밀번호 저장을 적용합니다. 감사 로그에는 비밀번호와 파일 본문을 저장하지 않습니다. 환자 식별정보는 입력 필드와 모델 모두에 존재하지 않습니다.

## 향후 개선

운영 전에는 객체별 Django Permission 정교화, 동시 번호 발급용 PostgreSQL sequence, 악성 파일 검사, 감사 로그 보존/서명 정책, 규제기관별 제출 어댑터, 비동기 알림과 다국어 DOCX 템플릿을 우선 권장합니다.

## CAPA와 규제 보고서

CAPA는 문제 확인 → 근본 원인 → 시정·예방조치 → 실행 → 검토 → 효과성 평가 → 종료 순서로 관리합니다. 실제 완료일과 진행률 100%가 있어야 완료할 수 있고, 효과성 평가 후 ADMIN이 종료합니다. `INEFFECTIVE` 결과에는 재조치 경고가 표시됩니다. 자세한 흐름은 [capa_workflow.md](docs/capa_workflow.md)를 참고하세요.

규제 보고서는 이상사례 선택 시 제품, LOT, 익명 환자, 조사와 CAPA 내용을 자동 반영합니다. RA_QA가 검토 요청하고 ADMIN이 승인한 뒤 DOCX를 생성하고 제출 완료 처리합니다. 파일은 `media/reports/RPT-연도-순번_v버전.docx`에 버전별로 저장됩니다. 흐름은 [report_workflow.md](docs/report_workflow.md)에 정리했습니다.

STAFF는 관련 기록 조회만 가능하고, RA_QA는 CAPA·보고서 작성과 검토 요청 및 승인된 보고서 제출, ADMIN은 CAPA 종료·재개와 보고서 승인을 담당합니다. 화면 버튼뿐 아니라 View와 서비스 계층에서도 권한을 검증합니다.

샘플 데이터는 `python manage.py seed_demo_data`로 CAPA 8건과 보고서 8건을 멱등 생성합니다. 테스트는 `pytest`로 실행합니다. 본 시스템의 분류·경고·자동 반영 결과는 참고용이며 실제 의료기기 규제 판단은 담당자가 수행해야 합니다.

Windows에서 설치가 끝난 뒤에는 `powershell -ExecutionPolicy Bypass -File .\scripts\run_local.ps1`로 로컬 SQLite 설정의 개발 서버를 실행할 수 있습니다. 스크립트는 Django 검사와 마이그레이션을 수행한 뒤 `127.0.0.1:8000` 서버를 전경에서 유지합니다.
