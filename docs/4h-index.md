---
layout: default
title: 4시간봉 분석
nav_order: 12
has_children: true
permalink: /4h/
---

# 4시간봉 분석
{: .no_toc }

4시간봉 타임프레임에서의 ㄴ자 패턴 롱 전략 분석 결과입니다.

---

## 요약

| 항목 | 4시간봉 | 1시간봉 | 비교 |
|:-----|------:|-------:|:----:|
| 총 수익률 | **166.6%** | 112.5% | +48% |
| 최대 낙폭 | 82% | 26% | +215% |
| 승률 | 49.2% | 69.7% | -29% |
| 수익/MDD | 2.03 | 4.33 | -53% |
| ML AUC | 0.56 | 0.62 | -10% |
| 거래 수 | 124 | 165 | -25% |

{: .warning }
> **4시간봉은 반익절 없이는 MDD가 매우 높습니다.**
> 반익절 적용이 필수적입니다.

---

## 최적 설정

### 반익절 없음 (공격적 - 비권장)

```python
config = LongStrategyConfig(
    breakout_ma=25,
    take_profit_pct=10.0,
    stop_loss_pct=7.0,
    consolidation_bars=3,
    consolidation_range_pct=7.0,
    drop_threshold_pct=5.0,
    half_close_enabled=False,
)
# 예상: 167% 수익, 82% MDD, 49% 승률
```

### 반익절 있음 (권장)

```python
config = LongStrategyConfig(
    breakout_ma=25,
    take_profit_pct=10.0,
    stop_loss_pct=7.0,
    consolidation_bars=3,
    consolidation_range_pct=7.0,
    drop_threshold_pct=5.0,
    half_close_enabled=True,
    half_close_pct=2.0,
)
# 예상: 104% 수익, 48% MDD, 81% 승률
```

---

## 세부 문서

- [파라메트릭 스터디]({{ '/parametric-4h' | relative_url }}) - 729개 파라미터 조합 분석
- [ML/DL 분석]({{ '/ml-analysis-4h' | relative_url }}) - SL/TP 예측 모델 성능
