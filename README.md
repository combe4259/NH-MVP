# NH AI 상담 파트너 '말하지 않아도 알아요'

## 주요 기능

### 1. 실시간 이해도 분석
- 웹캠을 통한 고객 표정 기반 이해도 판단
- 시선 추적을 통한 읽기 패턴 분석
- 혼란도 감지 시 자동으로 쉬운 설명 제공

### 2. 문장 간소화
- 복잡한 금융 용어를 쉬운 문장으로 자동 변환
- 문맥을 유지하면서 이해하기 쉬운 문장 생성
- 음성 안내 지원

### 3. 자연어 상담 내역 조회
- "최근에 가입한 예금 상품 보여줘" 같은 자연어 질의 지원
- SQL 자동 변환 및 데이터 조회
- 상담/가입 내역 관리

### 4. 직원용 대시보드
- 고객 이해도 실시간 모니터링
- 상담 진행 상황 추적
- AI 상담 가이드


## 프로젝트 구조

```
text-gaze-tracker/
│
├── backend/                    # FastAPI 백엔드 서버
│   ├── main.py                # FastAPI 앱 진입점
│   ├── routers/               # API 라우터
│   │   ├── ai_model.py       # AI 모델  API
│   │   └── consultation.py   # 상담 API
│   ├── models/                # 데이터베이스 모델
│   │   └── consultation.py   # 상담 데이터 모델
│   ├── services/              # 비즈니스 로직
│   │   └── ai_model_service.py  # AI 모델 서비스 
│   └── model_cache/           # 모델 캐시 디렉토리
│
├── frontend/                   # 프론트엔드 애플리케이션
│   ├── customer/              # 고객용 웹 앱
│   │   ├── src/
│   │   │   ├── components/   # React 컴포넌트
│   │   │   │   ├── AIAssistant.tsx        # AI 어시스턴트 채팅
│   │   │   │   ├── DocumentViewer.tsx     # 문서 뷰어
│   │   │   │   ├── EmotionRecognition.tsx # 표정 인식
│   │   │   │   ├── EyeTracker.tsx         # 시선 추적
│   │   │   │   ├── PDFViewer.tsx          # PDF 뷰어
│   │   │   │   └── WebcamFaceDetection.tsx # 웹캠 얼굴 감지
│   │   │   ├── services/
│   │   │   │   └── RealtimeAnalysisService.tsx # 실시간 분석 서비스
│   │   │   └── api/
│   │   │       └── backend.ts  # 백엔드 API 클라이언트
│   │   └── public/
│   │       └── mediapipe/     # MediaPipe 라이브러리
│   │           └── face_mesh/ # 얼굴 메시 모델
│   │
│   ├── staff/                 # 직원용 웹 앱
│   │   └── src/
│   │       └── App.tsx        # 직원용 대시보드
│   │
│   └── report/                # 리포트 웹 앱
│       └── src/
│           ├── Home.tsx       # 홈 화면
│           ├── Overview.tsx   # 상품 개요
│           ├── Consulting.tsx # 상담 내역
│           └── Menu.tsx       # 메뉴 네비게이션
│
├── face/                      # 얼굴 인식 및 혼란도 판단 모델
    ├── daisee_confusion_binary_improved.py  # 개선된 혼란도 판단 모델
    ├── face-comprehension/   # 얼굴 이해도 모델
    └── model_cache/           # 모델 캐시



```

## 기술 스택

### 백엔드
- **Python 3.12**: 메인 프로그래밍 언어
- **FastAPI**: 웹 프레임워크
- **SQLAlchemy**: ORM
- **SQLite**: 데이터베이스
- **Transformers (HuggingFace)**: NLP 모델
  - KR-FinBert: 금융 도메인 특화 언어 모델
  - combe4259/fin_simplifier: 문장 간소화 모델
  - combe4259/face-comprehension: 얼굴 이해도 판단 모델
- **PyTorch**: 딥러닝 프레임워크
- **MobileNetV2**: 경량 이미지 특징 추출기

### 프론트엔드
- **React 18**: UI 프레임워크
- **TypeScript**: 타입 안전성
- **MediaPipe**: 얼굴 인식 및 추적
- **WebRTC**: 실시간 웹캠 스트리밍
- **Axios**: HTTP 클라이언트
- **React Router**: 라우팅

### AI/ML 모델
- **얼굴 표정 인식**: MobileNetV2 기반 경량 모델
- **문장 간소화**: KR-FinBert 기반 금융 문장 간소화
- **자연어-SQL 변환**: T5 기반 NL to SQL 변환
- **혼란도 판단**: DAiSEE 데이터셋 기반 이진 분류 모델

## 설치 및 실행 방법

### 필수 요구사항
- Python 3.12 이상
- Node.js 18 이상
- npm 또는 yarn

### 백엔드 설정

1. Python 가상환경 생성 및 활성화
```bash
cd text-gaze-tracker
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. 필요한 패키지 설치
```bash
pip install fastapi uvicorn sqlalchemy transformers torch torchvision pillow opencv-python
```

3. 백엔드 서버 실행
```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 프론트엔드 설정

#### 고객용 앱 실행
```bash
cd frontend/customer
npm install
npm start
```
http://localhost:3000 에서 접속 가능

#### 직원용 대시보드 실행
```bash
cd frontend/staff
npm install
npm start
```
http://localhost:3001 에서 접속 가능

#### 리포트 앱 실행
```bash
cd frontend/report
npm install
npm start
```
http://localhost:3002 에서 접속 가능
