# 비공개 객체 저장소와 KMS

업무 코드는 `PrivateObjectStorage` 인터페이스에 의존합니다. 로컬 구현은 개발용 비공개 파일시스템이며, 운영 adapter는 SDK client를 주입해야 합니다. client가 없으면 명시적으로 설정 오류를 반환합니다.

필수 설정 후보:

- `OBJECT_STORAGE_BUCKET`
- `OBJECT_STORAGE_KMS_KEY_ID`
- `SIGNED_URL_EXPIRY_SECONDS` — 최대 900초
- 저장소 접근 역할, 리전, endpoint와 암호화 정책은 외부 secret manager/IAM에서 관리

저장 시 KMS 키 ID와 서버 측 암호화 옵션을 adapter에 전달합니다. 서명 URL은 애플리케이션 권한 확인 후에만 발급하며 발급 기록을 감사 로그에 남깁니다. 버킷은 public access를 차단하고 버전관리, 수명주기, 접근 로그 및 백업 정책을 별도로 구성합니다.
