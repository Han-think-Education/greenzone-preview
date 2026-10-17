# GreenZone Preview GitHub 업로드

저장소: https://github.com/Han-think-Education/greenzone-preview

현재 GitHub 앱 연결은 저장소 조회가 가능하지만 파일 업로드 권한이 403으로 거절됩니다. PC에서 `git push`로 업로드하세요. GitHub는 현재 **Public**이므로 API 키, `.env`, 주민 주소 원본, 개인정보는 업로드 금지입니다.

```powershell
# greenzone-preview 폴더에서 실행
git init -b main
git add .
git status --short
git commit -m "feat: GreenZone Preview WSL Docker and Ollama 11435"
git remote add origin https://github.com/Han-think-Education/greenzone-preview.git
git push -u origin main
```

`git remote add origin`에서 이미 origin이 있다고 나오면 `git remote -v`로 확인 후 기존 올바른 원격 주소를 사용하세요.
