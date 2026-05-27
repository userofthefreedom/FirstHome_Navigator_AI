# FirstHome Navigator AI Frontend

Vue 3 + JavaScript + Vite 기반 프론트엔드입니다. TypeScript는 사용하지 않습니다.

## 실행

```powershell
npm ci
npm run dev
```

접속 주소:

```text
http://localhost:5173/
```

## 빌드

```powershell
npm run build
```

## 환경 변수

`.env.example`을 `.env`로 복사합니다.

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

Vite에서는 브라우저 코드에서 사용할 환경 변수 이름이 `VITE_`로 시작해야 합니다.
