### headline

| Variant | Evidence Recall@5 | nDCG@10 | Unsupported claims per proposal | Judge score (1-5) | GigSim reply rate | Mean reply probability | p95 latency (s) | Cost per proposal (USD, list) |
|---|---|---|---|---|---|---|---|---|
| V0 | 0.118 | 0.220 | n/a | n/a | n/a | n/a | n/a | n/a |
| Shipped best | 0.186 | 0.440 | n/a | n/a | n/a | n/a | n/a | n/a |

### rag

| Variant | What changes | Recall@5 | Capped R@5 | MRR | nDCG@10 |
|---|---|---|---|---|---|
| V0 naive dense | v0_naive | 0.118 | 0.354 | 0.569 | 0.220 |
| V1 decomposition | v1_decompose | n/a | 0.262 | 0.439 | 0.162 |
| V2 hybrid BM25+dense | v2_hybrid | n/a | 0.365 | 0.605 | 0.236 |
| V4 outcome-aware | v4_outcome | n/a | 0.401 | 0.677 | 0.235 |
| V5 multi-vector projects | v5_multivector | n/a | 0.496 | 0.629 | 0.400 |
| **Shipped: hybrid+outcome+multivector** | combination | 0.186 | 0.555 | 0.772 | 0.440 |

### ablation

| Pipeline | nDCG@10 | Capped R@5 | MRR |
|---|---|---|---|
| hybrid+outcome+multivector (shipped) | 0.440 | 0.555 | 0.772 |
| without hybrid | 0.431 | 0.537 | 0.714 |
| without outcome | 0.407 | 0.508 | 0.649 |
| without multivector | 0.267 | 0.463 | 0.766 |

### decisions

| Run | Profile | Jobs | Bid/skip F1 | Accuracy | Scam P / R | Price in fair band | Unsupported (first draft -> final) | p95 s / job analysed | p95 s / proposal | USD / job (list) | USD / proposal (list) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| main | paid | 60 | 0.769 | 0.750 | 0.89 / 1.00 | 0.44 | 2.24 -> 0.34 | 45.3 | 526.6 | 0.0010 | 0.0063 |
| open | open | 12 | 0.667 | 0.875 | 1.00 / 0.25 | 0.00 | 5.00 -> 0.00 | 110.1 | 12.9 | 0.0011 | 0.0042 |
| open_qwen | open_qwen | 12 | 0.000 | 0.857 | 1.00 / 0.50 | n/a | n/a -> n/a | 112.8 | n/a | 0.0013 | n/a |

### injection

| Injection goal | Attacks | Success, defences off | Success, defences on |
|---|---|---|---|
| exfiltrate_prompt | 3 | 0/3 | 0/3 |
| force_bid | 8 | 0/8 | 0/8 |
| insert_phrase | 4 | 2/4 | 2/4 |
| leak_contact | 3 | 0/3 | 0/3 |
| price_manipulation | 3 | 0/3 | 0/3 |
| **all** | 21 | 0.10 | 0.10 |

### multiagent

| System | Jobs | Bid/skip accuracy | F1 | Scam recall | Unsupported / proposal | Proposals with policy violations | Mean reply probability | Tokens / job | p95 latency (s) |
|---|---|---|---|---|---|---|---|---|---|
| (a) single ReAct agent | 15 | 0.733 | 0.800 | 1.00 | 2.73 | 2 | n/a | 11008 | 143.3 |
| (b) langgraph-supervisor | 15 | 0.667 | 0.762 | 0.50 | 3.33 | 0 | n/a | 8399 | 150.5 |
| (c) hand-built graph | 15 | 0.800 | 0.800 | 1.00 | 1.00 | 0 | n/a | 12813 | 368.0 |

### tools

Model: gpt-4o-mini, 40 tasks.

| Tool design | Tools | Tool-selection accuracy | Argument accuracy | Tokens per task |
|---|---|---|---|---|
| fine | 20 | 0.975 | 0.900 | 2203 |
| coarse | 3 | 0.875 | 0.425 | 324 |
| best | 20 | 0.975 | 0.975 | 2384 |

### ab

_A/B pending_
