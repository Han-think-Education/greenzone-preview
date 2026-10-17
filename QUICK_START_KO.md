# 그린존 실행 안내

## 가장 간단한 실행

프로젝트 폴더에서 실행합니다.

```powershell
python -m pip install -r backend/requirements.txt
python run_local.py
```

- 기본 화면: http://127.0.0.1:8000
- 담당자 접속정보: storage/local-access.txt (자동 발급한 경우)
- 다른 포트: python run_local.py --port 8778
- 종료: 실행 창에서 Ctrl+C
- Windows 실행 파일: START_GREENZONE.bat

초기 데이터는 가상입니다. 담당자 정보 수정은 서버 실행과 로그인이 필요합니다.

## Docker로 실행

.env.example을 .env로 복사한 뒤, 관리 기능을 쓸 경우 ADMIN_PASSWORD를 12자 이상으로 정합니다.

```powershell
Copy-Item .env.example .env
# .env를 편집한 뒤 실행
docker compose up -d --build
```

기존 SQLite 볼륨을 유지하며 자료를 초기화하지 않습니다.

## AI를 쓰고 싶을 때

기본은 꺼져 있습니다. 실제 Ollama 서버와 사용할 모델이 준비된 경우에만 .env를 바꿉니다.

```text
GREENZONE_AI_ENABLED=1
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=설치한_모델의_정확한_이름
```

직접 Python으로 실행하는 주소 예시입니다. Docker에서는 host.docker.internal과 실제 서버 포트를 사용합니다. 다른 포트로 운영한다면 문서 예시를 따르지 말고 실제 주소로 맞춥니다. 모델이 없어도 기본 안내 웹은 동작합니다.

## 자료 교체

[구현 안내](docs/IMPLEMENTATION_GUIDE.md)의 CSV·메타정보·별도 새 DB 절차를 따릅니다. 이미 담당자가 수정한 DB는 파일 변경만으로 덮어쓰지 않습니다.

.env, storage/local-access.txt, 실제 DB를 공개 저장소에 올리지 않습니다.
## 사용자·관리자 화면

실행 후 `/`는 사용자 지도, `/admin`은 담당자 로그인·수정 화면입니다. 사용자 지도에서 **내 위치** 또는 **선택 건물로 시연**으로 가까운 제안 후보를 확인합니다. 지도 확대·이동과 건물별 배정 조회를 함께 제공합니다. 현재 후보는 실제 배출 가능한 운영 장소가 아닌 가상 자료입니다.
