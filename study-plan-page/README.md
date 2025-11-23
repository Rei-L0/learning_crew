# Study Plan Page - Setup Guide

## API Keys 설정

이 프로젝트는 Gemini API를 사용합니다. API 키는 보안을 위해 별도로 관리됩니다.

### 설정 방법:

1. `api-keys.example.js` 파일을 복사하여 `api-keys.js` 파일을 생성합니다:
   ```bash
   cp api-keys.example.js api-keys.js
   ```

2. `api-keys.js` 파일을 열어 실제 Gemini API 키로 교체합니다:
   ```javascript
   export const GEMINI_API_KEY = "YOUR_ACTUAL_GEMINI_API_KEY";
   ```

3. `api-keys.js` 파일은 `.gitignore`에 포함되어 있어 Git에 커밋되지 않습니다.

### 주의사항:

- ⚠️ **절대로 `api-keys.js` 파일을 Git에 커밋하지 마세요!**
- ✅ Git에는 `api-keys.example.js` 템플릿만 포함됩니다
- ✅ Firebase 설정 (`firebaseConfig`)은 공개되어도 괜찮습니다 (Security Rules로 보안 관리)

## 로컬 서버 실행

```bash
python3 -m http.server 8000
```

http://localhost:8000/study-plan-page/ 에서 확인할 수 있습니다.
