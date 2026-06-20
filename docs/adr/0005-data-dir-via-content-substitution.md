---
status: accepted
date: 2026-06-20
context: say-it (대인관계 빈 의자 세션 스킬) — grill-with-docs 검수서 발견한 P0(프로덕션 데이터디렉토리 해석 실패) 수정 산물. 근거 = 공식문서 plugins-reference("Environment variables" 절) + Bash 툴 env 실측 + ADR 0004(상태·틱 hook 소유)
---

# 데이터 디렉토리는 콘텐츠 치환(`${CLAUDE_PLUGIN_DATA}`)으로 넘긴다 — Bash 툴은 플러그인 env를 못 받는다 (tick hook만 예외)

스킬이 Bash로 호출하는 모든 스크립트(`session_start.py` 등 6개 + `transition_stage.sh` + SKILL.md 인라인 `python3 -c`)는 데이터 디렉토리를 **명시 인자 `--data-dir "${CLAUDE_PLUGIN_DATA}"`로 받는다.** 이 값은 SKILL.md 콘텐츠 안에서 Claude가 읽기 전에 실제 경로로 **치환**되어 명령 문자열에 박힌다. 스크립트는 env(`CLAUDE_PLUGIN_DATA`)를 1차로 신뢰하지 않는다. 단 **`tick.py`(UserPromptSubmit hook)는 env에서 그대로 읽는다** — hook 프로세스는 플러그인 env를 정상 수신하기 때문이다.

근거(공식문서, plugins-reference "Environment variables"): 플러그인 경로 변수들은 "**skill content**, agent content, hook commands, ... 에 inline 치환"되고, env 변수로는 "**hook processes and MCP or LSP server subprocesses**"에만 export된다. **Bash 툴은 env export 대상이 아니다**(`bin/`은 Bash 툴 PATH에 추가된다고 같은 문서가 명시 — 즉 Bash 툴을 알면서도 env-export 목록에서 의도적으로 제외). 따라서 Bash로 불리는 스크립트는 `CLAUDE_PLUGIN_DATA`를 env로 못 받는다. 실측에서도 활성 플러그인 15개 상황의 Bash 툴 env에 `CLAUDE_PLUGIN_*` = 0개였다.

`${CLAUDE_PLUGIN_ROOT}`(스크립트 경로)는 처음부터 SKILL.md 글자에 박혀 치환되어 작동했고, `CLAUDE_PLUGIN_DATA`(데이터 디렉토리)만 env로 읽게 설계돼 깨졌다. **같은 종류 변수를 한쪽은 치환·한쪽은 env로 처리한 비대칭이 P0의 직접 원인**이었다. 미래 정비자가 "왜 데이터 디렉토리만 인자로 넘기지? 그냥 env 변수 아닌가?" 또는 "왜 tick만 env에서 읽지? 통일하자"며 이 수정을 되돌릴 위험이 크므로 기록한다.

## Considered Options

- **A — env만 (수정 전 상태)**: 스크립트가 `st.data_dir()`를 인자 없이 호출, `os.environ`의 `CLAUDE_PLUGIN_DATA`/`SAY_IT_DATA_DIR`에만 의존. Bash 툴 env엔 그 변수가 없음 → `session_start.py` exit 1 → 세션 미시작 → hook 영구 침묵 → 가드·persona·takeaway 전멸. **프로덕션 비작동. 탈락.**
- **B (채택) — 콘텐츠 치환 + `--data-dir` 인자**: SKILL.md 호출부에 `--data-dir "${CLAUDE_PLUGIN_DATA}"`(인라인 `-c`는 `st.data_dir('${CLAUDE_PLUGIN_DATA}')`)를 박고, 각 스크립트 argparse에 `--data-dir`를 신설해 `st.data_dir(args.data_dir)`로 받는다. 문서가 "skill content는 치환된다"고 보장하므로 **spec-guaranteed**. `data_dir(explicit)` 우선순위는 이미 구현돼 있어 함수 변경 없음. `${CLAUDE_PLUGIN_DATA}`는 참조 시점에 디렉토리가 자동 생성된다(문서 명시).
- **C — `bin/` 래퍼가 env export 후 호출**: bin/ 래퍼에서 `SAY_IT_DATA_DIR`를 export하고 실제 스크립트를 부름. 하지만 래퍼도 Bash 툴서 실행 = env 못 받음 → export할 원본 값을 못 구함. **같은 벽. 탈락.**
- **D — 설치 가이드서 수동 export 요구**: 코드 무수정, 유저가 shell에 `SAY_IT_DATA_DIR` export. UX 최악 + 비결정 + 플러그인 자동화 철학 위반. **탈락.**

## Consequences

- **해석 비대칭은 의도적이며 플랫폼 계약을 반영한다**: Bash로 불리는 스크립트 = 인자(치환), `tick.py`(hook) = env. 억지로 통일하면 "hook은 env를 받고 Bash 툴은 못 받는다"는 플랫폼의 실제 차이를 가린다. `tick.py`/`hooks.json`에 이 의도를 주석으로 박는다. `data_dir()`의 우선순위 `explicit > SAY_IT_DATA_DIR > CLAUDE_PLUGIN_DATA`는 유지 — env 경로는 **테스트/개발 오버라이드**와 **hook 수신**용으로 남는다.
- **`SAY_IT_DATA_DIR`(env)는 테스트·dev 전용으로 강등**된다. 프로덕션 정상 경로는 항상 `--data-dir` 명시. 기존 유닛테스트가 P0를 못 잡은 이유 = 데이터 디렉토리를 `SAY_IT_DATA_DIR`로만 주입해 인자 경로를 한 번도 검증 안 함 → `--data-dir` 인자 경로 회귀 테스트를 추가해 이 구멍을 닫는다.
- **`transition_stage.sh` 시그니처가 1→2 인자로 바뀐다**(`<move>` + `<data-dir>`). thin-wrapper 성격 유지 위해 flag가 아닌 위치 인자로 받고 SKILL.md 호출을 짝으로 갱신한다.
- **같은 뿌리 동반 수정**: `session_start.py`/`save_takeaway.py`의 `--session` 기본값이 `CLAUDE_SESSION_ID`(존재 안 함)였다 → 실제 Bash env 이름 `CLAUDE_CODE_SESSION_ID`로 교정. 이건 Bash env에 실재하므로 이름만 고치면 됨(치환 불필요).
- **변경 없는 곳**: `hotline_text()`만 부르는 인라인 `-c`(say-it-build SKILL.md)는 데이터 디렉토리를 안 쓰므로 손대지 않는다.
- ADR 0004(hook이 상태·틱 소유)와 충돌 없음 — 오히려 그 ADR이 박은 "hook은 env 수신" 전제 위에서 비대칭이 정합적이다.
