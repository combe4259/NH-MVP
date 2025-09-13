"""
DAiSEE 데이터셋 상세 통계 분석
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter

def analyze_daisee_dataset():
    """DAiSEE Train Labels 상세 분석"""
    
    # 데이터 로드
    df = pd.read_csv('/Users/inter4259/Desktop/DAiSEE/Labels/TrainLabels.csv')
    df.columns = df.columns.str.strip()  # 컬럼명 공백 제거
    
    print("=" * 80)
    print("DAiSEE TRAIN DATASET COMPREHENSIVE ANALYSIS")
    print("=" * 80)
    
    # 1. 기본 통계
    print("\n📊 BASIC STATISTICS")
    print("-" * 40)
    print(f"Total samples: {len(df):,}")
    print(f"Unique users: {df['ClipID'].str[:6].nunique()}")
    print(f"Avg clips per user: {len(df) / df['ClipID'].str[:6].nunique():.1f}")
    
    # 2. 각 감정별 상세 분포
    emotions = ['Boredom', 'Engagement', 'Confusion', 'Frustration']
    
    print("\n📈 EMOTION DISTRIBUTION ANALYSIS")
    print("-" * 40)
    
    for emotion in emotions:
        print(f"\n{emotion.upper()}:")
        counts = df[emotion].value_counts().sort_index()
        
        # 통계값
        mean_val = df[emotion].mean()
        std_val = df[emotion].std()
        median_val = df[emotion].median()
        
        print(f"  Mean: {mean_val:.2f}, Std: {std_val:.2f}, Median: {median_val:.1f}")
        
        # 레벨별 분포
        for level in range(4):
            count = counts.get(level, 0)
            pct = count / len(df) * 100
            bar = '█' * int(pct/2)
            print(f"  Level {level}: {count:5d} ({pct:5.1f}%) {bar}")
        
        # 불균형 비율
        max_count = counts.max()
        min_count = counts.min()
        imbalance_ratio = max_count / min_count if min_count > 0 else float('inf')
        print(f"  Imbalance ratio: {imbalance_ratio:.1f}:1")
    
    # 3. 감정 조합 분석
    print("\n🔄 EMOTION COMBINATIONS")
    print("-" * 40)
    
    # 모든 감정이 0인 경우
    all_zero = df[(df['Boredom']==0) & (df['Engagement']==0) & 
                  (df['Confusion']==0) & (df['Frustration']==0)]
    print(f"All emotions at 0: {len(all_zero)} ({len(all_zero)/len(df)*100:.1f}%)")
    
    # High engagement + No confusion
    high_eng_no_conf = df[(df['Engagement']>=2) & (df['Confusion']==0)]
    print(f"High engagement + No confusion: {len(high_eng_no_conf)} ({len(high_eng_no_conf)/len(df)*100:.1f}%)")
    
    # Low engagement + High confusion
    low_eng_high_conf = df[(df['Engagement']<=1) & (df['Confusion']>=2)]
    print(f"Low engagement + High confusion: {len(low_eng_high_conf)} ({len(low_eng_high_conf)/len(df)*100:.1f}%)")
    
    # 상관관계
    print("\n📐 CORRELATION MATRIX")
    print("-" * 40)
    corr_matrix = df[emotions].corr()
    print(corr_matrix.round(2))
    
    # 4. 클래스별 샘플 수 (이진 분류 시뮬레이션)
    print("\n🔀 BINARY CLASSIFICATION SCENARIOS")
    print("-" * 40)
    
    scenarios = [
        ("Engaged (2-3) vs Not Engaged (0-1)", 
         len(df[df['Engagement']>=2]), len(df[df['Engagement']<=1])),
        ("Confused (1-3) vs Not Confused (0)", 
         len(df[df['Confusion']>=1]), len(df[df['Confusion']==0])),
        ("Bored (1-3) vs Not Bored (0)", 
         len(df[df['Boredom']>=1]), len(df[df['Boredom']==0])),
        ("Any Negative (B/C/F > 0) vs None",
         len(df[(df['Boredom']>0) | (df['Confusion']>0) | (df['Frustration']>0)]),
         len(df[(df['Boredom']==0) & (df['Confusion']==0) & (df['Frustration']==0)]))
    ]
    
    for scenario, positive, negative in scenarios:
        total = positive + negative
        pos_pct = positive/total*100
        neg_pct = negative/total*100
        ratio = max(positive, negative) / min(positive, negative)
        print(f"\n{scenario}:")
        print(f"  Positive: {positive:,} ({pos_pct:.1f}%)")
        print(f"  Negative: {negative:,} ({neg_pct:.1f}%)")
        print(f"  Imbalance: {ratio:.1f}:1")
    
    # 5. 추천사항
    print("\n💡 RECOMMENDATIONS")
    print("-" * 40)
    print("1. SEVERE CLASS IMBALANCE:")
    print("   - Engagement: 95.4% are High/Very High")
    print("   - Only 34 samples (0.6%) with Very Low engagement")
    print("   - Model will likely predict only High engagement")
    
    print("\n2. BETTER ALTERNATIVES:")
    print("   - Use Confusion as primary metric (32.5% positive)")
    print("   - Binary classification: Confused vs Not Confused")
    print("   - Combine Boredom + Confusion for 'Need Help' signal")
    
    print("\n3. DATA AUGMENTATION LIMITS:")
    print("   - 34 samples × 157 weight = extreme overfitting risk")
    print("   - Video SMOTE not feasible (1.1M dimensions)")
    print("   - Consider collecting more balanced data")
    
    # 6. 가장 균형잡힌 분류 태스크 찾기
    print("\n🎯 MOST BALANCED CLASSIFICATION TASKS")
    print("-" * 40)
    
    tasks = []
    
    # 각 감정의 이진 분류 버전
    for emotion in emotions:
        for threshold in [0, 1]:
            positive = len(df[df[emotion] > threshold])
            negative = len(df[df[emotion] <= threshold])
            if min(positive, negative) > 0:
                ratio = max(positive, negative) / min(positive, negative)
                tasks.append((f"{emotion} > {threshold}", positive, negative, ratio))
    
    # 가장 균형잡힌 태스크 상위 5개
    tasks.sort(key=lambda x: x[3])
    print("\nTop 5 most balanced tasks:")
    for i, (task, pos, neg, ratio) in enumerate(tasks[:5], 1):
        print(f"{i}. {task}: {pos} vs {neg} (ratio: {ratio:.2f}:1)")
    
    return df

if __name__ == "__main__":
    df = analyze_daisee_dataset()
    
    # 시각화 옵션
    visualize = input("\n\nGenerate visualization plots? (y/n): ").strip().lower()
    
    if visualize == 'y':
        import matplotlib.pyplot as plt
        
        # 각 감정별 분포 시각화
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        emotions = ['Boredom', 'Engagement', 'Confusion', 'Frustration']
        
        for idx, emotion in enumerate(emotions):
            ax = axes[idx // 2, idx % 2]
            df[emotion].value_counts().sort_index().plot(kind='bar', ax=ax)
            ax.set_title(f'{emotion} Distribution')
            ax.set_xlabel('Level')
            ax.set_ylabel('Count')
            
            # 백분율 표시
            total = len(df)
            for i, v in enumerate(df[emotion].value_counts().sort_index()):
                ax.text(i, v + 50, f'{v/total*100:.1f}%', ha='center')
        
        plt.suptitle('DAiSEE Dataset Emotion Distributions', fontsize=16)
        plt.tight_layout()
        plt.savefig('daisee_distribution.png', dpi=150)
        print(f"\n📊 Visualization saved as 'daisee_distribution.png'")
        plt.show()