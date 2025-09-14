-- NH 스마트 상담 분석 시스템 테이블 생성
-- Supabase SQL Editor에서 실행

-- 1. 고객 테이블
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. 상담 테이블
CREATE TABLE consultations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    product_type VARCHAR(50) NOT NULL,
    product_details JSONB,
    consultation_phase VARCHAR(20) DEFAULT 'product_intro',
    start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. 읽기 분석 결과 테이블
CREATE TABLE reading_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consultation_id UUID REFERENCES consultations(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    section_name VARCHAR(100) NOT NULL,
    section_text TEXT,
    difficulty_score DECIMAL(3,2),
    confusion_probability DECIMAL(3,2),
    comprehension_level VARCHAR(10),
    gaze_data JSONB,
    analysis_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. 상담 요약 테이블
CREATE TABLE consultation_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consultation_id UUID REFERENCES consultations(id) ON DELETE CASCADE,
    overall_difficulty DECIMAL(3,2),
    confused_sections TEXT[],
    total_sections INTEGER,
    comprehension_high INTEGER DEFAULT 0,
    comprehension_medium INTEGER DEFAULT 0,
    comprehension_low INTEGER DEFAULT 0,
    recommendations TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 생성
CREATE INDEX idx_consultations_customer_id ON consultations(customer_id);
CREATE INDEX idx_consultations_status ON consultations(status);
CREATE INDEX idx_reading_analysis_consultation_id ON reading_analysis(consultation_id);
CREATE INDEX idx_reading_analysis_timestamp ON reading_analysis(analysis_timestamp);

-- RLS (Row Level Security) 비활성화 (개발용)
ALTER TABLE customers DISABLE ROW LEVEL SECURITY;
ALTER TABLE consultations DISABLE ROW LEVEL SECURITY;
ALTER TABLE reading_analysis DISABLE ROW LEVEL SECURITY;
ALTER TABLE consultation_summaries DISABLE ROW LEVEL SECURITY;