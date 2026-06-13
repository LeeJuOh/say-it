Status: done
Blocked by: None

> **Closed** in commit `aaa1d8a` (feat(hook-infra)). State lib + 3 schemas +
> hook + CLIs + SKILL.md draft + references bundle + 28 unit tests (green).
> Two intentional deviations from the acceptance list below: (a) PRD/ADRs are
> NOT bundled into references/ (runtime never reads them; the build reads them
> in-repo from docs/) — see the note on the references criterion; (b) the
> bundle lives under `skills/say-it/references/`, not repo-root `references/`
> (which is a gitignored symlink to local reference projects). SAFETY.md is a
> stub owned by issue 10. The one remaining check — a live in-context
> confirmation of the system-reminder injection — is left to the human (an
> agent can't reload its own plugins); the hook is verified at the subprocess
> level (valid `hookSpecificOutput.additionalContext`, turn increments, gate
> stays silent when inactive).

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

- [x] UserPromptSubmit hook이 매 유저 메시지마다 실행됨 (hooks.json, no matcher = global)
- [x] session_state.json 생성/갱신: stage(vent/role-swap/integration/closure), turn count, extension flag
- [x] takeaway_log.json: append-only, theme label + takeaway per session
- [x] 매 턴 틱이 turn count를 +1
- [~] Hook stdout → system-reminder로 모델 컨텍스트에 주입 확인 — subprocess 레벨 검증 완료 (valid `hookSpecificOutput.additionalContext`); 라이브 in-context 확인은 human 몫
- [x] persona 파일 JSON 스키마 정의 (5층 + corrections 배열)
- [x] 상태 파일 읽기/쓰기/증분 유닛테스트 (28 tests, green)
- [x] 플러그인 폴더 scaffold 확정 + manifest 생성 (`.claude-plugin/plugin.json`, not `manifest.json` — spec 정정)
- [~] references 번들 — conflict-vocabulary.md ✅ / SAFETY.md stub ✅ / schemas ✅. **PRD·ADR 4개는 의도적 제외** (런타임 미사용, build는 docs/서 직접 읽음 → 중복/드리프트 회피). 위치 = `skills/say-it/references/` (repo-root `references/`는 참고-프로젝트 심링크, gitignore)
- [x] hook 등록 + `/say-it` 활성 시에만 실행 — `hooks/hooks.json` (not settings.json — spec 정정) + `session_state.active` 게이트
