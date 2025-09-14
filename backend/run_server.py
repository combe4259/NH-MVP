#!/usr/bin/env python3
"""
서버 직접 실행 스크립트
"""

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['AI_MODEL_TYPE'] = 'huggingface'

print("서버 시작 중...")

if __name__ == "__main__":
    import uvicorn
    from main import app
    
    print("Uvicorn으로 서버 실행...")
    uvicorn.run(
        app, 
        host="127.0.0.1", 
        port=8000,
        log_level="info"
    )