Status: ready-for-agent
Blocked by: 01-hook-infra

# 단계 전환 탐지 + 턴캡

## What to build

### 단계 전환 메커니즘

session_state.json의 stage 값: `vent` → `role-swap` → `integration` → `closure`. 전환 방식:

1. 모델이 전환 시점 판단 (캡 발동, 유저 동의, 단계 완료 등)
2. 모델이 `scripts/transition_stage.sh <next-stage>` 호출
3. 스크립트가 검증 — **앞으로만** (vent→role-swap→integration→closure), 역방향 거부
4. session_state.json stage 값 갱신
5. 다음 턴 hook이 새 stage 읽고 동작

이슈 06의 takeaway 저장과 동일 패턴: 모델→scripts/→상태 파일 갱신.

### 턴캡 (vent 단계 전용)

Hook 레벨 턴캡 강제. **vent 단계에만 적용** — role-swap/integration/closure는 구조화된 단계라 캡 불필요.

8턴 소프트캡(초대 문구로 물음) → 1회 연장(+3턴) → 11턴 하드천장(강제 마무리). 캡 enforce = hook(결정적), 신호 해석(반복·강도↓·포기어) = 프롬프트.

캡 발동 문구 = **초대**("충분히 풀었어, 다음 갈까") not 추방("그만해"). re-suppression(다시 억압) 방지.

### Hook 통신

Hook이 session_state에서 현재 단계 + 턴수 읽음 → vent이고 캡 조건 충족 시 → stdout으로 `CAP_TRIGGERED: SOFT` 또는 `CAP_TRIGGERED: HARD` 포함 system-reminder 주입 → 모델이 초대 문구로 물음(SOFT) 또는 강제 전환(HARD).

### 우선순위

디스트레스(이슈 07)가 턴캡보다 우선. 디스트레스 발동 시 캡 무관하게 즉시 중단.

### SKILL.md 영향

기존 `/say-it` SKILL.md에 추가 — 캡 트리거 system-reminder 해석 + 초대 문구 렌더 지침.

## Acceptance criteria

- [ ] `scripts/transition_stage.sh` 구현 — 앞으로만 전이, 역방향 거부
- [ ] 유닛테스트: 정방향 전이 성공, 역방향 전이 거부, 잘못된 stage명 거부
- [ ] 캡은 vent 단계에서만 카운트
- [ ] 8턴에서 hook이 소프트캡 트리거 → 모델이 초대 스타일로 물음
- [ ] 유저가 연장 선택 시 정확히 1회(+3턴)만 허용
- [ ] 11턴에서 하드천장, 강제 전환
- [ ] 연장은 세션당 1회 초과 불가
- [ ] 유닛테스트: 8턴 발동, 1회만 연장, 11턴 강제
- [ ] 신호 해석(반복/강도/포기어)은 프롬프트 레이어, 스크립트 아님
