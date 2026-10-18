# GitHub 공유와 업데이트

저장소: https://github.com/Han-think-Education/greenzone-preview

## 팀원 시작

```powershell
git clone https://github.com/Han-think-Education/greenzone-preview.git
cd greenzone-preview
```

이후 [실행 안내](../QUICK_START_KO.md)에 따라 개인 `.env`를 만들고 Docker 웹을 실행합니다. 공유 설정의 Ollama 기본 포트는 **11434**입니다. 실제 `.env`는 팀원이 직접 채우며 저장소에 포함하지 않습니다.

## 변경 공유

```powershell
git status --short
git add .
git diff --cached --stat
git commit -m "feat: update GreenZone preview and team guide"
git push origin main
```

커밋 전 `.env`·키·관리자 암호·실행 DB·세션·개인 접속정보가 제외되어 있는지 확인합니다. `.env.example`의 키·암호 입력란은 비워 둡니다. 화면 캡처에는 로그인 암호나 개인 위치를 담지 않습니다. 일반지도는 추가 데이터 키 없이 실행하고 영상지도는 본인 VWorld 키로 연결합니다.

시제품의 제안 조사점과 실제 운영 배출장소를 구분해서 설명합니다. [화면별 공유 안내](TEAM_PREVIEW_GUIDE.md)에서 구현 목적과 확인 범위를 확인하세요.
