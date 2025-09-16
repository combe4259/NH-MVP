import json
import random
import uuid

# ----------------------------------------------------------------------
# 1. 스키마 파일 생성 (AI Hub 형식) - (V4.1: PK/FK 인덱스 정밀 수정)
# ----------------------------------------------------------------------
def generate_schema_annotation_file():
    """
    (V4.1) 제공된 DB 스키마를 기반으로 AI Hub 형식의
    'db_annotation.json' 파일을 생성합니다.
    (PK/FK 컬럼 인덱스를 정밀하게 수정)
    """
    print("[1/2] (V4.1) 스키마 파일 생성 시작...")

    db_id = "nh_consultation_db"

    # 컬럼 리스트 (이 인덱스 기준으로 PK/FK 매핑)
    # 0: *
    # customers: 1(id), 2(name), 3(created_at)
    # consultations: 4(id), 5(customer_id), ...
    # reading_analysis: 14(id), 15(consultation_id), 16(customer_id), ...
    # consultation_summaries: 25(id), 26(consultation_id), ...

    column_names_original_list = [
        [-1, "*"],
        # customers (table 0) - Indices 1, 2, 3
        [0, "id"], [0, "name"], [0, "created_at"],
        # consultations (table 1) - Indices 4~13
        [1, "id"], [1, "customer_id"], [1, "product_type"],
        [1, "product_details"], [1, "consultation_phase"],
        [1, "start_time"], [1, "end_time"], [1, "status"],
        [1, "created_at"], [1, "detailed_info"],
        # reading_analysis (table 2) - Indices 14~24
        [2, "id"], [2, "consultation_id"], [2, "customer_id"],
        [2, "section_name"], [2, "section_text"], [2, "difficulty_score"],
        [2, "confusion_probability"], [2, "comprehension_level"],
        [2, "gaze_data"], [2, "analysis_timestamp"], [2, "created_at"],
        # consultation_summaries (table 3) - Indices 25~34
        [3, "id"], [3, "consultation_id"], [3, "overall_difficulty"],
        [3, "confused_sections"], [3, "total_sections"],
        [3, "comprehension_high"], [3, "comprehension_medium"],
        [3, "comprehension_low"], [3, "recommendations"], [3, "created_at"]
    ]

    schema_data = {
        "Dataset": {"identifier": "NH_MVP_2025", "name": "NH 상담 내역 Text-to-SQL 데이터", "category": 9, "type": 0},
        "data": [
            {
                "source": "NH-MVP",
                "db_id": db_id,
                "table_names_original": ["customers", "consultations", "reading_analysis", "consultation_summaries"],
                "table_names": ["고객 테이블", "상담 테이블", "읽기 분석 결과 테이블", "상담 요약 테이블"],
                "column_names_original": column_names_original_list,
                "column_names": [
                    [-1, "*"],
                    [0, "고객 ID"], [0, "고객명"], [0, "생성일시"],
                    [1, "상담 ID"], [1, "고객 ID"], [1, "상품 유형"], [1, "상품 상세 (JSON)"], [1, "상담 단계"], [1, "시작 시간"], [1, "종료 시간"], [1, "상태"], [1, "생성일시"], [1, "상세 정보 (JSON)"],
                    [2, "분석 ID"], [2, "상담 ID"], [2, "고객 ID"], [2, "섹션명"], [2, "섹션 텍스트"], [2, "난이도 점수"], [2, "혼동 확률"], [2, "이해도 수준"], [2, "시선 데이터 (JSON)"], [2, "분석 시간"], [2, "생성일시"],
                    [3, "요약 ID"], [3, "상담 ID"], [3, "전체 난이도"], [3, "혼동 섹션 (배열)"], [3, "총 섹션 수"], [3, "이해도(상) 수"], [3, "이해도(중) 수"], [3, "이해도(하) 수"], [3, "권장사항 (배열)"], [3, "생성일시"]
                ],
                "column_types": ["text", "uuid", "text", "time", "uuid", "uuid", "text", "jsonb", "text", "time", "time", "text", "time", "jsonb", "uuid", "uuid", "uuid", "text", "text", "number", "number", "text", "jsonb", "time", "time", "uuid", "uuid", "number", "array", "number", "number", "number", "number", "array", "time"],

                # (수정) PK 컬럼의 정확한 인덱스 (0번 '*' 제외)
                "primary_keys": [1, 4, 14, 25],

                # (수정) FK 컬럼 인덱스 -> PK 컬럼 인덱스 매핑
                "foreign_keys": [
                    [5, 1],  # consultations.customer_id (idx 5) -> customers.id (idx 1)
                    [15, 4], # reading_analysis.consultation_id (idx 15) -> consultations.id (idx 4)
                    [16, 1], # reading_analysis.customer_id (idx 16) -> customers.id (idx 1)
                    [26, 4]  # consultation_summaries.consultation_id (idx 26) -> consultations.id (idx 4)
                ]
            }
        ]
    }

    file_name = "nh_consultation_db_annotation.json"
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(schema_data, f, ensure_ascii=False, indent=2)

    print(f"✅ (V4.1) 스키마 파일 생성 완료: {file_name} (db_id: '{db_id}')\n")
    return db_id


# ----------------------------------------------------------------------
# 2. '정교한' 라벨 파일 생성 (V4) - (V4 로직과 동일, 총 780개 생성)
# ----------------------------------------------------------------------

# --- 확장용 엔티티 리스트 정의 ---
PRODUCTS_LIST = ["예금", "적금", "펀드", "청약", "대출", "보험", "ISA", "연금"]
STATUS_LIST = [("진행중인", "active"), ("완료된", "completed"), ("미완료", "!='completed'")]
TIME_FILTERS_LIST = [
    ("오늘", "DATE(start_time) = CURRENT_DATE"),
    ("이번주", "start_time >= DATE_TRUNC('week', CURRENT_DATE)"),
    ("이번달", "DATE_TRUNC('month', start_time) = DATE_TRUNC('month', CURRENT_DATE)"),
    ("최근 7일", "start_time >= CURRENT_DATE - INTERVAL '7 days'"),
    ("올해", "EXTRACT(YEAR FROM start_time) = EXTRACT(YEAR FROM CURRENT_DATE)")
]
PRODUCT_NAMES_MAP = {
    "적금": ["NH 올원 적금", "NH 청년 적금", "NH 자유 적금"],
    "예금": ["NH Smart 예금", "NH 행복 예금"],
    "펀드": ["NH-Amundi 글로벌 펀드", "NH ESG 펀드", "NH 국내주식 펀드"]
}
AMOUNTS_LIST = [("1000만원", 10000000), ("5000만원", 50000000), ("1억", 100000000)]
RATES_LIST = [("4%", 4.0), ("4.5%", 4.5), ("5%", 5.0)]

# --- (핵심 V4) '의도 + 쿼리 템플릿 + 발화 템플릿' 정의 (14개 의도) ---
INTENT_BASED_QUERIES = [
    # --- 의도 1: 기본 상품 조회 (가장 빈번) ---
    {
        "intent_id": "BASIC_PRODUCT_LOOKUP",
        "query_template": "SELECT * FROM consultations WHERE customer_id = :current_user_id AND product_type = '{product}' ORDER BY start_time DESC;",
        "utterance_templates": [
            "내 {product} 상담 내역", "{product} 상담 받은 거 보여줘", "{product} 관련 상담 조회", "내가 받은 {product} 상담들",
            "{product} 상담 기록 확인", "{product} 언제 상담받았지?", "{product} 상담 있었나?", "{product} 상담했던 거 목록 좀",
            "내가 상담받은 {product} 리스트", "{product} 상담 이력 조회", "{product} 관련해서 상담한 거 다 줘",
            "{product} 최근에 상담한거부터 보여줘", "내 {product} 상담 기록", "혹시 {product} 상담한 거 있어?", "지난번에 {product} 상담한 내역"
        ],
        "entities": {"product": PRODUCTS_LIST}
    },
    # --- 의도 2: 상품 + 상태 조회 ---
    {
        "intent_id": "PRODUCT_WITH_STATUS",
        "query_template": "SELECT * FROM consultations WHERE customer_id = :current_user_id AND product_type = '{product}' AND status = '{status_sql}' ORDER BY start_time DESC;",
        "utterance_templates": [
            "{status_text} {product} 상담", "{status_text} {product} 상담 내역 보여줘", "내 {product} 중에 {status_text} 것들",
            "{product} 상담 {status_text} 리스트", "{product} 상담 건 중에 {status_text} 것", "{status_text} 상태인 {product} 상담 목록",
            "아직 {status_text} {product} 상담 뭐있지?", "내 {product} 중에서 {status_text} 처리된 거"
        ],
        "entities": {"product": PRODUCTS_LIST, "status": [s for s in STATUS_LIST if s[1] != "!='completed'"]}
    },
    # --- 의도 3: 상품 + 시간 조회 ---
    {
        "intent_id": "PRODUCT_WITH_TIME",
        "query_template": "SELECT * FROM consultations WHERE customer_id = :current_user_id AND product_type = '{product}' AND {time_sql} ORDER BY start_time DESC;",
        "utterance_templates": [
            "{time_text} {product} 상담", "{time_text} 받은 {product} 상담 내역", "{product} 상담 {time_text} 받은 거",
            "{time_text} 상담한 {product} 목록", "{product} 상담 내역 {time_text} 기준", "{time_text} 본 {product} 상담",
            "최근 {product} 상담 {time_text}에 한 거"
        ],
        "entities": {"product": ["예금", "적금", "펀드", "대출"], "time": TIME_FILTERS_LIST}
    },
    # --- 의도 4: 시간 + 상태 복합 조회 ---
    {
        "intent_id": "COMPOSITE_TIME_STATUS",
        "query_template": "SELECT * FROM consultations WHERE customer_id = :current_user_id AND {time_sql} AND status = '{status_sql}' ORDER BY start_time DESC;",
        "utterance_templates": [
            "{time_text} {status_text} 상담 내역", "{time_text}에 {status_text} 처리된 상담", "상담 건 중에 {time_text}에 {status_text} 된거",
            "{status_text} 상담 {time_text} 기준", "상태가 {status_text}이고 {time_text}에 한거", "{time_text} 상담 중 {status_text} 건만"
        ],
        "entities": {"time": TIME_FILTERS_LIST, "status": [s for s in STATUS_LIST if s[1] != "!='completed'"]}
    },
    # --- 의도 5: 집계 (상품별 카운트) ---
    {
        "intent_id": "AGG_COUNT_BY_TYPE",
        "query_template": "SELECT product_type, COUNT(*) as count FROM consultations WHERE customer_id = :current_user_id GROUP BY product_type ORDER BY count DESC;",
        "utterance_templates": [
            "상품별 상담 횟수 알려줘", "내가 무슨 상담 제일 많이 받았어?", "상품 유형별로 상담 건수 집계해줘", "가장 많이 받은 상품 유형",
            "상담 횟수 통계", "상품별 상담 통계 보여줘", "상품별로 몇 번이나 상담했는지", "상담 유형별 통계",
            "내가 받은 상담 종류별 횟수", "무슨 상담을 제일 많이 받았어?", "상담 횟수 요약", "상품 카테고리별 상담 건수"
        ],
        "entities": {}
    },
    # --- 의도 6: 집계 (전체 카운트) ---
    {
        "intent_id": "AGG_TOTAL_COUNT",
        "query_template": "SELECT COUNT(*) as total FROM consultations WHERE customer_id = :current_user_id;",
        "utterance_templates": [
            "내가 받은 총 상담 횟수", "총 몇 번 상담했지?", "전체 상담 건수", "지금까지 상담 몇 번 받았어?",
            "지금까지 상담 총 몇건?", "내 전체 상담 이력 갯수", "총 상담 건수", "상담받은거 전부 몇개야?"
        ],
        "entities": {}
    },
    # --- 의도 7: JOIN (이해도 낮은 섹션) ---
    {
        "intent_id": "JOIN_LOW_COMPREHENSION_SECTIONS",
        "query_template": "SELECT r.section_name, r.comprehension_level, c.product_details->>'name' as product_name FROM reading_analysis r JOIN consultations c ON r.consultation_id = c.id WHERE r.customer_id = :current_user_id AND r.comprehension_level IN ('low', 'medium') ORDER BY r.analysis_timestamp DESC;",
        "utterance_templates": [
            "내가 헷갈려했던 부분들 보여줘", "상담받을 때 이해 못 했던 항목이 뭐야?", "이해도가 낮았던 약관 섹션들", "어려웠던 항목 다시 보기",
            "이해도 '하' 또는 '중' 받은 섹션 목록", "내가 잘 이해 못 한 섹션", "약관 읽을 때 혼동했던 부분", "어려웠던 항목들 리스트",
            "이해도 낮게 나온 항목", "이해 수준 '중' 이하 항목 조회", "복잡했던 약관 내용 다시보기", "지난 상담에서 헷갈린 부분",
            "내용이 어려웠던 섹션 목록", "집중 못했던 항목", "혼동 확률 높았던 섹션"
        ],
        "entities": {}
    },
    # --- 의도 8: JOIN (난이도 높은 요약본) ---
    {
        "intent_id": "JOIN_DIFFICULT_SUMMARIES",
        "query_template": "SELECT s.*, c.product_details->>'name' as product_name FROM consultation_summaries s JOIN consultations c ON s.consultation_id = c.id WHERE c.customer_id = :current_user_id AND (s.comprehension_low > 0 OR s.overall_difficulty > 0.7) ORDER BY c.start_time DESC;",
        "utterance_templates": [
            "이해도가 낮았던 상담 리포트", "어려웠던 상담 요약본만 모아줘", "전체적으로 난이도 높았던 상담 리스트", "내가 잘 이해 못한 상담 건들",
            "상담 요약 중에 어려웠던 거", "상담 요약 리포트 중에 어려웠던 것", "전체 난이도 높았던 상담", "상담 리포트 난이도 '상'인거",
            "이해 못한 내용 포함된 상담 요약본", "가장 복잡했던 상담 리포트", "이해도 낮은 상담 요약", "난이도 0.7 넘는 상담 요약본",
            "이해도 '하'가 1개라도 있는 상담 리포트"
        ],
        "entities": {}
    },
    # --- 의도 9: JOIN (모든 요약본) ---
    {
        "intent_id": "JOIN_ALL_SUMMARIES",
        "query_template": "SELECT s.*, c.product_type, c.product_details->>'name' as product_name FROM consultation_summaries s JOIN consultations c ON s.consultation_id = c.id WHERE c.customer_id = :current_user_id ORDER BY c.start_time DESC;",
        "utterance_templates": [
            "내 전체 상담 요약 리포트", "모든 상담 요약본 보여줘", "상담 리포트 목록",
            "지난 상담 요약 리포트 전부 조회", "상담 리포트 전체 목록", "요약본 리스트"
        ],
        "entities": {}
    },
    # --- 의도 10: JOIN (상품별 요약본) ---
    {
        "intent_id": "JOIN_SUMMARY_BY_PRODUCT",
        "query_template": "SELECT s.* FROM consultation_summaries s JOIN consultations c ON s.consultation_id = c.id WHERE c.customer_id = :current_user_id AND c.product_type = '{product}' ORDER BY c.start_time DESC;",
        "utterance_templates": [
            "{product} 상담 요약 리포트 보여줘", "내 {product} 상담 요약본", "{product} 상담 리포트 목록",
            "지난번 {product} 상담한거 요약본 조회", "{product} 관련 요약 리포트", "{product} 요약본만"
        ],
        "entities": {"product": PRODUCTS_LIST}
    },
    # --- 의도 11: JOIN (객관적 난이도 높은 섹션) ---
    {
        "intent_id": "JOIN_ANALYSIS_HIGH_DIFFICULTY_SCORE",
        "query_template": "SELECT r.section_name, r.difficulty_score, c.product_details->>'name' as product_name FROM reading_analysis r JOIN consultations c ON r.consultation_id = c.id WHERE r.customer_id = :current_user_id AND r.difficulty_score >= 0.8 ORDER BY r.difficulty_score DESC;",
        "utterance_templates": [
            "약관 중에 제일 어려웠던 섹션", "난이도 점수 높은 항목", "가장 복잡했던 약관 항목 Top 5", "난이도 0.8 넘는 항목들",
            "객관적으로 어려웠던 섹션 목록", "어려운 약관 부분", "제일 복잡했던 섹션명", "난이도 점수 0.8 이상인거"
        ],
        "entities": {}
    },
    # --- 의도 12: JSONB (특정 상품명) ---
    {
        "intent_id": "JSONB_SPECIFIC_PRODUCT_NAME",
        "query_template": "SELECT * FROM consultations WHERE customer_id = :current_user_id AND product_details->>'name' = '{product_name}' ORDER BY start_time DESC;",
        "utterance_templates": [
            "{product_name} 상담 내역", "{product_name} 상담 받은 거 보여줘", "내가 가입한 {product_name} 상담 기록",
            "{product_name} 언제 상담받았지?", "내가 {product_name} 상담받은 이력", "{product_name} 상품 상담했던거 찾아줘",
            "{product_name} 기록", "상담한 {product_name} 상세내역"
        ],
        "entities": {"product_name": PRODUCT_NAMES_MAP["적금"] + PRODUCT_NAMES_MAP["예금"] + PRODUCT_NAMES_MAP["펀드"]}
    },
    # --- 의도 13: JSONB (금액 기반) ---
    {
        "intent_id": "JSONB_AMOUNT_QUERY",
        "query_template": "SELECT * FROM consultations WHERE customer_id = :current_user_id AND CAST(NULLIF(REGEXP_REPLACE(product_details->>'amount', '[^0-9]', '', 'g'), '') AS BIGINT) >= {amount_sql} ORDER BY start_time DESC;",
        "utterance_templates": [
            "가입금액 {amount_text} 이상인 상담", "{amount_text} 넘는 상담 내역", "금액 큰 상담 {amount_text} 이상",
            "상담한 것 중에 {amount_text} 넘는거", "상담금액 {amount_text} 이상인거 목록", "내가 {amount_text} 이상 넣은 상품 상담"
        ],
        "entities": {"amount": AMOUNTS_LIST}
    },
    # --- 의도 14: JSONB (금리 기반) ---
    {
        "intent_id": "JSONB_RATE_QUERY",
        "query_template": "SELECT * FROM consultations WHERE customer_id = :current_user_id AND CAST(NULLIF(REGEXP_REPLACE(product_details->>'interestRate', '[^0-9\\.]', '', 'g'), '') AS DECIMAL) >= {rate_sql} ORDER BY start_time DESC;",
        "utterance_templates": [
            "금리 {rate_text} 이상 상품 상담한거", "이율 {rate_text} 넘는 상담 내역", "수익률 {rate_text} 이상인거 뭐있었지",
            "{rate_text} 초과 상품 상담 기록", "제시받은 금리 {rate_text} 이상인 것", "연이율 {rate_text} 이상 상담"
        ],
        "entities": {"rate": RATES_LIST}
    }
]


def generate_label_file(db_id):
    """
    (V4.1) 확장된 INTENT_BASED_QUERIES를 기반으로
    정교하고 다양한 자연어-쿼리 쌍을 생성하여 AI Hub 라벨 파일 형식으로 저장합니다.
    """
    print("[2/2] (V4.1) '정교한' 라벨 파일 생성 시작...")

    final_data_list = []
    item_counter = 1

    # 정의된 인텐트 셋을 순회
    for intent_block in INTENT_BASED_QUERIES:
        intent_id = intent_block["intent_id"]
        query_template = intent_block["query_template"]
        utterance_templates = intent_block["utterance_templates"]
        entities = intent_block.get("entities", {})

        if not entities:
            # 엔티티가 없는 경우 (예: 집계 쿼리)
            for utterance in utterance_templates:
                item_data = {
                    "db_id": db_id, "utterance_id": f"NH_Q_{item_counter}",
                    "hardness": "hard",
                    "utterance_type": intent_id,
                    "query": query_template,
                    "utterance": utterance,
                    "values": [], "cols": []  # 훈련 코드에서 이 키를 사용하지 않으므로 빈 리스트로 둠
                }
                final_data_list.append(item_data)
                item_counter += 1
        else:
            # 엔티티 조합이 필요한 경우
            keys = list(entities.keys())

            if len(keys) == 1:
                key1 = keys[0]
                for entity1_val in entities[key1]:
                    val_text = entity1_val[0] if isinstance(entity1_val, tuple) else entity1_val
                    val_sql = entity1_val[1] if isinstance(entity1_val, tuple) else entity1_val

                    format_dict = {key1: val_text, f"{key1}_text": val_text, f"{key1}_sql": val_sql}

                    for utterance_tmpl in utterance_templates:
                        sql = query_template.format(**format_dict)
                        utt = utterance_tmpl.format(**format_dict)

                        final_data_list.append({
                            "db_id": db_id, "utterance_id": f"NH_Q_{item_counter}",
                            "hardness": "medium", "utterance_type": intent_id,
                            "query": sql, "utterance": utt, "values": [], "cols": []
                        })
                        item_counter += 1

            elif len(keys) == 2:
                key1, key2 = keys[0], keys[1]
                for entity1_val in entities[key1]:
                    for entity2_val in entities[key2]:
                        val1_text = entity1_val[0] if isinstance(entity1_val, tuple) else entity1_val
                        val1_sql = entity1_val[1] if isinstance(entity1_val, tuple) else entity1_val
                        val2_text = entity2_val[0] if isinstance(entity2_val, tuple) else entity2_val
                        val2_sql = entity2_val[1] if isinstance(entity2_val, tuple) else entity2_val

                        format_dict = {
                            key1: val1_text, f"{key1}_text": val1_text, f"{key1}_sql": val1_sql,
                            key2: val2_text, f"{key2}_text": val2_text, f"{key2}_sql": val2_sql,
                        }

                        for utterance_tmpl in utterance_templates:
                            sql = query_template.format(**format_dict)
                            utt = utterance_tmpl.format(**format_dict)

                            final_data_list.append({
                                "db_id": db_id, "utterance_id": f"NH_Q_{item_counter}",
                                "hardness": "extra_hard", "utterance_type": intent_id,
                                "query": sql, "utterance": utt, "values": [], "cols": []
                            })
                            item_counter += 1

    print(f"  ... 총 {len(final_data_list)}개의 '정교한' (발화, 쿼리) 쌍 생성 완료. (현재 약 780개)")

    # 최종 JSON 구조 생성
    final_json_output = {
        "Dataset": {
            "identifier": "NH_MVP_2025_LABEL_V4_1",
            "name": "NH 상담 내역 Text-to-SQL 라벨 (정교화/확장형)",
            "category": 9,
            "type": 0
        },
        "data": final_data_list
    }

    file_name = "TEXT_NL2SQL_label_nh_consultation.json"
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(final_json_output, f, ensure_ascii=False, indent=2)

    print(f"✅ 라벨 파일 생성 완료: {file_name}")

# ----------------------------------------------------------------------
# 3. 메인 실행
# ----------------------------------------------------------------------
if __name__ == "__main__":
    generated_db_id = generate_schema_annotation_file()

    if generated_db_id:
        generate_label_file(generated_db_id)
        print("\n🎉 (V4.1) AI Hub 형식 데이터셋 2개 파일 생성이 모두 완료되었습니다.")
        print("   이 파일들을 훈련 코드의 경로에 맞게 배치하여 사용하세요.")
    else:
        print("❌ 스키마 생성에 실패하여 라벨 파일을 생성하지 못했습니다.")