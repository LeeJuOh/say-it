---
topic: say-it-contract-grill
date: 2026-06-06
---

# say-it — 구현 계약 그릴 + 이슈 쪼개기

## Goal

say-it PRD의 구현 계약 3종 확정 → 세로 슬라이스 이슈 생성 → skill-creator-pro 관점 검수. **계약 3종 완료, 이슈 9개 로컬 생성 완료, 검수 2라운드 전부 완료. 빌드 준비 끝.**

## First Action

**빌드 레포**: `~/Desktop/project/zero-code/say-it` (이 레포, 플러그인).
**설계 문서**: 이 레포 내 `docs/prd/PRD.md`, `docs/adr/`, `CONTEXT.md`.

say-it 레포에서 세션 열고 `/skill-creator-pro`로 이슈 01부터 빌드:

```
/skill-creator-pro

say-it 플러그인 빌드. 
이슈: docs/issues/01-hook-infra.md
PRD: docs/prd/PRD.md
ADR: docs/adr/
yourself-skill 참조: ~/Desktop/project/zero-code/references/yourself-skill/
```

01 끝나면 02 → 03 → ... 순서대로. 빌드 순서는 아래 표 참조.

## Context

grill-with-docs로 PRD 계약 3종 잠그고, to-issues로 세로 슬라이스 9개 쪼갬. 처음 GitHub Issues로 발행했다가 유저가 로컬 원해서 닫고 `docs/say-it/issues/`로 이전. 이후 skill-creator-pro 관점 검수 2라운드 완료.

유저 특성: caveman ultra + 한국어, 백엔드 비유, 추천 먼저 제시(떠넘기지 말 것), 너무 압축/jargon이면 "이해되게 말해"로 리셋.

## Current Progress

### 계약 3종 — 전부 완료

| # | 결정 | 근거 위치 |
|---|---|---|
| 이슈 정의 | `(persona, grievance-theme)` 튜플 | `docs/say-it/CONTEXT.md` |
| 상태/틱 | skill+hook, 상태=파일, 틱=hook | `docs/say-it/adr/0004-...md` |
| 유사도 매칭 | 비교=입구(S1 앞머리, 모델 판단), 저장=출구(S4, dedup+정확문자열). 오판=soft fail | `docs/say-it/CONTEXT.md` + PRD |

### 이슈 — 로컬 9개 생성, 검수 완료

빌드 순서 (의존 그래프 기준):

| 순서 | 이슈 | 스킬 | 블로커 | 핵심 |
|---|---|---|---|---|
| **1** | 01-hook-infra | `/say-it` | 없음 | hook 뼈대 + 상태 파일 3종 + references/ 번들 + settings.json 등록 |
| **1** | 02-persona-builder | `/say-it-build` | 없음 | 5층 intake + 관계 맥락 빌드 (01과 병렬 가능) |
| **2** | 03-s1-vent | `/say-it` | 01, 02 | S1 봇 렌더러 + 재방문 가드 입구 + 페르소나 선택 |
| **2** | 04-turn-cap | `/say-it` | 01 | 8턴 소프트캡 + 1회 연장 + 11턴 하드천장 |
| **2** | 07-distress-breaker | `/say-it` | 01 | HARD regex + SOFT 프롬프트 + 2등급 대응 |
| **3** | 05-s2-role-swap | `/say-it` | 03 | 역할교대 스캐폴딩 |
| **4** | 06-s3-s4-wrapup | `/say-it` | 05 | S3 통합 + S4 4비트 + takeaway 저장 |
| **4** | 08-persona-correction | `/say-it` | 03 | 세션 중 교정 피드백 |
| **5** | 09-integration-smoke | 둘 다 | 전부 | 전체 워크스루 eval (사람 리뷰) |

### 검수 — 2라운드 전부 완료

**1라운드: 구현 문제 6건 → 전부 반영 완료.**

**2라운드: skill-creator 관점 7건 → 전부 완료:**

| # | 문제 | 결과 |
|---|---|---|
| 1 | ~~hook vs skill 경계~~ | 철회 |
| 2 | ~~SKILL.md 생성 시점~~ | #3에 종속 |
| 3 | 커맨드 구조 | A안 확정 — `/say-it-build` + `/say-it` 2개 split |
| 4 | references/ 번들 | 이슈 01에 준비 단계 추가 |
| 5 | SKILL.md 누적 관계 | 이슈 01~08에 "SKILL.md 영향" 한 줄씩 추가 |
| 6 | eval 기준 | 패스 — 빌드 시 skill-creator-pro가 생성 |
| 7 | settings.json 배선 | 이슈 01 acceptance criteria에 추가 |

## Decisions Made

| 결정 | 근거 |
|---|---|
| 계약 3종 (위 표) | grill-with-docs 산출물 |
| 재방문 가드 타이밍 = "비교는 입구에서, 저장은 출구에서" | WAF 비유 — 처리 끝나고 차단하면 의미 없음 |
| 입구 비교 = S1 앞머리 포함 (별도 S0 안 만듦) | 4단계 상태머신 유지 |
| 이슈 GitHub→로컬 이전 | 유저 요청. GitHub issues #2~#10 closed |
| 커맨드 구조 = A안(2스킬 split) | `/say-it-build`(빌드) + `/say-it`(세션). 페르소나 여럿이라 자동 분기보다 멘탈모델 분리가 깔끔 |

## What Didn't Work

- **GitHub Issues로 발행** — 유저가 로컬 원함. 9개 닫고 `docs/say-it/issues/`로 이전.
- **검수 1라운드에서 "hook vs skill 경계" 지적** — skill-creator-pro가 hook도 빌드 가능하므로 무의미한 구분. 철회.
- **"정확 문자열 매칭" 용어 혼동** — 입구(모델 판단)와 출구(정확매칭)를 구분 안 해서 이슈에 오해 소지. 수정 완료.
- **설명 과압축** — "하나도 못 알아먹겠어" 피드백. plain하게, 비유로 설명할 것.
- **B안(1스킬 자동분기) 시도** — 페르소나 여럿일 때 빌드/세션 구분 애매. A안(2스킬)으로 확정.
- **핸드오프 문서에 "확정" 적혀 있는데 유저가 아직 확정 안 한 상태** — 문서만 보고 확정으로 밀지 말고 확인할 것.

## Next Steps

1. 새 세션에서 `/skill-creator-pro`로 이슈 01부터 빌드
2. 01 + 02 병렬 가능 → 03+04+07 → 05 → 06+08 → 09
3. say-it 변경만 선별 커밋 (`git add -A` 금지)

## ⚠️ Working Tree 주의

say-it과 무관한 변경 다수 미커밋 (wiki ingest 등). **say-it 커밋 시 `git add -A` 금지** — `docs/say-it/` 만 선별 스테이징.

## Reference

- PRD: `docs/say-it/PRD.md`
- 글로서리: `docs/say-it/CONTEXT.md`
- ADR 0001~0004: `docs/say-it/adr/`
- 이슈 01~09: `docs/say-it/issues/`
- brainstorm: `docs/say-it/brainstorm.md`
