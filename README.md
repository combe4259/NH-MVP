# 📊 Text Gaze Tracker - 시선 추적 기반 문맥 이해도 분석

MediaPipe + OpenCV 기반 실시간 텍스트 시선 추적 및 읽기 이해도 분석 시스템

## 🚀 주요 기능

### 핵심 기능
- **실시간 시선 추적** (MediaPipe Face Mesh)
- **텍스트 영역 감지** (Tesseract OCR)
- **시선 고정점(Fixation) 분석**
- **읽기 패턴 분석** (선형, 스캔, 집중)
- **읽기 속도 측정** (WPM)
- **회귀(Regression) 카운트**
- **히트맵 시각화**

### 🆕 신규 기능
- **문맥 이해도 측정** - 실시간 이해도 점수 (0-100%)
- **인지 부하 분석** - Cognitive Load 계산
- **어려운 단어 자동 감지** - 응시 시간 기반
- **한글 텍스트 지원** - 한국어 문서 분석

## 설치 방법

```bash
# 1. 가상환경 활성화
source venv/bin/activate

# 2. Tesseract 설치 (macOS)
brew install tesseract

# 3. 의존성 설치
pip install -r requirements.txt
```

## 🎯 실행 방법

### 1. 개선된 시선 추적 (권장)
```bash
python main_improved.py
```
- 실시간 조정 가능한 스케일
- 디버그 뷰 지원
- 머리 거리 자동 보정

### 2. 문맥 이해도 측정
```bash
python test_comprehension.py
```
- 실시간 이해도 점수
- 어려운 단어 감지
- 인지 부하 측정

### 3. 한글 텍스트 테스트
```bash
python test_korean_text.py
```
- LRU 리스트 구조 예제
- 한글 시선 추적

### 4. 캘리브레이션
```bash
python calibration.py
```
- 9-point 캘리브레이션
- 정확도 향상

## ⌨️ 키보드 컨트롤

| 키 | 기능 |
|---|------|
| `Q` | 종료 |
| `R` | 설정 리셋 |
| `S` | 세션 저장 |
| `H` | 히트맵 표시 |
| `D` | 디버그 모드 |
| `C` | 화면 클리어 |
| `W/A/S/D` | 오프셋 조정 |
| `↑↓←→` | 스케일 조정 |

## 📁 파일 구조

```
text-gaze-tracker/
├── 핵심 모듈
│   ├── gaze_tracker.py          # 시선 추적 엔진
│   ├── text_detector.py         # OCR 텍스트 감지
│   ├── text_gaze_analyzer.py    # 통합 분석
│   └── comprehension_analyzer.py # 이해도 분석 🆕
├── 실행 파일
│   ├── main_improved.py         # 메인 실행 (최신)
│   ├── test_comprehension.py    # 이해도 측정 🆕
│   ├── test_korean_text.py      # 한글 테스트 🆕
│   └── calibration.py           # 캘리브레이션
└── 설정
    └── requirements.txt         # 의존성 목록
```

## 📊 측정 지표

### 읽기 메트릭
- **Fixation Duration**: 시선 고정 시간 (ms)
- **Saccade**: 빠른 시선 이동
- **Regression Rate**: 재읽기 비율
- **Reading Speed**: 분당 단어 수 (WPM)

### 이해도 메트릭 🆕
- **Comprehension Score**: 0-100% 이해도 점수
- **Cognitive Load**: 인지 부하 (0-1)
- **Difficult Words**: 어려운 단어 자동 감지
- **Reading Efficiency**: 이해도 조정 WPM

## 🎓 활용 분야

- **교육**: 학생 읽기 능력 평가, 난독증 진단 보조
- **UX 리서치**: 문서 가독성 테스트, UI 텍스트 최적화
- **의료**: 인지 장애 진단, 읽기 치료
- **연구**: 인지 과학 실험, 주의력 연구

## 🔧 문제 해결

### 카메라 권한 (macOS)
```
시스템 설정 → 개인정보 보호 및 보안 → 카메라 → Terminal 허용
```

### 시선 정확도 향상
1. `python calibration.py` 실행
2. 균일한 조명 확보
3. 카메라 거리 50-70cm 유지

### 한글 폰트 설정
```python
# macOS 기본 한글 폰트
/System/Library/Fonts/AppleSDGothicNeo.ttc
```

## 📄 라이선스

MIT License

---

**Note**: 연구 및 교육 목적으로 개발. 의료 진단용으로 사용 금지.