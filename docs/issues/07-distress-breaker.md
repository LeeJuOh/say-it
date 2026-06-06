Status: ready-for-agent
Blocked by: 01-hook-infra

# 디스트레스 서킷브레이커 (HARD + SOFT)

## What to build

2층 감지 + 2등급 대응. ADR 0003 구현.

### 감지 2층

- **HARD 바닥**: hook 키워드 regex (매 턴, 명백 신호 무조건 트리거, 우회 불가, 한국어 로케일)
- **SOFT 보강**: 프롬프트 레이어 (변주·맥락 잡음 — "숨이 안 쉬어져", "다 끝내고 싶어" 등)

### 대응 2등급 + 파이프라인

- **① 일반 패닉**("무서워/너무 힘들어") → hook이 system-reminder로 `DISTRESS_GRADE_1` 주입 → **모델이** 세션 중단 + 진정/마무리 렌더. 모델 의존이지만 갓 주입된 fresh 명령이라 context-rot 안 걸림.
- **② 급성 위해**(자해·자살 암시) → hook이 system-reminder로 `DISTRESS_GRADE_2` + 위기 핫라인 정보 주입 + session_state를 `BLOCKED`로 갱신 → **모델이** 핫라인 안내 렌더 + 이후 세션 재개 시 hook이 `BLOCKED` 상태 감지하고 차단.

핵심: **detection은 hook(HARD)**, **enforcement 렌더는 모델** — 단 갓 주입된 authoritative system-reminder라 모델 선의 의존과 다름 (ADR 0004 패턴).

### 우선순위

**디스트레스 > 턴캡(이슈 04) > 단계 전환.** 디스트레스 발동 시 다른 가드 무관하게 즉시 중단.

핫라인 = 치료 아니라 한계 인정·주의의무. "치료 아님" 프레임과 충돌 안 함.

### SKILL.md 영향

기존 `/say-it` SKILL.md에 추가 — 디스트레스 system-reminder 해석 + 등급별 렌더 지침 (Grade 1: 진정/마무리, Grade 2: 핫라인).

## Acceptance criteria

- [ ] HARD regex가 명백 디스트레스 키워드 감지 (한국어)
- [ ] HARD regex가 정상 분출/카타르시스에 오발 안 함 (false positive 테스트)
- [ ] Grade 1: hook이 DISTRESS_GRADE_1 system-reminder 주입 → 모델이 진정/마무리
- [ ] Grade 2: hook이 DISTRESS_GRADE_2 + 핫라인 주입 + state BLOCKED → 모델이 핫라인 렌더
- [ ] BLOCKED 상태에서 세션 재개 시 hook이 차단
- [ ] 한국어 위기 핫라인 번호 포함
- [ ] SOFT 프롬프트 레이어가 변주 표현 감지
- [ ] 유닛테스트: true positive, false positive(정상 분출), 등급 라우팅 정확도
