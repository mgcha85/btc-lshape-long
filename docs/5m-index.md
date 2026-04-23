---
layout: default
title: 5분봉 분석
nav_order: 5
has_children: true
permalink: /5m/
---

# 5분봉 분석

{: .warning }
> **참고용 타임프레임** - 노이즈가 많아 1시간봉 대비 효율이 낮습니다.

## 핵심 지표

| 지표 | 값 |
|:-----|---:|
| 총 수익률 | 50.0% |
| 최대 낙폭 | 24.5% |
| 승률 | 45.2% |
| 수익/MDD | 2.04 |
| ML AUC | 0.55 |

## 최적 설정

```python
config = LongStrategyConfig(
    breakout_ma=48,
    take_profit_pct=2.0,
    stop_loss_pct=1.5,
    consolidation_bars=6,
    consolidation_range_pct=3.0,
    half_close_enabled=False,
)
```

## 1시간봉 대비 비교

| 항목 | 1시간봉 | 5분봉 |
|:-----|-------:|------:|
| 수익/MDD | **4.33** | 2.04 |
| ML AUC | **0.62** | 0.55 |
| 승률 | **69.7%** | 45.2% |

## 하위 문서

- [백테스트 결과](/btc-lshape-long/results-5m/) - 5분봉 최적 설정 성과
- [파라메트릭 스터디](/btc-lshape-long/parametric-5m/) - 729개 파라미터 조합 탐색
- [ML/DL 분석](/btc-lshape-long/ml-analysis-5m/) - 5분봉 예측 모델 한계
