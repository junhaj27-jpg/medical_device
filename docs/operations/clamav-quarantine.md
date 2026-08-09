# ClamAV와 격리 파일 운영

업로드 파일은 `QUARANTINED`로 시작하며 `CLEAN` 판정 전에는 다운로드할 수 없습니다. 작업자는 `run_pending_scan_jobs()` 또는 `process_scan_job()`을 호출합니다. Celery 등 큐를 도입할 경우에도 이 서비스만 호출합니다.

- 상태 확인: ClamAV daemon의 3310 포트, signature DB 갱신 시각, 작업자 backlog를 점검합니다.
- 장애: 연결 오류와 timeout은 exponential backoff로 제한 재시도됩니다.
- 최대 실패: `SCAN_FAILED`로 전환하고 다운로드를 계속 차단합니다. 자동 재개하지 말고 장애 원인 확인 후 승인된 재처리 절차를 사용합니다.
- 감염: `INFECTED` 파일은 격리 유지 후 보안 담당자 절차에 따라 파기 요청합니다.
- 테스트: mock scanner가 기본이며 실제 통합 검사는 `RUN_CLAMAV_INTEGRATION=1 pytest -m clamav_integration`으로 별도 실행합니다.

EICAR 문자열은 테스트 코드에서만 사용하며 운영 파일 저장소나 샘플 데이터에 저장하지 않습니다.
