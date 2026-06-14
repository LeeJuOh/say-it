Status: done
Blocked by: 01-hook-infra

> **Closed** in commit `cd6311c`. The session can now *move*: `transition_stage.sh`
> is the forward-only stage motor, and the vent turn cap is gated, extendable, and
> wired to branch tokens the model reads. All 9 acceptance items met; 54 tests green
> (+20 new), source Hangul-free.
>
> What landed:
> - `advance_stage(dd, next)` + `transition_stage.sh <stage>` — forward-only over
>   `vent→role-swap→integration→closure`; rejects backward, skip, unknown, and
>   advancing past closure. Logic in the tested library, shell stays thin (the 01–03
>   split).
> - Cap is **vent-only**: `evaluate_guards` gates `soft_hit`/`hard_hit` on
>   `stage == "vent"`, so the structured stages never trip it.
> - `render_reminder` emits `CAP_TRIGGERED: SOFT` (turn ≥ 8) / `HARD` (turn ≥ 11);
>   SKILL.md reads them as invitation (SOFT → invite onward / extend once) vs. force
>   (HARD → move on now). Signal interpretation (repetition / intensity↓ / giving-up
>   language) stays in the prompt layer, never the script (acceptance §9).
> - One-time extension: `use_extension(dd)` flips the `extension_used` latch; a
>   second call is refused. SOFT goes quiet once spent (no re-nagging); HARD still
>   fires through a spent extension.
>
> Three notes for the record:
>
> 1. **`extend` rides on `transition_stage.sh`.** The issue names only
>    `transition_stage.sh`. Rather than add a second, unnamed CLI for the extension,
>    it's a subcommand on the same script (`transition_stage.sh extend`). Both the
>    stage move and the extension are "the model nudging the session forward at the
>    cap," so one named surface fits; the once-only enforcement lives in the tested
>    library either way.
> 2. **The "+3" is the soft→hard gap, not a counter mutation.** Defaults are soft 8,
>    hard 11, so the extension is "suppress the SOFT invite and let the turns run to
>    the ceiling 11" — `use_extension` flips the latch, it does not rewrite the cap
>    numbers. `8 + 3 = 11` is encoded in the defaults.
> 3. **Turn counter stays monotonic across stages** (Open Question 2, resolved). The
>    cap is gated on `stage`, not reset per stage — simplest, no new coupling. The
>    counter keeps climbing into role-swap/integration/closure; it just stops
>    *meaning* anything there. Revisit if issue 06 needs per-stage counts.

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
