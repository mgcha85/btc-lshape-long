---
layout: default
title: 15분봉 분석
nav_order: 9
has_children: true
permalink: /15m/
---

# 15분봉 분석
{: .no_toc }

15분봉 타임프레임에서의 ㄴ자 패턴 롱 전략 분석 결과입니다.

---

## 요약

| 항목 | 15분봉 | 1시간봉 | 비교 |
|:-----|------:|-------:|:----:|
| 총 수익률 | **159.7%** | 112.5% | +42% |
| 최대 낙폭 | 35% | 26% | +35% |
| 승률 | 37.3% | 69.7% | -46% |
| 수익/MDD | **4.56** | 4.33 | +5% |
| ML AUC | 0.53 | 0.62 | -15% |
| 거래 수 | 968 | 165 | +487% |

{: .highlight }
> **15분봉은 반익절(HC 3%) 적용 시 수익/MDD 비율이 1시간봉과 유사**합니다.
> 그러나 ML 예측력은 낮아 필터 적용이 어렵습니다.

---

## 최적 설정

### 반익절 없음 (공격적)

```python
config = LongStrategyConfig(
    breakout_ma=25,
    take_profit_pct=7.0,
    stop_loss_pct=1.5,
    consolidation_bars=4,
    consolidation_range_pct=2.0,
    drop_threshold_pct=2.0,
    half_close_enabled=False,
)
# 예상: 206% 수익, 80% MDD, 21% 승률
```

### 반익절 있음 (권장)

```python
config = LongStrategyConfig(
    breakout_ma=25,
    take_profit_pct=7.0,
    stop_loss_pct=1.5,
    consolidation_bars=4,
    consolidation_range_pct=2.0,
    drop_threshold_pct=2.0,
    half_close_enabled=True,
    half_close_pct=3.0,
)
# 예상: 160% 수익, 35% MDD, 37% 승률
```

---

## 세부 문서

- [파라메트릭 스터디]({{ '/parametric-15m' | relative_url }}) - 729개 파라미터 조합 분석
- [ML/DL 분석]({{ '/ml-analysis-15m' | relative_url }}) - SL/TP 예측 모델 성능
