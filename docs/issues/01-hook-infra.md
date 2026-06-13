Status: ready-for-agent
Blocked by: None

# Hook 인프라 + 세션 상태 파일

## What to build

### 스킬 폴더 초기화 + references/ 번들

스킬 폴더 생성 시 `references/`에 빌드 참조 자료 번들:
- PRD.md (기전 표, 아키텍처 결정)
- ADR 0001~0004 (설계 근거)
- conflict-vocabulary.md (갈등 단어표 — 페르소나 빌더가 막연한 라벨→행동 번역에 사용, 이슈 02)
- SAFETY.md (유저 안전 고지문 — 이슈 10)

### Hook 인프라

UserPromptSubmit hook 뼈대 + JSON 상태 파일 3종 스키마 + 매 턴 틱. ADR 0004 구현.

Hook이 유저 메시지마다 자동 실행 → 상태 파일 읽기/쓰기 → authoritative system-reminder를 모델 컨텍스트에 주입. 이 슬라이스가 say-it 전체의 결정적 실행 인프라.

### Hook → 모델 통신 계약

Hook stdout → Claude Code가 `<system-reminder>`로 모델 컨텍스트에 주입 (Claude Code 표준 패턴). Hook은 매 턴:
1. 상태 파일(session_state.json) 읽고 갱신 (턴+1, 단계 확인)
2. 가드 체크 실행 (디스트레스 regex, 턴캡 — 별도 이슈 04, 07에서 구현, 여기선 체크 자리만)
3. 현재 상태 + 가드 결과를 **stdout으로 출력** → system-reminder로 주입

모델은 매 턴 주입된 system-reminder에서 현재 단계·턴수·가드 트리거 여부를 읽고 행동.

### 상태 파일 3종

- **persona (`$CLAUDE_PLUGIN_DATA_DIR/personas/{id}.json`)** — 빌드 산출물 (이 슬라이스에선 스키마만, 실제 생성은 이슈 02). 5층 구조: L0 하드규칙 / L1 정체 / L2 말투 / L3 감정트리거 / L4 관계역학(**양가성/핵심 긴장 필드 포함** — 그 사람 행동의 모순 보존, cf CONTEXT.md). `corrections` 배열로 교정 누적(이슈 08).
- **session_state.json** — 세션 내: 현재 단계(S1-S4), 턴 수, 연장 여부
- **takeaway_log.json** — 세션 간: append-only, 테마 라벨 + takeaway 원문. 읽기=hook(입구 매칭용), **쓰기=모델이 scripts/ 스크립트 호출** (S4 저장 시, 이슈 06 참조)

근거: [ADR 0004](../adr/0004-state-tick-via-hook.md) — 안전 틱(디스트레스 regex)이 hook을 강제 → 턴카운트·캡도 같은 hook에 무임승차.

### SKILL.md 영향

`/say-it` SKILL.md 초안 생성 — hook system-reminder 해석 계약, 상태 파일 읽기 명시.

## Acceptance criteria

- [ ] UserPromptSubmit hook이 매 유저 메시지마다 실행됨
- [ ] session_state.json 생성/갱신: stage(vent/role-swap/integration/closure), turn count, extension flag
- [ ] takeaway_log.json: append-only, theme label + takeaway per session
- [ ] 매 턴 틱이 turn count를 +1
- [ ] Hook stdout → system-reminder로 모델 컨텍스트에 주입 확인
- [ ] persona 파일 JSON 스키마 정의 (5층 + corrections 배열)
- [ ] 상태 파일 읽기/쓰기/증분 유닛테스트
- [ ] 플러그인 폴더 scaffold 확정 + manifest.json 생성
- [ ] references/에 PRD, ADR 4개, conflict-vocabulary.md, SAFETY.md(이슈 10) 번들
- [ ] settings.json에 hook 등록 + `/say-it` 스킬 활성 시에만 실행 조건
