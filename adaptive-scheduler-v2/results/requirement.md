# Requirement experiment (Idea C)

Target: p95 waiting time <= LIMIT, where LIMIT = 1.25 x the mean of the best fixed rule's p95 (a tight but reachable target). 'Violation rate' = share of runs whose ACTUAL p95 over the whole run broke the limit.

|                                       |   limit |   violation_rate |   avg_wait |   p95_wait |
|:--------------------------------------|--------:|-----------------:|-----------:|-----------:|
| ('batch', 'FCFS')                     |  127.11 |             0.22 |      43.84 |     102.22 |
| ('batch', 'RR4')                      |  127.11 |             0.87 |     153.72 |     292.08 |
| ('batch', 'SJF')                      |  127.11 |             0.41 |      39.56 |     157.15 |
| ('batch', 'Shadow+Guard (A+B)')       |  127.11 |             0.42 |      39.94 |     154.02 |
| ('batch', 'Shadow+Req (A+C)')         |  127.11 |             0.28 |      42.47 |     122.71 |
| ('interactive', 'FCFS')               |   42.91 |             0.2  |      16.53 |      34.33 |
| ('interactive', 'RR4')                |   42.91 |             0.6  |      24.64 |      60.29 |
| ('interactive', 'SJF')                |   42.91 |             0.59 |      14.24 |      70.91 |
| ('interactive', 'Shadow+Guard (A+B)') |   42.91 |             0.56 |      14.89 |      69.03 |
| ('interactive', 'Shadow+Req (A+C)')   |   42.91 |             0.55 |      14.51 |      65.31 |
| ('mixed', 'FCFS')                     |  104.25 |             0.35 |      39.03 |      88.07 |
| ('mixed', 'RR4')                      |  104.25 |             0.75 |      68.46 |     196.83 |
| ('mixed', 'SJF')                      |  104.25 |             0.42 |      26.23 |     102.85 |
| ('mixed', 'Shadow+Guard (A+B)')       |  104.25 |             0.42 |      29.12 |     107.16 |
| ('mixed', 'Shadow+Req (A+C)')         |  104.25 |             0.39 |      28.92 |      99.05 |
| ('phased', 'FCFS')                    |   88.09 |             0.27 |      32.61 |      73.99 |
| ('phased', 'RR4')                     |   88.09 |             0.73 |      63.78 |     207.23 |
| ('phased', 'SJF')                     |   88.09 |             0.37 |      20.78 |      94.63 |
| ('phased', 'Shadow+Guard (A+B)')      |   88.09 |             0.31 |      21.69 |      89.54 |
| ('phased', 'Shadow+Req (A+C)')        |   88.09 |             0.43 |      25.18 |      94.1  |
| ('phased_mix', 'FCFS')                |  140.39 |             0.32 |      66.19 |     129.99 |
| ('phased_mix', 'RR4')                 |  140.39 |             0.72 |      75.77 |     223.39 |
| ('phased_mix', 'SJF')                 |  140.39 |             0.44 |      46.69 |     155    |
| ('phased_mix', 'Shadow+Guard (A+B)')  |  140.39 |             0.39 |      51.38 |     151.34 |
| ('phased_mix', 'Shadow+Req (A+C)')    |  140.39 |             0.4  |      45.14 |     151.39 |
| ('spiky', 'FCFS')                     |  140.34 |             0.47 |      60.4  |     150.78 |
| ('spiky', 'RR4')                      |  140.34 |             0.37 |      34.96 |     150    |
| ('spiky', 'SJF')                      |  140.34 |             0.51 |      52.18 |     157.31 |
| ('spiky', 'Shadow+Guard (A+B)')       |  140.34 |             0.37 |      42.81 |     137.26 |
| ('spiky', 'Shadow+Req (A+C)')         |  140.34 |             0.4  |      42.84 |     142.1  |
