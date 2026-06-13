Status: ready-for-human
Blocked by: 01-hook-infra, 02-persona-builder, 03-s1-vent, 04-turn-cap, 06-s3-s4-wrapup, 07-distress-breaker, 10-safety-disclosure

# 통합 스모크 eval (전체 세션 워크스루)

## What to build

전체 세션 한 판(빌드→S1→S2→S3→S4) end-to-end 워크스루 eval. 톤·edges·스캐폴딩·매듭 품질 = 주관 영역이라 사람 리뷰 필수.

**eval 세트 다양화 (PRD Testing Decisions):**
- 관계종류: 상사 / 부모 / 연인 / 친구
- 감정결: 분노 / 서러움 / 죄책감 / 무감각
- 분출량: 폭발형 / 말 못 꺼내는형

좁은 eval = 좁은 보장. 다양성 자체가 일반화 동력.

**체크 포인트:**
- 진입: 안전 고지 1회 표시 (치료아님 + "내 인식 속 그 사람" + 힘들면 핫라인, 이슈 10)
- S1: 받는 모드, edges 유지, 공격 안 함
- S2: 역할교대 스캐폴딩, 유저 연기 유도
- S3: 반추→문제해결 전환
- S4: takeaway 품질, 유저 소유, 허구 재확인
- 가드: 턴캡·디스트레스·재방문 가드 정상 동작

## Acceptance criteria

- [ ] 진입 시 안전 고지 표시 확인 (이슈 10)
- [ ] 전체 세션 워크스루가 에러 없이 완료
- [ ] eval이 관계×감정×분출 교차 커버
- [ ] 각 단계 톤 리뷰 통과 (사람 판단)
- [ ] 가드가 트리거 시 정상 발동
- [ ] 사람 sign-off
