---
status: accepted
date: 2026-06-06
context: say-it (대인관계 빈 의자 세션 스킬, 별개 제품 실험) — grill-with-docs PRD #2(세션 상태 영속) 산물. 근거는 ../brainstorm.md + ADR 0003(안전 정지 HARD)
---

# 세션 상태·안전 틱은 hook이 박는다 — say-it = skill-only 아님 (skill + hook)

세션 런타임 상태(현재 단계·턴수·연장 여부)와 디스트레스 감지를 **매 턴 결정적으로 실행**하기 위해, say-it은 순수 Claude skill이 아니라 **skill + UserPromptSubmit hook**으로 구성한다. 상태는 대화 컨텍스트가 아니라 **JSON 파일**(`session_state` 세션 내 / `takeaway_log` 세션 간) + 페르소나 파일에 둔다. **hook이 매 턴 틱**(턴+1 · 디스트레스 regex 바닥 · 캡 체크)을 소유하고, 모델은 그 위에서 해석·톤만 맡는다.

레퍼런스(yourself/同事/前任)는 페르소나를 파일로 저장하지만 런타임 세션 상태·매 턴 틱은 0개(빌드 후 free chat) → 이 레이어는 prior art 없는 greenfield다. "Claude skill이면 그냥 스킬 하나로 끝 아니냐"는 자연스러운 기대라, 안전 때문에 hook을 동반해야 하는 이유를 명시 기록한다.

## Considered Options

- **A — 모델이 다 (in-context, prompt-only)**: 상태를 대화 기록에 녹이고 모델이 턴수·단계를 추론. 인프라 0, 순수 스킬. 하지만 비결정 + 긴 세션서 context-rot로 턴수 오산·디스트레스 놓침 → **[ADR 0003](0003-safety-stop-hard-gate.md) 정면 위반.** 탈락.
- **B — 파일 + 모델이 스크립트 호출**: 상태는 JSON 파일(결정적), SKILL.md가 "매 턴 가드 스크립트 호출하라" 지시. 순수 스킬 유지. 하지만 호출 자체를 모델이 까먹을 수 있음 → 결국 모델 선의 의존 = SOFT. 턴캡엔 견딜 만하나 **디스트레스(급성 피해)엔 불충분.**
- **C (채택) — 파일 + hook 매 턴 틱**: UserPromptSubmit hook이 유저 메시지가 모델에 닿기 **전** 코드로 실행 → 못 뚫음 = HARD. 디스트레스가 hook을 강제하므로, **이미 매 턴 도는 hook에 턴카운트·캡을 무임승차**(추가비용 ≈ 0, PRD 테스트가 요구하는 결정성도 확보). 단점 = 순수 스킬 아님(hook 배선·이식성↓).

## Consequences

- 배포 단위 = **skill + hook**. 순수 스킬보다 설치 1스텝(settings 배선) 더. 이식성 비용은 ADR 0003이 박은 "안전 > 이식성"으로 흡수.
- 상태 3종 파일: **페르소나**(빌드산출, yourself 패턴) / **session_state**(세션 내: 단계·턴·연장) / **takeaway_log**(세션 간: append-only, 테마 라벨).
- hook 책임 = 턴+1 · 디스트레스 regex 바닥 · 캡 체크 → 게이트 걸리면 authoritative system-reminder 주입. 모델 책임 = 해석·톤·디스트레스 변주 보강.
- **detection은 hook이 HARD 보장, enforcement(진정/핫라인 렌더)는 모델** — 단 갓 주입된 fresh 명령이라 context-rot 안 걸림 → ADR 0003 의도(긴 세션서 *못 알아챔* 방지) 충족.
- harness-zero 자체 패턴과 일치(architecture-guard=PreToolUse, bootstrap-check=SessionStart) — 집안 스타일.
- 앱(🅱️) 전환 시 hook → 서버 미들웨어로 자연 승격(WAF 자리 그대로).
- 6개월 뒤 "그냥 순수 스킬로 못 하나" 단순화 제안 가능 → 이 기록이 막음. [ADR 0003](0003-safety-stop-hard-gate.md) 종속.
