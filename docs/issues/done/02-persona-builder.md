Status: done
Blocked by: None

> **Closed** in commit `62c639c`. New `/say-it-build` skill (5-layer intake
> flow), `save_persona`/`load_persona`/`list_personas` helpers in
> `sayit_state.py`, `save_persona.py` CLI (validate-at-boundary write path), and
> 6 new unit tests (34 total, green). Acceptance list fully met.
>
> One intentional deviation: the conflict-vocabulary table was **moved** from
> `skills/say-it/references/` (where issue 01 first placed it) to
> `skills/say-it-build/references/` — the builder is its only consumer, the
> runner never reads it, and issue 02 calls for it bundled in the *build* skill's
> `references/`. Single source, no duplication; the file's `../../../` relative
> links survive because the directory depth is identical. The shared
> `persona.schema.json` stays under `skills/say-it/references/schemas/` (the
> runner reads it too); the build skill references it cross-skill.

# 페르소나 빌더

## What to build

**별도 스킬 `/say-it-build`**로 페르소나 빌드. 세션 실행은 `/say-it`(이슈 03~). 빌드와 세션 멘탈모델 분리.

Intake flow → 구조 질문(정체·말투·감정 트리거) + 관계 맥락(갈등역학·전형싸움·"내가 원하는 것") → 5층 페르소나 파일 생성. yourself-skill 패턴 차용(1인칭→2인칭 flip, Self Memory→관계맥락 교체).

### 5층 페르소나 구조 (yourself-skill 차용, 2인칭 flip)

| 층 | 내용 | 예시 |
|---|---|---|
| Layer 0 | 하드 규칙 (페르소나가 절대 안 하는 것) | 폭언 escalation 금지, 공격 금지 |
| Layer 1 | 정체 (누구, 역할, 유저와의 관계) | 직장 상사, 7년차, 같은 팀 |
| Layer 2 | 말투 (톤, 입버릇, 유저를 부르는 호칭) | 반말, "그니까~", 이름 호명 |
| Layer 3 | 감정 트리거 (뭐에 화내나, 유저의 뭘 건드리나) | 실수 지적 시 방어적, 공 가로챔 |
| Layer 4 | 관계 역학 (갈등 패턴, 전형적 싸움, "내가 원하는 것") + **양가성/핵심 긴장** | 회의서 무시→뒤에서 험담→내가 참음 / 평소 차갑다 가끔 툭 챙김 |

Layer 4가 yourself의 "인간관계"를 **관계 맥락**으로 교체한 say-it 고유 층.

**양가성 필드 (Layer 4)**: 그 사람 *본인 행동*의 모순을 지우지 말고 보존 — 예 "무시하다 가끔 챙김". 모순=버그 아니라 인격 핵심 (ref: nuwa-skill 矛盾처리). 안 풀린 양가성이 곧 반추 동력 → 우리한텐 핵심. cf [CONTEXT.md](../../CONTEXT.md) 양가성. (유저 *자신*의 감정 양가는 관계 맥락 쪽.)

**갈등 단어표 참조**: intake 때 [docs/references/conflict-vocabulary.md](../references/conflict-vocabulary.md)를 번역기로 사용 — 유저의 막연한 라벨("무시함")을 구체 행동 규칙으로 풀어 Layer 2/3/4에 박음. 표는 분류 감옥 아니라 fallback, 유저 서술이 1순위. **빌드 시 이 표를 스킬 `references/`로 번들** (PRD·ADR과 동일 패턴).

유저 서술만 입력. 카톡 원문 업로드 금지 ([ADR 0002](../adr/0002-narration-only-input.md), 영구). 빈 칸 = LLM 추론 — **추론 출처 = 유저 서술의 결을 따라 외삽, 데모그래픽/별자리/MBTI 스테레오타입 금지** ("내 인식 속 그 사람"이지 "평균적 그 직군" 아님; ex-skill 별자리·MBTI 빈칸채움은 안 따옴). "진짜 그 사람"이 아니라 "내 인식 속 그 사람"(대상관계 internal object) 프레이밍 명시.

### SKILL.md 영향

`/say-it-build` SKILL.md 신규 생성 — 5층 intake flow, 관계 맥락 빌드.

## Acceptance criteria

- [x] Intake flow가 5층 각각에 대한 질문 진행
- [x] intake에 **"그 사람이 죽어도 안 할 말/행동은?"**(부정 공간) 질문 → Layer 0에 박음 (ref: nuwa 禁忌词). 봇이 갑자기 착해져 가짜 사과/위로하는 것 차단 = 몰입+안전. 유저가 막막해하면 서술서 역추론으로 fallback
- [x] 관계 맥락(갈등역학·전형싸움·"내가 원하는 것") Layer 4로 저장
- [x] 빈 칸은 LLM 추론으로 채움 — **유저 서술 결 따라 외삽, 스테레오타입(직군/별자리/MBTI) 금지**
- [x] Layer 4에 **양가성/핵심 긴장** 필드 — 그 사람 행동의 모순 보존(매끄럽게 지우지 않음)
- [x] intake가 **갈등 단어표**(conflict-vocabulary.md) 참조해 막연한 라벨→구체 행동 번역
- [x] 프리뷰서 어느 층이 서술 vs 추론인지 표시 (유저가 추론분 교정 가능)
- [x] "내 인식 속 그 사람, 진짜 아님" 안내 표시
- [x] 유저가 페르소나 요약 미리보기 후 확정 가능
- [x] 페르소나 파일이 이슈 01의 JSON 스키마(5층 + corrections)대로 생성
- [x] 저장 경로: `$CLAUDE_PLUGIN_DATA_DIR/personas/{id}.json` (id = 관계+이름 slug, 예: `boss-kim`)
- [x] 멀티 페르소나: personas/ 디렉토리 내 파일 여러 개로 관리
