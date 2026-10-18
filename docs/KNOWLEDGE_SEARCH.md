> 최신 보강: [배출 정보 집약체](DISPOSAL_DATA_HUB.md). 품목이 모호하면 되묻고 공식 규격 버튼·직전 품목 맥락을 사용한다. 아래 연결·색인 수량은 시점별 기록이며 최신 실행 상태는 19문단/6벡터다.

# 공식 안내문 검색 — Ollama BGE-M3

사용자 승인 범위(2026-10-18): 기존 질문창에서 관련 공식 안내 요약과 원문을 찾는다. 안내 문장 생성·파인튜닝·영상 분석은 포함하지 않는다.

## 지금 들어간 것

- `data/knowledge_documents.json`: 공식 안내 요약 19개(양천구 7·강서구 5·전국 공통 7). 기존 스마트클린 양천 1개 원문의 주제별 요약 6개를 보존하고 일반·재활용·폐전지 안내를 보강했다. 요약 수와 원문 수는 다르다.
- SQLite: 안내문과 검색용 벡터 저장. 기존 후보·건물·규칙·관리자 수정 자료는 유지한다.
- `/api/chat`: 지역·품목·원문 확인 상태·시행기간을 먼저 확인한 뒤 관련 문서를 찾는다.
- 질문창: 안내와 함께 원문 링크·원문 확인일·원문 기준일·시행기간을 표시한다.
- 기본은 키워드 검색. 벡터를 만들고 임베딩을 활성화하면 Ollama `/api/embed`를 호출한다. 서버 오류·색인 부족 시 키워드 안내를 사용한다.
- `/api/knowledge/status`: 문단 수·색인 수·설정 상태만 반환한다. 모델 서버 연결 확인이나 모델 호출은 하지 않는다.

최신 상태: 원문 6페이지를 추가 보관하고 요약 13개를 보강했다. 실행 중 문단은 19개·유효 벡터는 기존 6개다. 새 문서는 키워드로 검색하며 신규 벡터 색인은 아직 실행하지 않았다. 지도는 실제 자료지만 현장 조사 기준점이며 운영 승인은 확인 전이다. [자료 묶음](DISPOSAL_DATA_HUB.md)을 참고한다.

2026-10-18 추가: [공식 품목 DB](WASTE_DATABASE.md)에 91개 품목명·268개 규격별 수수료를 등록했다. 명칭으로 조회되는 품목은 문서 검색 전에 공식 표에서 답한다. 문서 요약 6건과는 별도 자료이며 벡터 재색인이 필요하지 않다.

## 도우미 이름과 상태 표시 (2026-10-18 초기 기록)

- 화면 이름은 ‘해우리 배출도우미’. 양천구 캐릭터 ‘볼빵빵 해우리’ 이름을 활용한 교육용 시제품이며 구청 공식 서비스가 아니라는 안내를 함께 표시한다.
- 이름 출처: [양천구·공공누리 캐릭터 등록](https://www.kogl.or.kr/recommend/recommendDivView.do?division=img&recommendIdx=139193). 이번에는 이미지 파일을 사용하지 않았다.
- 화면의 ‘AI 꺼짐’ 표시를 질문 안내로 바꾸었다. 각 응답에는 공식 안내 검색/질문 분류/기본 안내 상태를 표시하고, 기술적인 구분은 ‘안내 방식’을 펼쳐 확인한다.
- `GREENZONE_AI_ENABLED`는 질문 분류용, `GREENZONE_EMBEDDING_ENABLED`는 문서 검색용이다. 한쪽이 꺼져 있어도 도우미 전체가 사용 불가능하다는 뜻은 아니다.
- 이 날짜의 실행 상태 확인: 질문 분류 사용 설정, Ollama 연결 및 설치 모델 확인, 공식 요약 6개/색인 6개. 실제 질문·모델 추론·브라우저 사용 확인은 이번 변경에서 수행하지 않았다.
- 소스 또는 환경 설정을 바꾸면 `docker compose up -d --build web`으로 웹만 반영한다. Docker Desktop 전체나 Ollama를 다시 시작할 필요는 없다. 현재 SQLite 저장 자료는 별도 볼륨에 유지한다.

## Docker에서 켜는 순서

1. Docker Desktop과 기존 Ollama 서버를 켠다. 설치된 임베딩 모델의 정확한 이름을 확인한다.
2. 기존 `.env`를 덮어쓰지 않고 아래 항목을 추가·수정한다.

```dotenv
# bge-m3:latest가 실제 설치되어 있을 때의 예시
GREENZONE_EMBEDDING_ENABLED=1
EMBEDDING_MODEL=bge-m3:latest
EMBEDDING_OLLAMA_BASE_URL=http://host.docker.internal:11434
```

Ollama가 다른 포트라면 실제 포트로 변경한다. 분류 모델을 사용하지 않으면 `GREENZONE_AI_ENABLED=0`을 유지할 수 있다. 위 두 기능은 별개다. 기존 `OLLAMA_MODEL`에는 임베딩 모델을 넣지 않는다.

3. 프로젝트 폴더에서 웹을 빌드·시작한다.

```powershell
docker compose up -d --build
```

4. 문서 벡터를 명시적으로 생성한다. **이 명령부터 실제 Ollama 모델을 호출한다.**

```powershell
docker compose exec web python -m scripts.index_knowledge --embed
```

5. `http://localhost:8000/#assistant`를 열고 “이사하면서 나온 책상은 어떻게 버려?” 같은 질문을 입력한다. 실제 `APP_PORT`가 다르면 주소의 포트를 바꾼다. “임베딩 문서 검색” 표시와 출처 카드를 확인한다.

처음 모델을 불러오는 데 오래 걸리면 `.env`의 `EMBEDDING_TIMEOUT_SECONDS=60`으로 조정한 뒤 컨테이너 설정을 반영하고 색인을 다시 실행한다. `host.docker.internal`은 Docker에서 호스트의 Ollama로 접근할 때 쓴다. 모델 서버가 컨테이너에서 접근 가능한 상태여야 한다. 추가 파일·모델을 자동 다운로드하지 않는다.

## 모델 없이 먼저 사용하는 경우

`GREENZONE_EMBEDDING_ENABLED=0`으로 두고 웹만 실행하면 된다. 웹 시작 시 요약 파일을 검색 테이블에 등록하며 모델 호출은 하지 않는다. 질문창에 키워드 검색으로 표시된다.

로컬 Python 실행도 지원한다. `.env`의 임베딩 서버 주소를 실제 로컬 서버 주소(예: `http://127.0.0.1:11434`)로 바꾼다.

```powershell
python run_local.py
# 별도 터미널에서 벡터를 만들 때만 실행
python scripts/index_knowledge.py --embed
```

Docker와 로컬 Python은 기본 DB 위치가 다르다. 실제로 실행할 쪽에서 색인한다. Docker의 SQLite 볼륨에 만든 벡터는 재시작 후에도 유지된다.

## 자료를 추가할 때

`data/knowledge_documents.json`의 `documents` 배열에 다음 정보를 기록한다.

| 필드 | 내용 |
| --- | --- |
| document_id, title, text | 중복 없는 ID·제목·직접 확인한 원문 요약 |
| district_code, district_name | 양천구 `11470`, 강서구 `11500`, 전국 공통 `ALL`; 적용 지역명 |
| dongs | 특정 동만 적용되면 동 목록. 빈 배열은 해당 구 전체 범위 |
| category | general / recycle / battery / bulky |
| keywords | 문서 검색 보조어·품목 표현 |
| source_url, checked_at | 공식 원문 HTTPS 주소·직접 확인한 날짜 |
| reference_date | 원문 자료 기준일. 모르면 null |
| effective_from, effective_until | 원문에 명시된 시행기간. 모르면 null |
| verification_status | 직접 원문을 확인한 요약만 source_checked; 나머지는 unverified |

확인일을 시행일로 채우지 않는다. 화면에서 양천구·강서구를 선택한다. 동별 문서는 질문의 `dong`이 지정되지 않으면 검색하지 않는다. 해당 구 또는 ALL 문서만 선택하며 다른 지역이 질문에 명시되면 지역별 근거를 혼합하지 않는다. `topics`는 how/when/where/source로 질문 유형을 제한한다.

Docker에서는 파일 수정 후 이미지를 다시 빌드하고 `--embed`로 색인한다. 내용·메타정보가 바뀐 문단의 벡터만 갱신하며, 제거한 문서는 검색 테이블에서도 제거한다. 원본 안내문은 이 JSON에서 관리한다. 관리자 규칙 편집 화면은 별도 규칙 테이블이므로 검색 문서와 자동 동기화되지 않는다.

`EMBEDDING_MIN_SCORE=0.55`는 초기 유사도 기준이며 정확도나 정답 확률이 아니다. 실제 질문으로 조정해야 한다. 모델 버전·양자화가 바뀌면 `EMBEDDING_REVISION` 값을 올려 컨테이너를 갱신하고 재색인한다. 현재 구현은 BGE-M3의 dense 벡터 검색만 사용한다.

## 확인 범위

공식 원문과 현재 코드를 대조해 구현했다. 2026-10-18 연결 수정 후 Docker 재빌드·그린존 컨테이너 재생성을 진행했다. 컨테이너에서 문서 6개·벡터 0개·임베딩 활성화와 Ollama 서버 접근·설정 모델 설치 여부를 메타정보로 확인했다. 실제 모델 호출·벡터 색인·검색 품질·브라우저 화면·테스트 실행은 아직 수행하지 않았다. 색인 실패 시 활성화·서버 연결·응답 시간·HTTP 상태·문서·DB 오류를 구분해 표시한다.

근거: [스마트클린 양천 이용 안내](https://smartclean.yangcheon.go.kr/online/bulky/guide), [Ollama 임베딩 API](https://docs.ollama.com/api/embed), [BGE-M3 모델 설명](https://huggingface.co/BAAI/bge-m3).
