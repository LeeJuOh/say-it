Status: done
Blocked by: 03-s1-vent

> **Closed** in commit `c6b91e5` (feat(correction)). 이미 비어 있던 `corrections`
> 시드를 채우는 작업 — 스키마 변경 없음. `sayit_state.append_correction()` +
> `scripts/save_correction.py` CLI 래퍼가 `append_takeaway` / `save_takeaway`
> 패턴을 그대로 미러. 유저의 "그 사람 안 이래" 피드백은 기존 L0..L4 레이어를 절대
> 건드리지 않고 `corrections` 배열에만 append-only로 쌓임(비파괴 레이어링,
> Decisions §3). 쓰기는 단일 경로 `save_persona`를 타므로 경계에서 한 번
> 검증됨 — `validate_persona`를 항목 단위 검사로 확장(layer enum + note 비어있지
> 않음 + at 타임스탬프, persona.schema.json의 items.required 미러). open question
> 해소: append 헬퍼가 "신뢰"가 아니라 "검증"을 택함 — corrections는 persona 안에
> 살고 그 단일 쓰기 경로가 이미 검증하니, 항목 검증을 그 경계에 넣는 게 일관됨.
> SKILL.md에 트리거 지침 추가: 분쟁 감지 → 대상 레이어 선택 → 유저 표현 raw 저장,
> 그리고 다음 persona load 시 나중 correction이 빌드 레이어를 override 하도록 —
> "적용 안 되는 correction은 로그일 뿐". L0 persona-hold 플래그는 08 범위 아님
> (세션 차단은 이슈 07이 소유) — SKILL.md의 stale 참조도 함께 정정.
> Closed alongside: 89 unit tests green, Hangul gate 0, throwaway-dir smoke
> (두 세션에 걸친 누적 + 원본 레이어 byte-identical 확인).

# 페르소나 교정 (세션 후 피드백)

## What to build

세션 중/후 유저가 "그 사람 안 이래"라고 피드백 → 페르소나 파일 업데이트. 교정은 세션 넘어 누적됨. 점점 유저 인식에 가까워지는 구조.

원본 페르소나 데이터 보존 — 교정은 덮어쓰기가 아니라 레이어로 쌓음(어떤 교정이 언제 왜 들어왔는지 추적 가능).

### SKILL.md 영향

기존 `/say-it` SKILL.md에 추가 — "그 사람 안 이래" 감지 + 교정 flow 트리거 지침.

## Acceptance criteria

- [x] "그 사람 안 이래" 피드백이 교정 흐름 트리거 (SKILL.md 교정 섹션)
- [x] 페르소나 파일에 교정 반영 (`corrections` append + `save_persona` 영속)
- [x] 교정이 세션 간 지속 (별도 CLI 호출=세션 간 누적, smoke 확인)
- [x] 원본 데이터 보존 (교정은 레이어, L0..L4 byte-identical 검증)
