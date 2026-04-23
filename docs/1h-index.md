---
layout: default
title: 1시간봉 분석
nav_order: 2
has_children: true
permalink: /1h/
---

# 1시간봉 분석

{: .highlight }
> **권장 타임프레임** - 리스크 대비 수익률이 가장 우수합니다.

## 핵심 지표

| 지표 | 값 |
|:-----|---:|
| 총 수익률 | **112.5%** |
| 최대 낙폭 | **26%** |
| 승률 | **69.7%** |
| 수익/MDD | **4.33** |
| ML AUC | **0.62** |

## 최적 설정

```python
config = LongStrategyConfig(
    breakout_ma=100,
    take_profit_pct=10.0,
    stop_loss_pct=5.0,
    half_close_enabled=True,
    half_close_pct=3.0,
)
```

## 하위 문서

- [백테스트 결과](/btc-lshape-long/results-1h/) - 최적 설정 성과, 연도별 분석
- [파라메트릭 스터디](/btc-lshape-long/parametric-1h/) - 960개 파라미터 조합 탐색
- [ML/DL 분석](/btc-lshape-long/ml-analysis-1h/) - SL/TP 예측 모델 성능
