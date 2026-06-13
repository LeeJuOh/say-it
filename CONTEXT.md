# say-it — Ubiquitous Language

> say-it(대인관계 빈 의자 세션 스킬) 도메인 용어 글로서리.
> grill-with-docs 세션서 확정된 용어만 기록. 구현 디테일 금지(글로서리 only).
> 근거: [PRD](docs/prd/PRD.md) · ADR [0001](docs/adr/0001-s2-user-voices-the-other.md)~[0004](docs/adr/0004-state-tick-via-hook.md)

---

## 핵심 표상

- **persona ("내 인식 속 그 사람")**: 봇이 연기하는 대상. "진짜 그 사람"이 아니라 유저 머릿속 표상의 외재화(대상관계 internal object). 유저 서술만으로 빌드, 빈 칸 = LLM 추론. **추론 출처 = 유저 서술의 결을 따라 외삽**(internal consistency), 데모그래픽/별자리/MBTI 스테레오타입 금지 — "내 인식 속 그 사람"이지 "평균적 그 직군"이 아니라서. (ex-skill의 별자리·MBTI 빈칸채움은 안 따옴.)
- **양가성 / 핵심 긴장 (ambivalence)**: 그 사람 *본인 행동*의 모순(예: "무시하다 가끔 챙김"). **지우지 않고 보존**한다 — 모순은 버그 아니라 인격의 핵심(ref: nuwa-skill 矛盾처리). 안 풀린 이 양가성이 곧 반추 동력(같은 내용 무해결 반복)이라 우리한텐 장식 아닌 핵심. persona Layer 4(관계역학)에 1필드로 박음. 유저 *자신의* 감정 양가("미운데 죄책감")는 별개 — 그건 [관계 맥락]에.
- **관계 맥락 (relationship context)**: 갈등 역학·전형 싸움·"내가 원하는 것". persona와 별개 저장. "내가 원하는 것" = 세션 arc 종착점.
- **매듭 (closure)**: 제품 목표 = 감정 **소화**. 배출(분풀이)·후련함과 **다름** — 배출은 우리가 막는 반추 그 자체.

## 세션 단위

- **세션 (session)**: 빈 의자 4단계(S1 분출 → S2 역할교대 → S3 통합 → S4 마무리) 한 판. takeaway 1줄로 강제 종료.
- **이슈 (issue)**: **(persona, grievance-theme) 튜플.** 한 사람에 대한 **반복되는 불만 테마** 단위. 단일 사건 아님. 재방문 가드·MVP 성공지표·유사도 매칭의 기준 단위.
  - 같은 persona + 다른 테마 = **다른 이슈** (정당한 재방문, 통과).
  - 같은 테마 + 다른 사건 = **같은 이슈** (반추 임상정의 = 같은 내용 무해결 반복 → 가드 발동).
- **occurrence (사건)**: 이슈의 단일 발생 인스턴스. 이슈 밑에 매달림. 매칭은 occurrence가 아니라 이슈(테마) 레벨.
- **테마 라벨 (theme label)**: 이슈를 식별하는 구조 라벨(예: `boss/credit-theft`). 라벨 생애주기 = **"비교는 입구에서, 저장은 출구에서"**: ①세션 시작 — 모델이 유저 첫마디 + 기존 라벨 목록으로 매칭 시도 → 걸리면 재방문 가드 발동(reflection 질문). ②S4 마무리 — 모델이 기존 라벨 목록 보고 dedup(같은 이슈=재사용, 다르면 신규) → 확정 라벨 + takeaway 저장. 재방문 가드 매칭 = **정확 문자열 매칭**(스크립트/결정적, 유닛테스트 가능). 의미 해석은 모델이 라벨 부여·비교 시점서만, 이후 읽기는 정확일치.

## 런타임 상태

- **세션 상태 (runtime session state)**: 대화 도는 동안 바뀌는 값 — 현재 단계(S1~S4)·턴수·연장 여부. **페르소나(빌드 상태, 불변)와 대비.** prior art 없음(yourself는 free chat이라 세션 상태 0) → greenfield. cf [ADR 0004](docs/adr/0004-state-tick-via-hook.md).
- **매 턴 틱 (per-turn tick)**: 유저 메시지마다 1회 자동 실행되는 기계 동작(턴+1 · 디스트레스 검사 · 캡 체크). Claude skill엔 이 자리가 없음(model-invoked) → **hook이 소유**. cf [ADR 0004](docs/adr/0004-state-tick-via-hook.md).

## 가드

- **재방문 가드 (revisit guard)**: 같은 이슈 재방문 감지. 출력 = **차단 아니라 reflection 질문**("또 같은 거야, 진전 있어?"). 진전 있으면 유저 응답으로 통과 → 정당한 재방문 추방 방지.
- **디스트레스 서킷브레이커 (distress circuit-breaker)**: 위험 신호(패닉·자해 암시) 감지 시 세션 즉시 중단. 2등급 — ① 일반 패닉 → 진정/마무리 ② 급성 위해 → 위기 핫라인 + 재개 금지. 반추용 캡과 **별개**(급성 피해용). cf [ADR 0003](docs/adr/0003-safety-stop-hard-gate.md).
- **HARD 바닥 / SOFT 보강 (hard floor / soft augment)**: 안전 감지 2층. 코드 regex = **바닥**(매 턴·명백 신호 무조건·못 뚫음). 프롬프트 = **보강**(변주·맥락, 바닥 위 한 겹). prompt-only 금지 = [ADR 0003](docs/adr/0003-safety-stop-hard-gate.md).
