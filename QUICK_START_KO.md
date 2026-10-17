# 그린존 프리뷰 — Windows Ollama 11435 / WSL Docker

현재 로컬 구성에 맞춘 **기본 실행은 Docker에서 웹만 실행**합니다. Ollama 설치나 모델 재다운로드는 불필요합니다(선택 모델이 설치된 경우).

## STEP 1: Windows Ollama 확인

```powershell
Invoke-RestMethod http://127.0.0.1:11435/api/tags
```

모델 목록의 `name`을 보고 `.env`의 `OLLAMA_MODEL`로 지정합니다.

## STEP 2: 설정 및 실행

```powershell
Copy-Item .env.example .env
notepad .env
docker compose up -d --build
docker compose ps
```

- 화면: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs
- Ollama 상태: http://127.0.0.1:8000/api/ai/status

## STEP 3: 컨테이너 → Windows Ollama 연결 검사

```powershell
docker compose exec web python -c "import os,httpx; u=os.environ['OLLAMA_BASE_URL']; r=httpx.get(u+'/api/tags',timeout=5); print(u,r.status_code,r.text[:240])"
```

상태 코드가 `200`이면 네트워크 접근은 성공입니다. `model_installed:false`라면 로컬에 설치된 정확한 Ollama 모델 이름을 `.env`에 적고 `docker compose up -d`로 반영합니다.

`host.docker.internal`이 해석되지 않거나 연결이 거부된다면 Docker Desktop WSL integration 사용 여부와 Windows Ollama의 수신 바인딩을 확인해야 합니다. WSL 내부에 독립 Docker Engine을 설치한 경우 Windows 호스트 접근 주소가 다를 수 있습니다. 보안을 위해 Ollama 포트를 공용 네트워크에 개방하지 마세요.

## 선택: Ollama까지 Docker에서 구동하려면

```powershell
docker compose -f compose.yaml -f compose.container-ollama.yaml up -d --build
docker compose -f compose.yaml -f compose.container-ollama.yaml exec ollama ollama pull qwen2.5:1.5b
```

이 모드는 Windows Ollama와 **별개 인스턴스**이며 현재 사용 환경에서는 권장하지 않습니다.

## GitHub 최초 업로드 (저장소는 현재 빈 상태)

```powershell
git init -b main
git add .
git status --short
git commit -m "feat: GreenZone Preview WSL Docker and Ollama 11435"
git remote add origin https://github.com/Han-think-Education/greenzone-preview.git
git push -u origin main
```

실제 `.env`가 `git status --short`에 나타나면 **커밋하지 말고 제외 설정을 다시 확인**하세요. 저장소는 현재 Public입니다.
