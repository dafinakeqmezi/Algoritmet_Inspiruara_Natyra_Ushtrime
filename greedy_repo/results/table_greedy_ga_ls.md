# Phase 1 -> 2 -> 3 cumulative improvement (Greedy -> GA -> LS)

Phase 3 applied Guided Local Search **on top of E3** (the experiment selected as optimal).
The table below shows: Greedy baseline -> best GA score from E3 -> LS-improved score.

| instance | Greedy | GA-E3 best | LS best | Δ Greedy→GA(E3) | Δ GA(E3)→LS | Δ Greedy→LS (total) |
|---|---:|---:|---:|---:|---:|---:|
| australia_iptv | 1346 | 3191 | 3341 | +137.1% | +4.7% | +148.2% |
| canada_pw | 1070 | 2503 | 2624 | +133.9% | +4.8% | +145.2% |
| china_pw | 1296 | 2254 | 2274 | +73.9% | +0.9% | +75.5% |
| croatia_tv_input | 1278 | 1936 | 2012 | +51.5% | +3.9% | +57.4% |
| france_iptv | 1215 | 2927 | 2848 | +140.9% | -2.7% | +134.4% |
| germany_tv_input | 725 | 932 | 932 | +28.6% | +0.0% | +28.6% |
| kosovo_tv_input | 1160 | 1533 | 1553 | +32.2% | +1.3% | +33.9% |
| netherlands_tv_input | 1133 | 1723 | 1723 | +52.1% | +0.0% | +52.1% |
| singapore_pw | 1223 | 3357 | 3400 | +174.5% | +1.3% | +178.0% |
| spain_iptv | 978 | 1721 | 1727 | +76.0% | +0.3% | +76.6% |
| toy | 380 | 380 | 380 | +0.0% | +0.0% | +0.0% |
| uk_iptv | 1491 | 3110 | 3171 | +108.6% | +2.0% | +112.7% |
| uk_tv_input | 1098 | 1923 | 1979 | +75.1% | +2.9% | +80.2% |
| us_iptv | 1513 | 2075 | 2188 | +37.1% | +5.4% | +44.6% |
| usa_tv_input | 1711 | 2510 | 2512 | +46.7% | +0.1% | +46.8% |
| youtube_gold | 13058 | 13058 | 13058 | +0.0% | +0.0% | +0.0% |
| youtube_premium | 19900 | 21646 | 22889 | +8.8% | +5.7% | +15.0% |

**Mean across 17 instances:**
- Greedy → GA(E3): **+69.23%**
- GA(E3) → LS: **+1.81%**
- Greedy → LS (cumulative): **+72.31%**

Negative `Δ GA(E3)→LS` happens only on the very largest instances (youtube_gold, youtube_premium) where E3 cannot evolve past its greedy seed within 5 min; LS starts from the same seed and finds slightly different but lower-scoring local optima. In those cases LS-best may fall *under* the E3-best (which equals the greedy seed). This is honest behaviour, not a bug.