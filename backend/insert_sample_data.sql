-- 기존 데이터 삭제
DELETE FROM consultation_summaries;
DELETE FROM reading_analysis;
DELETE FROM consultations;
DELETE FROM customers;

-- 1. '김민수' 고객 데이터만 삽입 (고정 ID 사용)
INSERT INTO customers (id, name) VALUES ('cd507d56-7eff-4819-9ac4-8c400c0340f6', '김민수');

-- 2. '김민수' 고객의 ELS 상담 데이터 5개 삽입
INSERT INTO consultations (customer_id, product_type, product_details, consultation_phase, start_time, end_time, status)
VALUES
    ('cd507d56-7eff-4819-9ac4-8c400c0340f6', 'ELS', '{"name": "N2 ELS 제44회 파생결합증권", "type": "ELS", "amount": "10,000,000원", "period": "3년", "interestRate": "변동수익"}'::JSONB, 'completed', '2025-10-17 10:30:00+09', '2025-10-17 11:00:00+09', 'completed'),
    ('cd507d56-7eff-4819-9ac4-8c400c0340f6', 'ELS', '{"name": "N2 ELS 제58회 파생결합증권", "type": "ELS (Step-Down)", "yield": "23.80%", "assets": "Tesla, Palantir"}'::JSONB, 'completed', '2025-10-15 11:00:00+09', '2025-10-15 11:30:00+09', 'completed'),
    ('cd507d56-7eff-4819-9ac4-8c400c0340f6', 'ELS', '{"name": "N2 ELS 제51회 파생결합증권", "type": "ELS (월지급식)", "yield": "14.31%", "assets": "SK이노베이션, 삼성SDI"}'::JSONB, 'completed', '2025-10-11 14:00:00+09', '2025-10-11 14:30:00+09', 'completed'),
    ('cd507d56-7eff-4819-9ac4-8c400c0340f6', 'ELS', '{"name": "N2 ELS 제55회 파생결합증권", "type": "ELS (Step-Down)", "yield": "16.60%", "assets": "한화에어로, KOSPI200"}'::JSONB, 'completed', '2025-10-10 09:30:00+09', '2025-10-10 10:00:00+09', 'completed'),
    ('cd507d56-7eff-4819-9ac4-8c400c0340f6', 'ELS', '{"name": "N2 ELS 제57회 파생결합증권", "type": "ELS (Step-Down)", "yield": "13.30%", "assets": "Shopify, S&P500"}'::JSONB, 'completed', '2025-10-05 16:00:00+09', '2025-10-05 16:30:00+09', 'completed');

-- 확인 쿼리
SELECT 'customers' as table_name, COUNT(*) as count FROM customers
UNION ALL
SELECT 'consultations', COUNT(*) FROM consultations;