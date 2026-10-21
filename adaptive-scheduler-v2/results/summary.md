# Results

100 random seeds per workload. Context switch = 1 tick, rule-change penalty = 1 tick.

Regret = % worse than the best single fixed rule chosen in hindsight (negative = better than any single fixed rule).


## interactive

| method                     |   avg_wait |   p95_wait |   max_wait |   ctx |   rule_changes |   regret_pct |
|:---------------------------|-----------:|-----------:|-----------:|------:|---------------:|-------------:|
| FCFS                       |      16.53 |      34.33 |      38.12 | 59.87 |           0    |        14.96 |
| SJF                        |      14.24 |      70.91 |     122.33 | 59.87 |           0    |         0.25 |
| RR4                        |      24.64 |      60.29 |      70.16 | 76    |           0    |        72.54 |
| SJF* (cheats: true bursts) |      12.53 |      59.28 |     110.19 | 59.87 |           0    |        -9.88 |
| Rule router (old design)   |      14.24 |      70.91 |     122.33 | 59.87 |           0    |         0.25 |
| Shadow (A)                 |      14.27 |      70.95 |     122.4  | 59.87 |           0.14 |         0.59 |
| Shadow+Guard (A+B)         |      14.89 |      69.03 |     117.44 | 59.87 |           1.6  |         5.49 |


## batch

| method                     |   avg_wait |   p95_wait |   max_wait |    ctx |   rule_changes |   regret_pct |
|:---------------------------|-----------:|-----------:|-----------:|-------:|---------------:|-------------:|
| FCFS                       |      43.84 |     102.22 |     113.14 |  30.31 |           0    |         8.3  |
| SJF                        |      39.56 |     157.15 |     207.92 |  30.31 |           0    |         0.29 |
| RR4                        |     153.72 |     292.08 |     325.99 | 179.68 |           0    |       295.46 |
| SJF* (cheats: true bursts) |      35.79 |     157.82 |     240.11 |  30.31 |           0    |        -8.29 |
| Rule router (old design)   |      44.29 |     102.92 |     113.95 |  30.31 |           1.11 |         9.45 |
| Shadow (A)                 |      39.94 |     154.02 |     200.6  |  30.41 |           0.51 |         1.41 |
| Shadow+Guard (A+B)         |      39.94 |     154.02 |     200.6  |  30.41 |           0.51 |         1.41 |


## mixed

| method                     |   avg_wait |   p95_wait |   max_wait |    ctx |   rule_changes |   regret_pct |
|:---------------------------|-----------:|-----------:|-----------:|-------:|---------------:|-------------:|
| FCFS                       |      39.03 |      88.07 |      96.65 |  31.26 |           0    |        43.84 |
| SJF                        |      26.23 |     102.85 |     134.74 |  31.26 |           0    |         0    |
| RR4                        |      68.46 |     196.83 |     220.4  | 105.14 |           0    |       149.88 |
| SJF* (cheats: true bursts) |      22.82 |     101.29 |     160.04 |  31.26 |           0    |        -9.69 |
| Rule router (old design)   |      34.83 |      88.34 |     100.87 |  31.26 |           4.38 |        27.1  |
| Shadow (A)                 |      27.61 |     105.47 |     137.29 |  34.79 |           1.12 |         5.99 |
| Shadow+Guard (A+B)         |      29.12 |     107.16 |     136.51 |  35.09 |           2.41 |        11.47 |


## spiky

| method                     |   avg_wait |   p95_wait |   max_wait |   ctx |   rule_changes |   regret_pct |
|:---------------------------|-----------:|-----------:|-----------:|------:|---------------:|-------------:|
| FCFS                       |      60.4  |     150.78 |     163.1  | 24.32 |           0    |        77.43 |
| SJF                        |      52.18 |     157.31 |     182.05 | 24.32 |           0    |        60.35 |
| RR4                        |      34.96 |     150    |     194.71 | 79.84 |           0    |        22.06 |
| SJF* (cheats: true bursts) |      35.62 |     126.15 |     163.61 | 24.32 |           0    |        28.63 |
| Rule router (old design)   |      51.63 |     152.37 |     170.62 | 24.32 |           1.67 |        63.5  |
| Shadow (A)                 |      41.68 |     142.98 |     169.72 | 41.27 |           2.3  |        30.21 |
| Shadow+Guard (A+B)         |      42.81 |     137.26 |     162.34 | 41.68 |           3.42 |        35.23 |


## phased

| method                     |   avg_wait |   p95_wait |   max_wait |    ctx |   rule_changes |   regret_pct |
|:---------------------------|-----------:|-----------:|-----------:|-------:|---------------:|-------------:|
| FCFS                       |      32.61 |      73.99 |      89.41 |  74.26 |           0    |        42.06 |
| SJF                        |      20.78 |      94.63 |     190.59 |  74.26 |           0    |         0.11 |
| RR4                        |      63.78 |     207.23 |     277.89 | 162.37 |           0    |       193    |
| SJF* (cheats: true bursts) |      18.66 |      86.18 |     210.92 |  74.26 |           0    |        -9.16 |
| Rule router (old design)   |      24.51 |      96.16 |     161.1  |  74.26 |           2.52 |        13.25 |
| Shadow (A)                 |      21.14 |      92.9  |     189.85 |  74.38 |           0.58 |         1.73 |
| Shadow+Guard (A+B)         |      21.69 |      89.54 |     186.47 |  74.34 |           2.09 |         4.51 |


## phased_mix

| method                     |   avg_wait |   p95_wait |   max_wait |    ctx |   rule_changes |   regret_pct |
|:---------------------------|-----------:|-----------:|-----------:|-------:|---------------:|-------------:|
| FCFS                       |      66.19 |     129.99 |     147.95 |  56.68 |           0    |        44.8  |
| SJF                        |      46.69 |     155    |     250.42 |  56.68 |           0    |         9.75 |
| RR4                        |      75.77 |     223.39 |     305.31 | 168.96 |           0    |       130.08 |
| SJF* (cheats: true bursts) |      33.06 |     129.08 |     223.6  |  56.68 |           0    |       -12.19 |
| Rule router (old design)   |      56.17 |     145.91 |     183.69 |  56.68 |           4.48 |        28.65 |
| Shadow (A)                 |      45.43 |     158.59 |     245.21 |  60.34 |           1.55 |         9.22 |
| Shadow+Guard (A+B)         |      51.38 |     151.34 |     223.13 |  60.66 |           2.4  |        19.3  |


## Paired comparison (avg wait, lower is better)

diff = adaptive - baseline (negative = adaptive better). CI = 95% bootstrap.

| workload    | adaptive                 | baseline   |    diff | ci                 | win_rate   | verdict             |
|:------------|:-------------------------|:-----------|--------:|:-------------------|:-----------|:--------------------|
| interactive | Shadow (A)               | FCFS       |   -2.26 | [-2.72, -1.85]     | 97%        | better              |
| interactive | Shadow (A)               | SJF        |    0.03 | [0.01, 0.06]       | 0%         | worse               |
| interactive | Shadow (A)               | RR4        |  -10.37 | [-11.71, -9.06]    | 100%       | better              |
| interactive | Shadow+Guard (A+B)       | FCFS       |   -1.64 | [-2.04, -1.26]     | 86%        | better              |
| interactive | Shadow+Guard (A+B)       | SJF        |    0.65 | [0.46, 0.86]       | 8%         | worse               |
| interactive | Shadow+Guard (A+B)       | RR4        |   -9.75 | [-11.03, -8.49]    | 100%       | better              |
| interactive | Rule router (old design) | FCFS       |   -2.29 | [-2.74, -1.89]     | 98%        | better              |
| interactive | Rule router (old design) | SJF        |    0    | [0.00, 0.00]       | 0%         | no clear difference |
| interactive | Rule router (old design) | RR4        |  -10.41 | [-11.73, -9.09]    | 100%       | better              |
| batch       | Shadow (A)               | FCFS       |   -3.9  | [-5.12, -2.84]     | 79%        | better              |
| batch       | Shadow (A)               | SJF        |    0.38 | [0.19, 0.60]       | 0%         | worse               |
| batch       | Shadow (A)               | RR4        | -113.78 | [-127.40, -100.34] | 100%       | better              |
| batch       | Shadow+Guard (A+B)       | FCFS       |   -3.9  | [-5.12, -2.84]     | 79%        | better              |
| batch       | Shadow+Guard (A+B)       | SJF        |    0.38 | [0.19, 0.60]       | 0%         | worse               |
| batch       | Shadow+Guard (A+B)       | RR4        | -113.78 | [-127.40, -100.34] | 100%       | better              |
| batch       | Rule router (old design) | FCFS       |    0.44 | [0.36, 0.54]       | 5%         | worse               |
| batch       | Rule router (old design) | SJF        |    4.72 | [3.59, 6.03]       | 7%         | worse               |
| batch       | Rule router (old design) | RR4        | -109.44 | [-122.22, -96.90]  | 100%       | better              |
| mixed       | Shadow (A)               | FCFS       |  -11.42 | [-13.52, -9.43]    | 95%        | better              |
| mixed       | Shadow (A)               | SJF        |    1.38 | [0.91, 1.90]       | 5%         | worse               |
| mixed       | Shadow (A)               | RR4        |  -40.85 | [-47.38, -35.11]   | 100%       | better              |
| mixed       | Shadow+Guard (A+B)       | FCFS       |   -9.91 | [-11.89, -8.01]    | 94%        | better              |
| mixed       | Shadow+Guard (A+B)       | SJF        |    2.89 | [2.13, 3.77]       | 5%         | worse               |
| mixed       | Shadow+Guard (A+B)       | RR4        |  -39.34 | [-45.41, -33.77]   | 100%       | better              |
| mixed       | Rule router (old design) | FCFS       |   -4.2  | [-5.11, -3.37]     | 86%        | better              |
| mixed       | Rule router (old design) | SJF        |    8.6  | [6.97, 10.31]      | 2%         | worse               |
| mixed       | Rule router (old design) | RR4        |  -33.63 | [-38.54, -29.05]   | 100%       | better              |
| spiky       | Shadow (A)               | FCFS       |  -18.73 | [-27.67, -11.78]   | 65%        | better              |
| spiky       | Shadow (A)               | SJF        |  -10.5  | [-15.90, -5.71]    | 43%        | better              |
| spiky       | Shadow (A)               | RR4        |    6.72 | [2.78, 11.20]      | 43%        | worse               |
| spiky       | Shadow+Guard (A+B)       | FCFS       |  -17.59 | [-26.58, -10.83]   | 61%        | better              |
| spiky       | Shadow+Guard (A+B)       | SJF        |   -9.36 | [-15.04, -4.41]    | 42%        | better              |
| spiky       | Shadow+Guard (A+B)       | RR4        |    7.86 | [3.16, 13.08]      | 43%        | worse               |
| spiky       | Rule router (old design) | FCFS       |   -8.77 | [-15.22, -4.26]    | 56%        | better              |
| spiky       | Rule router (old design) | SJF        |   -0.54 | [-4.44, 1.66]      | 12%        | no clear difference |
| spiky       | Rule router (old design) | RR4        |   16.68 | [10.60, 22.94]     | 44%        | worse               |
| phased      | Shadow (A)               | FCFS       |  -11.48 | [-14.98, -8.47]    | 92%        | better              |
| phased      | Shadow (A)               | SJF        |    0.36 | [0.13, 0.62]       | 2%         | worse               |
| phased      | Shadow (A)               | RR4        |  -42.65 | [-49.51, -36.52]   | 99%        | better              |
| phased      | Shadow+Guard (A+B)       | FCFS       |  -10.92 | [-14.48, -7.92]    | 89%        | better              |
| phased      | Shadow+Guard (A+B)       | SJF        |    0.91 | [0.64, 1.23]       | 2%         | worse               |
| phased      | Shadow+Guard (A+B)       | RR4        |  -42.09 | [-48.93, -35.90]   | 99%        | better              |
| phased      | Rule router (old design) | FCFS       |   -8.1  | [-10.34, -6.09]    | 91%        | better              |
| phased      | Rule router (old design) | SJF        |    3.74 | [2.61, 5.09]       | 6%         | worse               |
| phased      | Rule router (old design) | RR4        |  -39.27 | [-45.06, -33.83]   | 100%       | better              |
| phased_mix  | Shadow (A)               | FCFS       |  -20.76 | [-28.93, -13.59]   | 85%        | better              |
| phased_mix  | Shadow (A)               | SJF        |   -1.26 | [-4.29, 1.68]      | 15%        | no clear difference |
| phased_mix  | Shadow (A)               | RR4        |  -30.34 | [-38.30, -22.93]   | 83%        | better              |
| phased_mix  | Shadow+Guard (A+B)       | FCFS       |  -14.82 | [-21.50, -9.08]    | 82%        | better              |
| phased_mix  | Shadow+Guard (A+B)       | SJF        |    4.69 | [0.29, 9.36]       | 15%        | worse               |
| phased_mix  | Shadow+Guard (A+B)       | RR4        |  -24.39 | [-33.38, -15.15]   | 82%        | better              |
| phased_mix  | Rule router (old design) | FCFS       |  -10.02 | [-15.71, -5.20]    | 59%        | better              |
| phased_mix  | Rule router (old design) | SJF        |    9.48 | [6.31, 13.20]      | 5%         | worse               |
| phased_mix  | Rule router (old design) | RR4        |  -19.6  | [-28.28, -10.67]   | 78%        | better              |


## Overhead (wall-clock, this machine)

| method                     |   controller_ms_per_run |   wall_ms_per_run |
|:---------------------------|------------------------:|------------------:|
| FCFS                       |                    0.01 |              0.35 |
| SJF                        |                    0.01 |              0.39 |
| RR4                        |                    0.01 |              0.47 |
| SJF* (cheats: true bursts) |                    0.01 |              0.38 |
| Rule router (old design)   |                    1.52 |              1.99 |
| Shadow (A)                 |                   12.25 |             12.78 |
| Shadow+Guard (A+B)         |                   12.13 |             12.65 |
