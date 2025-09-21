# NH AI 상담 파트너 '말하지 않아도 알아요'

## 주요 기능

### 1. 실시간 이해도 분석
- 웹캠을 통한 고객 [표정 기반 이해도 판단 AI](https://huggingface.co/combe4259/face-comprehension)
- 시선 추적을 통한 읽기 패턴 분석
- 혼란도 감지 시 자동으로 쉬운 설명 제공
- [문장 난이도 분류 AI](https://huggingface.co/combe4259/difficulty_klue)를 통한 난이도 판단
### 2. 문장 간소화

- [금융 문장 변환 AI](https://huggingface.co/combe4259/fin_simplifier)로 고객이 이해하지 못하는 문장을 쉬운 문장으로  변환
- 문맥을 유지하면서 이해하기 쉬운 문장 생성
- 음성 안내 지원

### 3. 자연어 상담 내역 조회
- "최근에 가입한 예금 상품 보여줘" 같은 자연어 질의 지원
- [자연어 → SQL 변환 모델](https://huggingface.co/combe4259/NHSQLNL)로 데이터 조회
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
└── frontend/                   
    ├── customer/              # 고객용 상담 태블릿 
    │   └── public/
    │       └── mediapipe/     
    │           └── face_mesh/ # 얼굴 메시 모델
    │ 
    ├── staff/                 # 직원용 태블릿 
    └── report/                # 상담내역 조회가 가능한 어플리케이션 

    



```



## 기술 스택

### 백엔드
- **Python 3.12**: 메인 프로그래밍 언어
- **FastAPI**: 웹 프레임워크
- **SQLAlchemy**: ORM
- **SQLite**: 데이터베이스
- **PyTorch**: 딥러닝 프레임워크
- **MobileNetV2**: 경량 이미지 특징 추출기

### 프론트엔드
- **React 18**: UI 프레임워크
- **TypeScript**: 타입 안전성
- **MediaPipe**: 얼굴 인식 및 추적
- **WebRTC**: 실시간 웹캠 스트리밍
- **Axios**: HTTP 클라이언트
- **React Router**: 라우팅

### 데이터베이스
- **PostgreSQL**
-  주요 테이블 구조:
  - customers: 고객 정보
  - consultations: 상담 기록 (상품 타입, 상담 단계, 상태 등)
  - reading_analysis: 시선 추적 및 읽기 분석 데이터 (난이도, 혼란도, 시선데이터)
  - consultation_summaries: 상담 요약 리포트

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
