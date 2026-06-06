Status: ready-for-agent
Blocked by: None

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
| Layer 4 | 관계 역학 (갈등 패턴, 전형적 싸움, "내가 원하는 것") | 회의서 무시→뒤에서 험담→내가 참음 |

Layer 4가 yourself의 "인간관계"를 **관계 맥락**으로 교체한 say-it 고유 층.

유저 서술만 입력. 카톡 원문 업로드 금지 ([ADR 0002](../adr/0002-narration-only-input.md), 영구). 빈 칸 = LLM 추론. "진짜 그 사람"이 아니라 "내 인식 속 그 사람"(대상관계 internal object) 프레이밍 명시.

### SKILL.md 영향

`/say-it-build` SKILL.md 신규 생성 — 5층 intake flow, 관계 맥락 빌드.

## Acceptance criteria

- [ ] Intake flow가 5층 각각에 대한 질문 진행
- [ ] 관계 맥락(갈등역학·전형싸움·"내가 원하는 것") Layer 4로 저장
- [ ] 빈 칸은 LLM 추론으로 채움
- [ ] "내 인식 속 그 사람, 진짜 아님" 안내 표시
- [ ] 유저가 페르소나 요약 미리보기 후 확정 가능
- [ ] 페르소나 파일이 이슈 01의 JSON 스키마(5층 + corrections)대로 생성
- [ ] 저장 경로: `$CLAUDE_PLUGIN_DATA_DIR/personas/{id}.json` (id = 관계+이름 slug, 예: `boss-kim`)
- [ ] 멀티 페르소나: personas/ 디렉토리 내 파일 여러 개로 관리
