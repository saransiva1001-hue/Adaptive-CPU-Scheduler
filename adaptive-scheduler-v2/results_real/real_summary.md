# Real-trace results

15 slices x 200 jobs per log, arrivals rescaled to load 0.9. Controller check interval = 0.5 x mean burst. No tuning on these logs.


## 1791528284035_SDSC-Par-1995-3_1-cln_swf.swf

| method                     |   slices |   avg_wait |   median_avg_wait |   p95_wait |   max_wait |   rule_changes |   mean_regret_pct |   worst_slice_regret_pct |
|:---------------------------|---------:|-----------:|------------------:|-----------:|-----------:|---------------:|------------------:|-------------------------:|
| FCFS                       |       15 |    61109.7 |          31304.8  |   121330   |     129973 |           0    |            455.17 |                  2849.59 |
| SJF                        |       15 |    37966.2 |          17356.4  |   103643   |     181837 |           0    |            229.26 |                  1013.23 |
| RR4                        |       15 |    18515.2 |          13933.5  |   132299   |     248286 |           0    |             19.5  |                   146.67 |
| Rule router (old design)   |       15 |    42023.3 |          18364.4  |   105687   |     145250 |          10.67 |            244.7  |                  1013.58 |
| Shadow (adaptive)          |       15 |    32279.5 |          15936    |   104949   |     198074 |           9.4  |             61.39 |                   438.38 |
| SJF* (cheats: true bursts) |       15 |    13353.1 |           9603.26 |    41697.9 |     148144 |           0    |             61.68 |                   968.56 |


Paired comparison on avg wait (diff = Shadow - baseline, negative = Shadow better; 95% bootstrap CI over slices):

| shadow_vs                |   mean_diff | ci                   | shadow_wins   | verdict             |
|:-------------------------|------------:|:---------------------|:--------------|:--------------------|
| FCFS                     |    -28830.2 | [-45061.5, -15915.6] | 100%          | shadow better       |
| SJF                      |     -5686.7 | [-10463.8, -1098.4]  | 80%           | shadow better       |
| RR4                      |     13764.4 | [-1839.3, 34836.2]   | 60%           | no clear difference |
| Rule router (old design) |     -9743.8 | [-17639.7, -3249.1]  | 87%           | shadow better       |


## SDSC-SP2-1998-4_swf.swf

| method                     |   slices |   avg_wait |   median_avg_wait |   p95_wait |   max_wait |   rule_changes |   mean_regret_pct |   worst_slice_regret_pct |
|:---------------------------|---------:|-----------:|------------------:|-----------:|-----------:|---------------:|------------------:|-------------------------:|
| FCFS                       |       15 |    4939.63 |           2078.18 |    9781.33 |    10887.5 |           0    |            110.63 |                   248.16 |
| SJF                        |       15 |    2200.22 |           1212.7  |    8832.8  |    17236.7 |           0    |              7.29 |                    40.84 |
| RR4                        |       15 |    2414.18 |           1607.46 |   13583.1  |    28144   |           0    |             42.92 |                   240.42 |
| Rule router (old design)   |       15 |    2499.18 |           1282.6  |    9103.13 |    13085.7 |          18.73 |             19.5  |                    50.78 |
| Shadow (adaptive)          |       15 |    2172.57 |           1207.76 |    9873.93 |    18790.1 |          17.2  |             13.29 |                    66.51 |
| SJF* (cheats: true bursts) |       15 |    1006.53 |            549.4  |    3092.33 |    17692.3 |           0    |            -49.56 |                   -24.25 |


Paired comparison on avg wait (diff = Shadow - baseline, negative = Shadow better; 95% bootstrap CI over slices):

| shadow_vs                |   mean_diff | ci                | shadow_wins   | verdict             |
|:-------------------------|------------:|:------------------|:--------------|:--------------------|
| FCFS                     |     -2767.1 | [-5773.6, -924.6] | 100%          | shadow better       |
| SJF                      |       -27.7 | [-227.8, 174.8]   | 47%           | no clear difference |
| RR4                      |      -241.6 | [-585.7, 85.1]    | 73%           | no clear difference |
| Rule router (old design) |      -326.6 | [-780.7, -4.8]    | 60%           | shadow better       |
