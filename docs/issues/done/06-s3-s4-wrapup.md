Status: done
Blocked by: 03-s1-vent

> **Closed** in commit `281b554`. The `/say-it` SKILL.md now runs the full 4-stage
> arc end to end: S3 (integration) and S4 (closure, 4 bits + closing line) modules
> join the existing S1/S2. Prompt-layer slice — no new runtime Python; the seams
> (`save_takeaway.py`, `session_end.py`, `transition_stage.sh`, `load_log`) all
> pre-existed. All 9 acceptance items met; 58 tests green (+4 new), source
> Hangul-free.
>
> What landed:
> - **S3 module** — back-in-your-own-chair turn (rumination → problem-solving,
>   RF-CBT); the single load-bearing question "what did you actually want from
>   them?"; deliverable is *one named want*; guardrails against re-venting and
>   against turning S3 into advice-giving. Reached via `transition_stage.sh
>   integration`.
> - **S4 module** — the four bits: (1) bot drafts the takeaway from the S3 want,
>   (2) user re-articulates in their own words (a bare "yeah" doesn't set it),
>   (3) fiction reminder / cognitive defusion, (4) **exact-string** label dedup
>   against `load_log` then `save_takeaway.py` with the **raw** takeaway, (5) the
>   warm-but-plain closing line. Then `session_end.py` force-closes.
> - **Closing-line tone** spelled out with both failure modes named (clinical
>   "saved. done." ❌ / heavy therapy-speak ❌) and the knot-not-the-person
>   distinction (`set this knot down` ⭕ / `said goodbye to them` ❌).
> - **Lifecycle markers refreshed** — the intro, step 2 (entry gate), step 4, and
>   step 5 no longer describe S3/S4 as future work.
>
> Two notes for the record:
>
> 1. **This slice activates issue 03's entry revisit gate.** That gate (step 2) was
>    a documented permanent no-op because nothing wrote theme labels. S4 bit 4 now
>    saves `(persona, theme_label, raw takeaway)` at closure, so on a return visit
>    the log has prior issues for the gate's semantic match to mirror back. Entry
>    gate = model semantic judgment; S4 exit dedup = exact-string `find_revisit`
>    territory — kept distinct, the issue-03 trap not repeated.
> 2. **CLI test added (acceptance §"save_takeaway 유닛테스트").** The library append
>    was already covered by `TestTakeawayLog`; the closure path actually invoked is
>    the `save_takeaway.py` **CLI**, which was untested. `TestSaveTakeawayCLI` drives
>    it end-to-end on a tmp `SAY_IT_DATA_DIR`: append correctness, raw non-ASCII
>    preservation, JSON integrity, and append-only across separate process
>    invocations. No new production Python (Decisions §1).

# integration 통합 + closure 마무리 (takeaway + 라벨 저장)

## What to build

**integration 통합:** 유저가 본인 자리로 복귀, "그래서 내가 원했던 게 뭐냐" 정리. 반추(감정에 매달림)에서 문제해결(목표지향)로 전환 (RF-CBT).

**closure 마무리 (4비트):**
1. **통합 회수** — 봇이 takeaway 초안 제시 ("넌 사과가 아니라 인정을 원했어, 맞아?")
2. **유저 확정** — 유저가 자기 말로 고쳐 소유 (그냥 "응" 아님, 본인이 articulate해야 박힘)
3. **허구 재확인** — "이건 네 기억 속 그 사람, 진짜 아냐" (cognitive defusion, 봇 의존·가짜 친밀 차단)
4. **라벨 확정 + takeaway 저장** — 모델이 기존 라벨 목록 보고 dedup (같은 이슈=기존 라벨 재사용, 다르면 신규 생성). 확정 라벨 + takeaway 원문을 takeaway_log에 저장. 라벨 매칭 = 정확 문자열 (스크립트/결정적).
5. **닫는 한마디 (톤)** — 사무적("저장됨. 끝")으로 끊지 말고 **따뜻하되 담백하게** 매듭 닫음 (ref: ex-skill `/let-go` 톤 차용). 예: "오늘 이거 잘 내려놨네. 수고했어." **주의**: 보내는 건 *그 사람*이 아니라 *이 응어리 하나* — 산 사람이라 "그 사람 안녕/보냈다" ❌(내일 또 봄), "이 응어리 내려놨다" ⭕. 진한 상담 톤("당신은 충분히 잘하고 있어요") ❌ — "가벼운 한 판" 프레임 유지.

### takeaway_log 쓰기 메커니즘

모델이 closure bit 4에서 라벨·takeaway 확정 후, **`scripts/save_takeaway.sh`(또는 동등 스크립트)를 호출**해 takeaway_log.json에 append. hook은 takeaway_log를 **읽기만** 함(입구 매칭용). 쓰기는 모델→스크립트 경로.

> 이 슬라이스의 라벨 저장이 완료되어야 이슈 03(S1 재방문 가드 입구)의 매칭이 실제로 작동함.

세션은 takeaway 한 줄로 **강제 종료** — 끝없이 늘어져 세션 간 반추로 새지 않게.

### SKILL.md 영향

기존 `/say-it` SKILL.md에 추가 — integration 통합 + closure 4비트 마무리 프롬프트 모듈 + save_takeaway 스크립트 호출 지침.

## Acceptance criteria

- [ ] integration에서 "내가 원한 게 뭐냐" 전환 프롬프트
- [ ] closure bit 1: 봇이 takeaway 초안 제시
- [ ] closure bit 2: 유저가 자기 말로 고쳐 확정 (단순 수긍 아님)
- [ ] closure bit 3: 허구 면책 표시
- [ ] closure bit 4: 모델이 기존 라벨 보고 dedup → scripts/ 스크립트로 takeaway_log에 저장
- [ ] closure bit 5: 닫는 한마디 = 따뜻하되 담백 (응어리 매듭, "사람 보내기" ❌, 상담 톤 ❌)
- [ ] 세션이 takeaway 후 강제 종료 (늘어짐 방지)
- [ ] takeaway는 원문 보존 (요약/압축 없음)
- [ ] save_takeaway 스크립트 유닛테스트 (append 정확성, JSON 무결성)
