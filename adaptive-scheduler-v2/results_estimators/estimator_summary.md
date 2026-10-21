# Estimator study: SDSC-SP2-1998-4.swf.gz

30 slices x 200 jobs, arrivals rescaled to load 0.9. Controller check interval = 0.5 x mean burst. Nothing tuned on this log.

## Scheduling results (average waiting time in ticks, lower is better)

| method                     |   slices |   avg_wait |   median_avg_wait |   p95_wait |   max_wait |   rule_changes |
|:---------------------------|---------:|-----------:|------------------:|-----------:|-----------:|---------------:|
| FCFS                       |       30 |     4233.8 |            1901.4 |     8676.4 |     9849.1 |            0   |
| RR4                        |       30 |     2228.7 |            1430.2 |    13090.9 |    25272.1 |            0   |
| SJF [history]              |       30 |     2173   |            1087.6 |     8671.2 |    17226.8 |            0   |
| SJF [requested]            |       30 |     1386.1 |             679.2 |     6389.4 |    13402.8 |            0   |
| SJF [corrected]            |       30 |     1302.2 |             590.4 |     5808.1 |    15459.5 |            0   |
| Rule router [history]      |       30 |     2397.9 |            1220.7 |     8953.6 |    13774.3 |           19.6 |
| Shadow [history]           |       30 |     1986.6 |            1074.6 |     9065.7 |    16265.6 |           16.6 |
| Shadow [requested]         |       30 |     1400.2 |             753.9 |     7522.2 |    17180.2 |           12.8 |
| Shadow [corrected]         |       30 |     1491.9 |             842.3 |     7499.5 |    17958.9 |           14.1 |
| SJF* (cheats: true bursts) |       30 |      915.5 |             519.7 |     2997.4 |    15258.9 |            0   |

## How good are the guesses?

median_abs_rel_error: typical |guess - truth| / truth (0 = perfect). spearman_rank_corr: how well the guesses ORDER the jobs (1 = perfect; SJF only needs the order). median_over_under: median guess/truth (1 = unbiased, >1 = overestimates).

| estimator   |   median_abs_rel_error |   spearman_rank_corr |   median_over_under |
|:------------|-----------------------:|---------------------:|--------------------:|
| history     |                   0.8  |                 0.48 |                1.14 |
| requested   |                   6.62 |                 0.57 |                7.62 |
| corrected   |                   0.71 |                 0.62 |                1.41 |

## Paired comparisons on avg wait (negative diff = A better; 95% bootstrap CI over slices)

| A                  | B                |   mean_diff_A_minus_B | ci95              | A_wins   | verdict             |
|:-------------------|:-----------------|----------------------:|:------------------|:---------|:--------------------|
| SJF [requested]    | SJF [history]    |                -786.9 | [-1234.8, -408.1] | 90%      | A better            |
| SJF [corrected]    | SJF [history]    |                -870.9 | [-1343.0, -455.9] | 97%      | A better            |
| Shadow [requested] | Shadow [history] |                -586.5 | [-817.4, -364.9]  | 90%      | A better            |
| Shadow [corrected] | Shadow [history] |                -494.8 | [-713.4, -297.7]  | 97%      | A better            |
| Shadow [requested] | SJF [requested]  |                  14.1 | [-91.4, 105.8]    | 33%      | no clear difference |
| Shadow [corrected] | SJF [corrected]  |                 189.7 | [39.4, 338.3]     | 17%      | A worse             |
| Shadow [requested] | RR4              |                -828.5 | [-1101.8, -585.9] | 100%     | A better            |
| Shadow [corrected] | RR4              |                -736.8 | [-1025.4, -481.7] | 97%      | A better            |
| SJF [corrected]    | RR4              |                -926.5 | [-1186.7, -685.9] | 100%     | A better            |
| SJF [requested]    | RR4              |                -842.6 | [-1099.9, -609.2] | 100%     | A better            |