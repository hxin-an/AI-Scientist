# Research Knowledge Base

背景知識資料庫，記錄架構設計決策的研究依據。
每份文件包含：**決策摘要（直接可用）** + 完整的原始 deep research 結果。

---

## 已完成

| 檔案 | 內容 | 關鍵結論 |
|------|------|---------|
| [kb_01_sakana_ai_scientist.md](kb_01_sakana_ai_scientist.md) | Sakana v1/v2 深度分析、後繼系統生態 | Docker 必要、重試上限 4 次、Reviewer ensemble、PaperForge/EvoScientist 模式 |
| [kb_02_agent_architecture.md](kb_02_agent_architecture.md) | 長時 agentic pipeline 框架選型、state 設計、記憶體模型 | LangGraph、Git-centric state、3-tier memory、8 項韌性機制 |
| [kb_03_sentinel_monitoring.md](kb_03_sentinel_monitoring.md) | Sentinel 模型選型（動態 VRAM）、推理框架、混合異常偵測 | Qwen 2.5 Coder 分層選型、llama.cpp/ExLlamaV2、Z-score + LLM hybrid |
| [kb_04_paper_and_literature.md](kb_04_paper_and_literature.md) | 文獻調查 pipeline、novelty 評估、LaTeX 論文生成 | S2AG + OpenAlex、Idea Novelty Checker、zero-hallucination citation、Extended Thinking |
| [kb_05_claude_harness.md](kb_05_claude_harness.md) | Claude harness 設計：tool schema、system prompt、multi-agent 溝通、成本管理 | Plan-Then-Execute、Blackboard 模式、Conciliator node、Haiku/Sonnet 分層路由 |
| [kb_06_docker_gpu_training.md](kb_06_docker_gpu_training.md) | Docker + GPU PyTorch：container 設定、安全沙盒、log streaming、可重現性 | python:3.11-slim+uv、genv watchdog、tmux in container、DCGM 雙層健康檢查 |
| [kb_07_self_evolution.md](kb_07_self_evolution.md) | 自我演進機制：DSPy/GEPA prompt 優化、Sentinel model 生命週期、workflow 動態修改 | DSPy+GEPA Pareto optimizer、3D signal、Shadow→A/B→Canary rollout、4-tier failure taxonomy、5-layer guardrails |
| [kb_08_reviewer_validation.md](kb_08_reviewer_validation.md) | Reviewer 統計驗證：統計檢定、ML sanity checks、LangGraph Reviewer subgraph | Welch t-test/Wilcoxon auto-select、zero-trust metric extraction、CAP ensemble calibration、CRITICAL_FAIL interrupt |
| [kb_09_harness_engineering.md](kb_09_harness_engineering.md) | Harness Engineering 學科定義、12-Factor Agents、長時 agent 架構、Claude Agent SDK、基礎設施噪音 | Harness=OS+motherboard、>40%="dumb zone"、Rippable design、Two-agent pattern、Progressive Disclosure Skills、±6pt infra noise |
| [kb_10_research_value.md](kb_10_research_value.md) | 研究價值判斷：5-stage Reviewer pipeline、DeepReviewer-14B、S2AG SPECTER2、Empirical Supremacy | MVVC→DeepReviewer→S2AG 三層過濾、>15%=人工審查、PARTIAL_FAIL=HiTL、Andrew Ng無專用工具 |

---

## 待研究

目前無待研究項目。所有 deep research 已完成。

---

## 使用方式

- 開始新的設計討論前，先讀各 kb 檔案頂部的「Key Decisions」表格
- 所有 deep research 原始內容保留在同一檔案的下半部，可回頭查證
- 需要新 research 時，建立 `pending_XX_topic.md`，結果回來後升級為 `kb_XX`
