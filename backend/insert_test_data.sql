-- 테스트 데이터 삽입 스크립트

-- 1. 고객 생성
INSERT INTO customers (id, name, created_at) VALUES
('11111111-1111-1111-1111-111111111111', '김민수', NOW() - INTERVAL '1 hour'),
('22222222-2222-2222-2222-222222222222', '이서연', NOW() - INTERVAL '2 hours'),
('33333333-3333-3333-3333-333333333333', '박정호', NOW() - INTERVAL '3 hours')
ON CONFLICT (id) DO NOTHING;

-- 2. 상담 세션 생성
INSERT INTO consultations (id, customer_id, product_type, product_details, consultation_phase, start_time, status) VALUES
(
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    '11111111-1111-1111-1111-111111111111',
    'ELS(주가연계증권)',
    '{
        "name": "N2 ELS 제44회 파생결합증권(주가연계증권)",
        "type": "ELS",
        "amount": "10,000,000원",
        "period": "3년",
        "interest_rate": "변동수익",
        "current_section": "원금손실 조건"
    }'::jsonb,
    'terms_reading',
    NOW() - INTERVAL '5 minutes',
    'active'
),
(
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
    '22222222-2222-2222-2222-222222222222',
    '적금',
    '{
        "name": "NH 올원 적금",
        "type": "적금",
        "amount": "500,000원/월",
        "period": "24개월",
        "interest_rate": "연 4.5%",
        "current_section": "가입 신청서 작성"
    }'::jsonb,
    'application',
    NOW() - INTERVAL '3 minutes',
    'active'
),
(
    'cccccccc-cccc-cccc-cccc-cccccccccccc',
    '33333333-3333-3333-3333-333333333333',
    '펀드',
    '{
        "name": "NH-Amundi 글로벌 펀드",
        "type": "펀드",
        "amount": "5,000,000원",
        "period": "자유",
        "interest_rate": "변동금리",
        "current_section": "투자 위험 고지"
    }'::jsonb,
    'product_intro',
    NOW() - INTERVAL '10 minutes',
    'active'
)
ON CONFLICT (id) DO NOTHING;

-- 3. 읽기 분석 데이터 (김민수 - ELS 상담)
INSERT INTO reading_analysis (consultation_id, customer_id, section_name, section_text, difficulty_score, confusion_probability, comprehension_level, analysis_timestamp) VALUES
(
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    '11111111-1111-1111-1111-111111111111',
    '원금손실 조건',
    '원금손실(손실률)은 만기평가가격이 최초기준가격 대비 가장 낮은 기초자산의 하락률만큼 발생합니다.',
    0.85,
    0.82,
    'low',
    NOW() - INTERVAL '2 minutes'
),
(
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    '11111111-1111-1111-1111-111111111111',
    '기초자산 평가',
    '세 개의 기초자산 중 어느 하나라도 최초기준가격의 50% 미만인 경우 원금손실이 발생합니다.',
    0.78,
    0.75,
    'low',
    NOW() - INTERVAL '1 minute'
)
ON CONFLICT DO NOTHING;

-- 4. 읽기 분석 데이터 (박정호 - 펀드 상담)
INSERT INTO reading_analysis (consultation_id, customer_id, section_name, section_text, difficulty_score, confusion_probability, comprehension_level, analysis_timestamp) VALUES
(
    'cccccccc-cccc-cccc-cccc-cccccccccccc',
    '33333333-3333-3333-3333-333333333333',
    '투자 위험 등급',
    '이 펀드는 투자 위험 등급 3등급으로 중간 수준의 위험을 가지고 있습니다.',
    0.72,
    0.68,
    'low',
    NOW() - INTERVAL '5 minutes'
),
(
    'cccccccc-cccc-cccc-cccc-cccccccccccc',
    '33333333-3333-3333-3333-333333333333',
    '환매 수수료',
    '펀드 환매 시 보유기간에 따라 차등 수수료가 부과됩니다.',
    0.65,
    0.62,
    'medium',
    NOW() - INTERVAL '3 minutes'
)
ON CONFLICT DO NOTHING;

COMMIT;
