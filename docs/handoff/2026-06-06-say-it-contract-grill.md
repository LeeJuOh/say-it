---
topic: say-it-contract-grill
date: 2026-06-06
---

# say-it — 이슈 스펙 grill 완료, 빌드 준비

## Goal

say-it 플러그인(마켓 배포) 빌드. PRD 계약 확정 → 이슈 9개 생성 → 이슈 스펙 grill 2라운드 → 빌드.

## First Action

say-it 레포에서 이슈 01(hook 인프라)부터 빌드:

```
docs/issues/01-hook-infra.md 분석해서 구현 진행
```

01 + 02 병렬 가능. 이후 빌드 순서는 아래 표 참조.

## Context

이전 세션에서 PRD 계약 3종 확정 + 이슈 9개 생성 + skill-creator-pro 관점 검수 완료. 이번 세션에서 grill-with-docs로 이슈 하나씩 줌아웃 → 개선안 제시 → 승인 후 수정. 커밋 `d718c92`.

## Current Progress

working tree 클린. 모든 변경 커밋 완료.

### 이슈 grill 결과 (이번 세션)

| 이슈 | 변경 |
|---|---|
| 01 | references/ 번들 정리(brainstorm/yourself 제거), 플러그인 scaffold criteria 추가, persona JSON 스키마(5층+corrections) 정의, stage 네이밍(vent/role-swap/integration/closure) |
| 02 | 저장 경로 `$CLAUDE_PLUGIN_DATA_DIR/personas/{id}.json`, 멀티 페르소나 규약 |
| 03 | 이슈 05(S2 역할교대) 합류, 재방문 가드 테스트 시점 명시(빈 로그=단독 테스트, 로그 있음=이슈 06 후 통합 테스트) |
| 04 | 단계 전환 메커니즘 추가(`scripts/transition_stage.sh`, 앞으로만 전이), 턴캡 stage명 반영 |
| 05 | → 03에 merged (프롬프트 전용이라 독립 슬라이스 불필요) |
| 06 | stage 네이밍 반영(S3→integration, S4→closure), 의존성 05→03 |
| 07 | false positive 경계 추가 — 상대 향 격앙=정상, 유저 자신 향=가드 발동 |
| 08, 09 | 변경 없음 |

### 빌드 순서

| 순서 | 이슈 | 블로커 |
|---|---|---|
| **1** | 01-hook-infra | 없음 |
| **1** | 02-persona-builder | 없음 |
| **2** | 03-s1-vent (+S2) | 01, 02 |
| **2** | 04-turn-cap | 01 |
| **2** | 07-distress-breaker | 01 |
| **3** | 06-s3-s4-wrapup | 03 |
| **3** | 08-persona-correction | 03 |
| **4** | 09-integration-smoke | 전부 |

## Decisions Made

| 결정 | 근거 |
|---|---|
| stage 값 = `vent/role-swap/integration/closure` | S1~S4는 의미 불명 |
| persona 스키마 = JSON, 5층(L0~L4) + corrections 배열 | hook이 프로그래밍적으로 읽어야 함 + 이슈 08 교정 누적 |
| 저장 경로 = `$CLAUDE_PLUGIN_DATA_DIR/personas/{id}.json` | 플러그인 환경변수 활용 |
| 이슈 05 → 03 합류 | 프롬프트 전용, 결정적 코드 0개, 독립 슬라이스 불필요 |
| 단계 전환 = 모델→`scripts/transition_stage.sh`→session_state 갱신 | takeaway 저장과 동일 패턴(모델→스크립트→상태 파일) |
| references/ 번들에서 brainstorm.md, yourself 스니펫 제거 | 내용이 이미 PRD+ADR+이슈에 증류됨 |
| 디스트레스 핫라인 = 제품 책임(주의의무) | 제품이 감정 격앙 상황을 만드므로 프로바이더 맡김만으론 부족. 출시 전 법률 검토 필요 |

## What Didn't Work

- **"scripts/ 디렉토리 규약" 별도 정의 제안** — 과잉. 각 스크립트 인터페이스는 해당 이슈에서 정의하면 충분
- **"상태 파일 경로 미정" 지적** — 플러그인 환경변수 쓰면 끝. 유저가 즉시 반박
- **S1/S2/S3/S4 약어 사용** — 유저가 "이따위" 반응. 의미 있는 이름으로 교체

## Reference

- PRD: `docs/prd/PRD.md`
- 글로서리: `CONTEXT.md`
- ADR 0001~0004: `docs/adr/`
- 이슈 01~09: `docs/issues/`
