-- 기존 데이터 삭제
DELETE FROM consultation_summaries;
DELETE FROM reading_analysis;
DELETE FROM consultations;
DELETE FROM customers;

-- 1. 고객 데이터만 먼저 삽입
INSERT INTO customers (name) VALUES
('김민수'),
('이서연'),
('박정호');

-- 2. 상담 데이터 삽입 (JSON 문자열을 한 줄로 수정)
INSERT INTO consultations (customer_id, product_type, product_details, consultation_phase, start_time, status)
SELECT
    c.id,
    CASE
        WHEN c.name = '김민수' THEN '예금'
        WHEN c.name = '이서연' THEN '적금'
        WHEN c.name = '박정호' THEN '펀드'
    END,
    CASE
        -- ERROR FIX: Multi-line JSON strings are combined into a single line.
        WHEN c.name = '김민수' THEN '{"name": "NH Smart 예금", "type": "예금", "amount": "10,000,000원", "period": "1년", "interestRate": "연 3.5%"}'::JSONB
        WHEN c.name = '이서연' THEN '{"name": "NH 올원 적금", "type": "적금", "amount": "500,000원/월", "period": "24개월", "interestRate": "연 4.5%"}'::JSONB
        WHEN c.name = '박정호' THEN '{"name": "NH-Amundi 글로벌 펀드", "type": "펀드", "amount": "5,000,000원", "period": "자유", "interestRate": "변동금리"}'::JSONB
    END,
    CASE
        WHEN c.name = '김민수' THEN 'terms_reading'
        WHEN c.name = '이서연' THEN 'application'
        WHEN c.name = '박정호' THEN 'product_intro'
    END,
    CASE
        WHEN c.name = '김민수' THEN NOW() - INTERVAL '25 minutes'
        WHEN c.name = '이서연' THEN NOW() - INTERVAL '15 minutes'
        WHEN c.name = '박정호' THEN NOW() - INTERVAL '35 minutes'
    END,
    'active'
FROM customers c;

-- 3. 읽기 분석 데이터 삽입 (JSON 문자열을 한 줄로 수정)
INSERT INTO reading_analysis (consultation_id, customer_id, section_name, section_text, difficulty_score, confusion_probability, comprehension_level, gaze_data)
SELECT
    cons.id,
    cons.customer_id,
    CASE
        WHEN cust.name = '김민수' THEN '중도해지 시 불이익'
        WHEN cust.name = '이서연' THEN '가입 신청서 작성'
        WHEN cust.name = '박정호' THEN '투자 위험 고지'
    END,
    CASE
        WHEN cust.name = '김민수' THEN '중도해지 시 약정금리에서 0.5%포인트 차감하여 지급됩니다.'
        WHEN cust.name = '이서연' THEN '개인정보 수집·이용 동의서를 작성해 주시기 바랍니다.'
        WHEN cust.name = '박정호' THEN '이 상품은 원금 손실 가능성이 있으며, 투자성과에 따라 수익이 달라질 수 있습니다.'
    END,
    CASE
        WHEN cust.name = '김민수' THEN 0.75
        WHEN cust.name = '이서연' THEN 0.25
        WHEN cust.name = '박정호' THEN 0.90
    END,
    CASE
        WHEN cust.name = '김민수' THEN 0.70
        WHEN cust.name = '이서연' THEN 0.20
        WHEN cust.name = '박정호' THEN 0.85
    END,
    CASE
        WHEN cust.name = '김민수' THEN 'medium'
        WHEN cust.name = '이서연' THEN 'high'
        WHEN cust.name = '박정호' THEN 'low'
    END,
    CASE
        -- ERROR FIX: Multi-line JSON strings are combined into a single line.
        WHEN cust.name = '김민수' THEN '{"fixation_duration": 4500, "saccade_count": 12, "regression_count": 3}'::JSONB
        WHEN cust.name = '이서연' THEN '{"fixation_duration": 2800, "saccade_count": 6, "regression_count": 0}'::JSONB
        WHEN cust.name = '박정호' THEN '{"fixation_duration": 8200, "saccade_count": 25, "regression_count": 8}'::JSONB
    END
FROM consultations cons
JOIN customers cust ON cons.customer_id = cust.id;

-- 4. 상담 요약 데이터 삽입
INSERT INTO consultation_summaries (consultation_id, overall_difficulty, confused_sections, total_sections, comprehension_high, comprehension_medium, comprehension_low, recommendations)
SELECT
    cons.id,
    CASE
        WHEN cust.name = '김민수' THEN 0.75
        WHEN cust.name = '이서연' THEN 0.25
        WHEN cust.name = '박정호' THEN 0.90
    END,
    CASE
        WHEN cust.name = '김민수' THEN ARRAY['중도해지 불이익', '우대금리 조건']
        WHEN cust.name = '이서연' THEN ARRAY[]::TEXT[]
        WHEN cust.name = '박정호' THEN ARRAY['투자 위험 등급', '환매 수수료', '과세 체계']
    END,
    CASE
        WHEN cust.name = '김민수' THEN 5
        WHEN cust.name = '이서연' THEN 3
        WHEN cust.name = '박정호' THEN 6
    END,
    CASE
        WHEN cust.name = '김민수' THEN 1
        WHEN cust.name = '이서연' THEN 3
        WHEN cust.name = '박정호' THEN 0
    END,
    CASE
        WHEN cust.name = '김민수' THEN 2
        WHEN cust.name = '이서연' THEN 0
        WHEN cust.name = '박정호' THEN 2
    END,
    CASE
        WHEN cust.name = '김민수' THEN 2
        WHEN cust.name = '이서연' THEN 0
        WHEN cust.name = '박정호' THEN 4
    END,
    CASE
        WHEN cust.name = '김민수' THEN ARRAY['중도해지 수수료 계산 예시 제공', '우대금리 조건 체크리스트 제공']
        WHEN cust.name = '이서연' THEN ARRAY['자동이체 설정 안내', '세제혜택 추가 설명 준비']
        WHEN cust.name = '박정호' THEN ARRAY['투자 시뮬레이션 도구 활용', '단계별 설명으로 전환']
    END
FROM consultations cons
JOIN customers cust ON cons.customer_id = cust.id;

-- 확인 쿼리
SELECT 'customers' as table_name, COUNT(*) as count FROM customers
UNION ALL
SELECT 'consultations', COUNT(*) FROM consultations
UNION ALL
SELECT 'reading_analysis', COUNT(*) FROM reading_analysis
UNION ALL
SELECT 'consultation_summaries', COUNT(*) FROM consultation_summaries;