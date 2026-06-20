Status: done
Blocked by: 01-hook-infra

> **Closed** in commit `961e823`. The distress circuit-breaker now bites: the HARD
> keyword floor (ADR 0003) is populated and the BLOCKED resume-refusal is wired
> through the hook, the library, and `session_start`. All 8 acceptance items met;
> 73 tests green (+15), source Hangul-free, end-to-end CLI smoke (trigger → GRADE_2
> → BLOCKED → hold re-inject → resume-refused) passes.
>
> What landed:
> - **HARD floor as DIRECTION, not intensity.** The discriminator is self- vs
>   other-directed: the desiderative "want to die" (self) fires; the transitive
>   "want to kill them" (rage at the other = this product's core catharsis) stays
>   clear. The first-person *want* marker is what cleanly separates the two for the
>   death-verb family; the corpus locks it with negatives written first.
> - **Pattern home (Blocker 1).** Korean regexes + the crisis hotline are runtime
>   *data*, so they live in a new top-level `lexicon/` dir
>   (`distress.ko.json`), outside the `scripts/skills/tests` the English-source gate
>   scans. `distress_examples.ko.json` is the labelled corpus the tests assert
>   against, which keeps the test source itself Hangul-free.
>   `sayit_state.load_distress_lexicon()` loads both globals once at import.
> - **BLOCKED state (Blocker 2).** New `blocked` bool on session_state. `tick`
>   latches it (acute-harm → `blocked=true`, `active=false`) in code, so the stop
>   never depends on model goodwill. Resume is refused twice: the tick hook
>   re-injects a SAFETY HOLD every later turn, and `start_session` rejects opening a
>   new round over a blocked file (CLI exit 2 + hotline). Distinct from the
>   persona-level block flag (issue 08).
> - **Two grades.** `render_reminder` emits `DISTRESS_TRIGGERED: GRADE_1` (panic,
>   render-only de-escalation) or `GRADE_2` (acute-harm + hotline verbatim + BLOCKED
>   notice). SKILL.md "Reading the hook" gained the grade branches and the SOFT-layer
>   guidance; SAFETY.md went stub → live.
>
> Intentional deviations / notes:
> - **`session_block.py` / `block_session()` added beyond the strict acceptance** so
>   the SOFT model layer can latch the *same* BLOCKED hold for acute phrasings the
>   regex misses — otherwise SOFT-detected harm would end the session but leave it
>   resumable, a gap between the two detection layers ADR 0003 pairs.
> - **Panic floor kept high-precision.** The issue's three panic examples
>   (scared / overwhelmed / "want it to stop") are all on the floor, but
>   direction-ambiguous and somatic variants (e.g. "can't breathe", or fear that
>   describes *the other* rather than the self) are deliberately left to the SOFT
>   layer, per ADR 0003's "HARD precise, SOFT recall" split — firing them in code
>   would risk cutting off legitimate venting.
> - **Hotline `109`** (자살예방 상담전화, the 2024 unified line) is the single source;
>   issue 10's disclosure copy is to *share*, not re-define it.
> - **Multi-locale is out of scope and unplanned** (confirmed across issues/ADR/PRD).
>   This product is Korean-locale by ADR 0003; the `.ko` suffix is only a defensive
>   seam, not a committed roadmap item.

# 디스트레스 서킷브레이커 (HARD + SOFT)

## What to build

2층 감지 + 2등급 대응. ADR 0003 구현.

### 감지 2층

- **HARD 바닥**: hook 키워드 regex (매 턴, 명백 신호 무조건 트리거, 우회 불가, 한국어 로케일)
- **SOFT 보강**: 프롬프트 레이어 (변주·맥락 잡음 — "숨이 안 쉬어져", "다 끝내고 싶어" 등)

### false positive 경계 (이 제품 특유)

이 제품은 유저가 억눌렀던 감정을 쏟는 게 핵심 사용법. 욕설·격앙·분노 폭발이 **정상 사용**이다. regex 설계 시 핵심 구분:

- **정상 분출 (오발 금지)**: "죽여버리고 싶어"(상대에 대한 분노), "미쳐버리겠다", "때려치우고 싶다" — 상대/상황 향 격앙
- **Grade 1 (일반 패닉)**: "무서워", "너무 힘들어", "그만하고 싶어" — 유저 자신의 고통 호소
- **Grade 2 (급성 위해)**: "죽고 싶어", "사라지고 싶어", "자해" — 유저 자신 향 위해 암시

방향성이 **상대/상황 향**이면 정상, **유저 자신 향**이면 가드 발동. 오발 = 정상 카타르시스 끊김 = 제품 파괴.

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
