---
topic: say-it-plugin-review
date: 2026-06-20
---

# say-it 플러그인 검수 — 완료. 다음 = 발견사항 그릴

## Goal

`say-it` 플러그인 정성 검수(skill-creator-pro 철학 + PRD/ADR 부합 기준)는 **끝났다**.
다음 세션 목표 = 검수에서 나온 **P0 결함 + 개선목록을 그릴**(`/grill-with-docs`)해서
"진짜 결함인가 / 어떻게 고칠 것인가"를 확정한다. 유저가 P0를 아직 납득 못 함 →
그릴 전에 P0를 **실측으로 못박는 것**이 최우선.

검수 방식 = eval 안 돌림. 정성 read-only 평가만. 대화=한국어, 코드/커밋=영어.

## First Action

P0(데이터디렉토리 결함)를 실측으로 재현해 못박는다 — 유저가 의심하는 바로 그 지점:

```bash
cd /Users/ljo/Desktop/project/zero-code/say-it
# 스킬이 Bash로 부르는 방식 그대로, env에 CLAUDE_PLUGIN_DATA/SAY_IT_DATA_DIR 없이 실행
env -u CLAUDE_PLUGIN_DATA -u SAY_IT_DATA_DIR python3 scripts/session_start.py --persona test 2>&1; echo "exit=$?"
# 예상: "say-it: no data dir (CLAUDE_PLUGIN_DATA / SAY_IT_DATA_DIR unset)" + exit=1
# = 데이터디렉토리 못 구하면 세션 시작이 즉시 죽는다는 증명(스크립트 쪽 절반).
```

이건 "env 없으면 죽는다"의 절반만 증명. 나머지 절반("프로덕션 Bash엔 그 env가 실제로
없다")은 문서+실측(아래 P0 근거)로 이미 확보됨. 100% 확정사격을 원하면: say-it을 실제
플러그인으로 설치 → `/say-it-build` 시도 → "no data dir" 뜨는지 확인.

그다음 `/grill-with-docs`로 P0 수정안(아래 "수정")을 그릴.

## Context

검수는 전부 끝나 결론 확정. 유저 반응의 핵심 = **P0를 이해 못 함**("왜 변수가 안 넘어가?
공식문서 봤어?"). 그래서 다음 세션은 새 검수가 아니라 **P0를 납득시키고 그릴해서 고치는** 흐름.

P0 헷갈림의 정체 = 두 메커니즘 혼동:
- **텍스트 치환(substitution)**: SKILL.md 글자 속 `${CLAUDE_PLUGIN_ROOT}`가 Claude 읽기 전
  실제 경로로 바뀜 → 명령어 문자열에 박힘 → 작동.
- **환경변수 export**: *프로세스 env*에 변수 주입. 문서가 받는 대상을 **hook·MCP·LSP로만 한정**.
  Bash 툴은 빠짐.

say-it은 ROOT는 ①치환(됨), DATA는 ②env(Bash엔 안 됨)으로 처리 = 그게 버그.

## Current Progress

검수 100% 완료. 코드 변경 0(read-only). untracked = `docs/handoff/`(이 파일)뿐. 마지막 커밋 `6f04ce5`.

**실측으로 확정한 사실 (명령 실행 결과):**
- 한글-소스 게이트 `grep -rlP scripts skills tests` = **0건 clean**.
- 유닛테스트 `python3 -m unittest discover -s tests -v` = **94 pass, OK**.
- `claude plugin validate . --strict` = plugin.json·hooks.json·skill frontmatter **통과**.
  경고 1개: `CLAUDE.md at plugin root는 end-user에 안 실림`(개발용이라 무해).
- **훅 배선됨**(핸드오프 구버전 최우선 리스크 #1 = 기우). 근거: plugins-reference.md
  line 408("manifest 생략시 기본위치 자동탐색")+805(Hooks 기본위치=`hooks/hooks.json`).
  manifest에 `hooks` 필드 없어도 자동탐색. validate도 정상 인식.
- 현재 Bash 툴 env에 `CLAUDE_PLUGIN_*` = **0개**(플러그인 15개 활성인데도).

## What Worked (검수 결론 — 강점, 확정)

7개 평가축 거의 전부 모범:
- **primitive 선택 ✅**: 스킬(런너/빌더)+훅(tick)+데이터(lexicon) 분리 정확. tick은
  model-invoked 스킬에 자리 없는 매-턴 자동동작이라 hook 소유(ADR 0004) = 교과서적.
- **결정/프롬프트 경계 ✅✅**: `scripts/sayit_state.py` 단일 진실원 + 얇은 래퍼. 결정적
  가드(턴캡·distress HARD regex·dedup·forward-only stage·1회연장 latch) 전부 코드(테스트
  가능), 대화·SOFT는 프롬프트. acute-harm은 `tick()`이 코드로 `blocked/active` 래치(터미널,
  모델선의 비의존, ADR 0003).
- **progressive disclosure ✅**: 본문 적정, references 역할분리, schemas 별도, lexicon 게이트 밖.
- **글쓰기 ✅**: MUST 남발 X, 각 지시에 why(임상기전) 설명. docstring이 설계의도까지 전달.
- **triggering ✅**: say-it/say-it-build description이 RUNNER/BUILDER + build먼저/run나중 상호참조로
  명확 분리 = 트리거 충돌 실재 안 함.
- **도메인 충실도 ✅**: `CONTEXT.md` 용어 ↔ 코드 높은 정합. issue=(persona,theme) 튜플 →
  `find_revisit` 정확매칭. "입구비교/출구저장", distress 2층(HARD floor/SOFT augment) 일치.
- **검증가능성 ✅(설계)**: 94 유닛 + 라벨코퍼스 + 통합 커버링배열(8셀+가드3+교정1, `docs/evals/09-integration-matrix.md`)+사람 sign-off 게이트.

## What Didn't Work / 발견 결함

### ⚠️ P0 (치명) — 프로덕션 데이터디렉토리 해석 실패. **이걸 그릴할 것.**

**증상**: 모델이 스킬에서 Bash로 부르는 CLI 전부 — `session_start.py`·`save_persona.py`·
`save_takeaway.py`·`save_correction.py`·`session_end.py`·`session_block.py`·
`transition_stage.sh` + SKILL.md 인라인 `python3 -c` — 가 `st.data_dir()`를 **인자 없이**
호출(`scripts/sayit_state.py:70`). 즉 `os.environ`의 `CLAUDE_PLUGIN_DATA`/`SAY_IT_DATA_DIR`에만 의존.

**근거 3중 수렴** (공식문서 = plugins-reference.md, 전문 fetch 확인):
1. line 633 verbatim: "All are substituted inline... All are also exported as environment
   variables **to hook processes and MCP or LSP server subprocesses**." → env export 대상에
   Bash 툴 **없음**.
2. line 809: `bin/`은 "Bash tool's PATH"에 추가 — 문서가 Bash 툴을 *알면서도* env-export
   목록(633)엔 일부러 안 넣음 = 누락 아니라 제외. Bash 툴은 PATH만, env var는 안 받음.
3. skills.md 치환표에도 `CLAUDE_PLUGIN_DATA` 없음.
4. 실측: Bash env에 `CLAUDE_PLUGIN_*` 0개(플러그인 15개 활성).

**실패 체인**: `session_start.py:29`이 Bash서 dd=None → "no data dir" exit 1 → active 세션파일
미생성 → hook `tick.py:41`(env는 받음)이 load_session→None→영구 침묵 → 가드·페르소나·takeaway
전부 사망. **`SAY_IT_DATA_DIR` 수동 export 없이는 플러그인 비작동.**

**대조 — 왜 ROOT는 되고 DATA는 안 되나**:
- `${CLAUDE_PLUGIN_ROOT}` → SKILL.md 글자에 박음 → 치환됨 → 스크립트 경로 해결 ✅
- `CLAUDE_PLUGIN_DATA` → SKILL.md에 글자로 안 박고 스크립트가 env서 읽음 → Bash엔 env 없음 ❌

**보강증거**: `session_start.py:23`이 `os.environ.get("CLAUDE_SESSION_ID")` 읽는데 실제 Bash
env는 `CLAUDE_CODE_SESSION_ID`(이름 다름) → session_id도 프로덕션서 항상 null. 같은 뿌리.

**왜 테스트가 안 잡았나**: `test_state.py`·`test_integration_smoke.py` 전부 `SAY_IT_DATA_DIR`
명시 주입(`test_integration_smoke.py:46`) → 프로덕션 `CLAUDE_PLUGIN_DATA`-from-Bash 경로 미검증.
issue 09 사람 워크스루(체크리스트 전부 미체크)가 이 버그 첫 발현 지점.

**수정 (spec-guaranteed; env상속→콘텐츠치환 전환)**:
```text
# 양 SKILL.md: 모든 CLI 호출에 --data-dir 추가 (${CLAUDE_PLUGIN_DATA}는 skill콘텐츠서 치환보장 + 참조시 디렉토리 자동생성)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_start.py" --persona <id> --data-dir "${CLAUDE_PLUGIN_DATA}" --session "${CLAUDE_SESSION_ID}"
# 인라인 -c 도: st.data_dir('${CLAUDE_PLUGIN_DATA}')
```
```python
# 각 CLI argparse: parser.add_argument("--data-dir"); dd = st.data_dir(args.data_dir)  # explicit 최우선, data_dir 이미 지원
# transition_stage.sh: 디렉토리를 argv로 받아 st.data_dir(sys.argv[...])
```
`tick.py`(hook)는 env 정상수신 → 그대로 둠. `SAY_IT_DATA_DIR` 폴백 유지.
**신뢰도**: 높음(문서+실측). 잔여 caveat = 실제 설치 E2E 미실행 → First Action으로 못박기.

### ⚠️ 나머지 (그릴 후순위)

| # | 심각도 | 항목 |
|---|---|---|
| M1 | Major | persona `id` slug 패턴 미강제. `persona.schema.json:14`엔 `^[a-z0-9]+(?:-[a-z0-9]+)*$` 있으나 `validate_persona`(`sayit_state.py:560`)는 non-empty string만 검사. id가 파일경로(`_persona_path` → `personas/<id>.json`) → `../` 경로탈출 여지(모델발, 위험낮음). 쓰기경계(`validate_persona`)에 패턴가드 추가 권장. |
| m2 | Minor | `무서워` panic regex 방향-모호(`lexicon/distress.ko.json` note 자인). `distress_examples.ko.json` 코퍼스는 자기두려움 positive만, 외부두려움("그 상황이 무서워")은 음성으로 안 잠김. panic=render-only·non-latching=세션내 회복가능 → 안전쪽 의도적 over-trigger. 권장: 외부두려움 케이스 코퍼스 추가 or regex에 1인칭 grain. |
| m3 | Minor | `conflict-vocabulary.md` 2벌 = 의도된 KO설계doc(`docs/references/`)/EN런타임번들(`skills/say-it-build/references/`) 쌍. 중복버그 아님. 단 단일소스 메커니즘 없음 → drift 위험(이미 구조 미세 불일치). |
| m4 | Minor | `validate_persona`가 L3 items의 `trigger/reaction` 형태 미검(schema엔 required). 의도적 부분집합. |
| m5 | Trivial | `skills/say-it/SKILL.md:177` cross-ref "above"가 실제 아래(line 195) 가리킴. |
| m6 | Trivial | CLAUDE.md plugin-root 경고(validate --strict). |

## Decisions Made

- 검수 결론 확정: **구조·철학·도메인충실도·안전설계 최상급. 단 P0 하나가 프로덕션 작동 차단.**
  "잘 지은 집, 메인 수도밸브 잠김." 발행 가능조건 = P0 수정.
- 우선순위: P0 → M1 → m2~m6.
- PRD 부합: 결정 A 하이브리드/결정 B 원칙우선/4단계 arc/턴캡(이슈04)/distress 2등급(ADR0003)/
  재방문가드/단일소스 핫라인(이슈10)/안전고지 1회 = **전부 부합**. 단 **end-to-end 작동만 P0로 차단**.
- 유저 의도(구버전서 3회 교정): eval 안 돌림. skill-creator-pro는 기준지식으로만.

## Next Steps

1. First Action으로 P0 실측 확정.
2. `/grill-with-docs`로 P0 수정안 그릴 — 그릴 포인트 후보:
   - `--data-dir` 인자방식 vs 다른 대안(예: `${CLAUDE_SKILL_DIR}` 기반? wrapper?)이 맞나.
   - `tick.py`만 env 받는 비대칭이 설계상 OK인가, 통일할까.
   - 수정이 ADR 0004(hook 소유)나 CONTEXT.md 용어에 영향 주나.
3. 그릴 합의 후 P0 패치 적용(SKILL.md 2개 + CLI 7개 + 인라인 -c). 코드=영어.
4. M1(id slug) 그릴/수정.
5. (선택) issue 09 사람 워크스루로 E2E 검증 = 마지막 게이트.
