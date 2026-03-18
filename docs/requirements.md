# AI Scientist System — Requirements

**版本:** 0.2.0
**日期:** 2026-03-18
**狀態:** Draft — 基於 KB-01 至 KB-10 全部完成後的整合版本

---

## 快速摘要表

| 類別 | 項目 | 決策 |
|------|------|------|
| **系統** | 架構 | LangGraph macro-orchestration + Claude Agent SDK inside nodes |
| **系統** | 狀態管理 | Git-centric + PostgreSQL (LangGraph PostgresSaver) |
| **系統** | 記憶體 | 3-tier: hot (context) / warm (filesystem+RAG) / cold (vector DB) |
| **系統** | 實驗環境 | Docker container，tmux in container，非 host |
| **LLM** | 主模型 | Claude Code CLI（agent 本身，非 API 呼叫） |
| **LLM** | 本地 Sentinel | Qwen 2.5 Coder，依 VRAM 分層：3B / 7B / 14B |
| **LLM** | Reviewer 評審 | DeepReviewer-14B Fast Mode |
| **流程** | Pipeline | Planner → Researcher → Reviewer (5-stage) → Writer |
| **流程** | 自我演進 | DSPy + GEPA；3D composite signal；5-layer guardrails |
| **程式碼** | 語言 / 版本 | Python 3.11+ |
| **程式碼** | 套件管理 | uv（禁止 pip / requirements.txt） |
| **程式碼** | 型別 | 全面強制 type hints；mypy --strict；零 error 才能 merge |
| **程式碼** | 測試 | pytest；integration tests 打真實 PostgreSQL，禁止 mock DB |
| **程式碼** | 風格 | ruff（lint + format）；pre-commit hooks |
| **監測** | 指標 | Prometheus metrics export；8 項核心指標 |
| **監測** | GPU | DCGM 雙層健康檢查 |
| **監測** | 自動 rollback | Reviewer score rolling avg 連續 3 次下降 > 5% → git revert |

---

## 1. 專案概述

### 1.1 目標

自動化 AI Scientist 系統，協助 Deep Learning 研究者執行完整的研究 pipeline——從想法到論文草稿——以最少的人工干預完成。

**最終目標：** 可安裝、可運行的成品（working product），非研究論文。

**版本 1 範圍：** Deep Learning 研究領域。

### 1.2 Stakeholders

| 角色 | 描述 | 主要關注點 |
|------|------|----------|
| 主要使用者 | DL 研究者 | 安裝簡單、結果可信、不需要看 code |
| 專案負責人 | 要求可展示的成品 | 可複現、可展示 |
| 系統管理者 | 共享 GPU 工作站管理 | GPU 資源不被獨佔、系統不崩潰 |

### 1.3 部署環境

- **平台：** Windows（WSL2）/ Linux（Ubuntu 22.04+）同等支援；macOS 無 GPU 模式次之
- **硬體：** RTX 30/40/90 系列消費級 GPU（無 MIG），共用工作站
- **存取方式：** 本地或 SSH 遠端

---

## 2. 資料夾結構

```
ai_scientist/
│
├── ai_scientist/                   # Python package (pip/uv install -e .)
│   ├── agents/                     # LangGraph nodes
│   │   ├── planner.py
│   │   ├── researcher.py
│   │   ├── writer.py
│   │   └── conciliator.py          # Reviewer↔Researcher 震盪防護
│   ├── harness/
│   │   ├── state.py                # LangGraph State schema (Blackboard TypedDict)
│   │   ├── graph.py                # Graph 組裝唯一入口
│   │   ├── hooks.py                # PreToolUse / PostToolUse / SessionStart
│   │   └── circuit_breaker.py      # max Pregel super-steps = 15
│   ├── reviewer/                   # 5-stage Reviewer pipeline
│   │   ├── statistical.py          # Welch t-test / Wilcoxon / BH correction
│   │   ├── sanity_checks.py        # data leakage / sandbagging / code audit
│   │   ├── mvvc.py                 # Minimum Viable Value Check (local)
│   │   ├── deep_review.py          # DeepReviewer-14B Fast Mode
│   │   └── s2ag.py                 # S2AG SPECTER2 + influentialCitationCount
│   ├── sentinel/                   # 本地模型監控
│   │   ├── model.py                # VRAM-tiered model loading
│   │   ├── detector.py             # EMA + Z-score → LLM hybrid
│   │   └── lifecycle.py            # Shadow → A/B → Canary model upgrade
│   ├── evolution/                  # 自我演進
│   │   ├── optimizer.py            # DSPy + GEPA prompt optimization
│   │   ├── regression.py           # Golden dataset trace replay
│   │   └── failure_taxonomy.py     # L1-L4 failure classifier
│   ├── memory/                     # 3-tier memory
│   │   ├── hot.py                  # In-context management
│   │   ├── warm.py                 # Filesystem RAG
│   │   └── cold.py                 # Vector DB (cold storage)
│   ├── tools/                      # Claude Code 可呼叫的工具函數（唯一外部 API 入口）
│   │   ├── literature.py           # S2AG + OpenAlex + ArXiv
│   │   ├── docker_runner.py        # Experiment container 控制
│   │   └── git_ops.py              # Git commit / revert / log
│   ├── monitoring/                 # 系統健康度
│   │   ├── metrics.py              # Prometheus metrics export
│   │   ├── health.py               # /health endpoint + GPU DCGM
│   │   ├── alerts.py               # 告警規則與閾值常數
│   │   └── dashboard.py            # 指標彙整
│   └── config/
│       ├── settings.py             # Pydantic settings (環境變數)
│       └── constants.py            # 所有具名常數（閾值、上限等）
│
├── docker/                         # Experiment container 定義
│   ├── Dockerfile.experiment
│   └── seccomp.json                # 安全沙盒 profile
│
├── experiments/                    # 實驗輸出（gitignored 大檔）
│   └── {exp_id}/
│       ├── models/
│       ├── results/
│       ├── plots/
│       └── config.json
│
├── db/
│   └── migrations/                 # Alembic migrations
│
├── .claude/                        # Claude Agent SDK — Claude 讀的
│   ├── skills/                     # Progressive disclosure skill files
│   │   ├── literature_review.md
│   │   ├── experiment_runner.md
│   │   ├── statistical_validation.md
│   │   └── paper_writing.md
│   └── commands/                   # Slash command macros
│
├── docs/                           # 人讀的文件
│   ├── research/                   # KB-01 至 KB-10 背景知識庫
│   ├── architecture/               # 系統架構設計文件（待寫）
│   ├── runbooks/                   # 操作手冊（告警處理、手動 rollback）
│   └── api/                        # Tool schema 參考文件
│
├── tests/
│   ├── golden_datasets/            # Reviewer regression testing traces
│   └── integration/                # 打真實 PostgreSQL 的整合測試
│
├── CLAUDE.md                       # Harness 根指令（Claude 讀；放 root）
├── CHANGELOG.md                    # 版本紀錄（人讀）
├── README.md                       # 安裝與快速開始（人讀）
└── pyproject.toml                  # 單一 source of truth（uv 管理）
```

**人機分離原則：**
- `CLAUDE.md` + `.claude/` → Claude Agent SDK 讀取，控制 harness 行為
- `docs/` + `README.md` + `CHANGELOG.md` → 人讀，描述系統設計與操作
- 兩者不混用。docs/ 不放 agent instruction，CLAUDE.md 不放使用說明

---

## 3. 系統功能需求 (Functional Requirements)

### 3.1 核心 Pipeline

**FR-01** 系統必須支援完整的自動化研究 pipeline：Planner → Researcher → Reviewer → Writer。

**FR-02** Pipeline 必須能在無人值守的情況下連續運行多天（multi-day autonomous operation）。

**FR-03** 每個決策點必須作為 Git commit 記錄，支援時間旅行式 rollback。

**FR-04** Context window 耗盡後必須自動恢復（Two-Agent Pattern，KB-09）：
- Initializer Agent（首次 session）：建立 JSON task list，所有 task 初始標記為 `failing`
- Coding Agent（後續每個 session）：強制只處理一個 `failing` task
- Session 結束前必須 commit + 自我驗證，才能將 task 標記為 `passing`

**FR-05** 系統必須強制執行 mandatory orientation routine：每次新 session 開始前，agent 必須依序執行：確認工作目錄 → 讀取 progress log → 查看最新 git log → 讀取 task list。

### 3.2 Planner

**FR-06** Planner 必須輸出包含以下欄位的結構化研究提案：
- 量化成功指標（mandatory，不得模糊）
- 要打敗的 baseline（具體論文 + 數字）
- 文獻新穎性評估（基於 S2AG Idea Novelty Checker）
- Sentinel 異常偵測 schema

**FR-07** 研究提案必須等待人工確認後才能繼續執行。

### 3.3 Researcher

**FR-08** Researcher 在 Docker container 內執行實驗，tmux in container（非 host tmux）。

**FR-09** 代碼執行失敗上限為 4 次（KB-01），超過則升級為人工干預。

**FR-10** 實驗完成後必須輸出：論文草稿（LaTeX）、實驗代碼（clean）、超參數配置。

### 3.4 Reviewer（5-stage pipeline）

**FR-11** Reviewer 必須按順序執行以下 5 個 stage，任一 stage 短路即停止：

| Stage | 節點 | 失敗條件 | 路由 |
|-------|------|---------|------|
| 1 | Statistical_Validation | 統計不顯著 / data leakage / sandbagging / metric hallucination | CRITICAL_FAIL |
| 2 | MVVC_Filter | 本地 embedding 相似度 > 0.98（derivative）或 Sentinel 快評 < 3/5 | CRITICAL_FAIL |
| 3 | DeepReviewer_Eval | Fast Mode 評分 < 4/10 | CRITICAL_FAIL |
| 3 | DeepReviewer_Eval | Fast Mode 評分 4–6/10 | PARTIAL_FAIL |
| 4 | S2AG_Impact_Check | 鄰近論文 influentialCitationCount 極低（abandoned field） | PARTIAL_FAIL |
| 5 | Empirical_Supremacy | delta > 15% absolute over SOTA → 覆蓋語言模型的 CRITICAL_FAIL | PARTIAL_FAIL |

**FR-12** Reviewer 必須使用 zero-trust metric extraction：從 CSVLogger / trainer_state.json 直接讀取，不信任 agent 回報數字（KB-08）。

**FR-13** CRITICAL_FAIL 必須將失敗的 hyperparameter trajectory 寫入 experimentation memory，防止系統重複探索同一個死胡同。

**FR-14** PARTIAL_FAIL 必須打包評估報告，送入人工審查 queue，系統暫停等待回應。

**FR-15** LLM ensemble review 必須使用 Comparative Augmented Prompting (CAP) + contextual baseline calibration，不得使用絕對評分（防 adversarial prompt injection）。

**FR-16** PyTorch reproducibility 設定：執行驗證時強制套用 `manual_seed` + `cudnn.deterministic=True` + `cudnn.benchmark=False` + `num_workers=0`。

### 3.5 Sentinel 監控

**FR-17** Sentinel 有三個明確職責：
1. **Watchdog**：以獨立 process 監控 Claude Code session 是否意外終止或卡住，並嘗試自動重啟
2. **Z-score 異常偵測**：監控實驗 metrics（loss、accuracy）是否發散，提早終止廢棄的實驗跑
3. **HiTL 預判**：PARTIAL_FAIL 發生時，在轉交人工審查前先做可行性預評估，降低人工審查負擔

**FR-18** Sentinel 模型依**可用 VRAM**（扣除實驗用量後剩餘）分層載入（KB-03）：
- 可用 < 6GB：Qwen 2.5 Coder 3B（Watchdog + Z-score only）
- 可用 6–12GB：Qwen 2.5 Coder 7B（Watchdog + Z-score + 基本 HiTL）
- 可用 > 12GB：Qwen 2.5 Coder 14B（全功能）

**FR-19** Z-score 異常偵測採用混合式：EMA + Z-score（deterministic Python）先行，僅在觸發時才載入 Sentinel LLM 做語義解讀，平時 Sentinel 盡量讓出 VRAM 給實驗。

**FR-20** Sentinel 觸發後直接呼叫 Python callback 更新 LangGraph State，payload 必須包含 `experiment_id`、`anomaly_type`、`metric_snapshot`，不使用 HTTP webhook。

### 3.6 自我演進

**FR-20** Prompt 自動優化使用 DSPy + GEPA optimizer，優化信號為 3D composite：
- `reproducibility_pass_rate`
- `execution_stability_score`
- `reviewer_quality_rubric`

**FR-21** 每次 prompt mutation 前必須通過 golden dataset regression test（trace replay with stubbed external calls + LLM-as-Judge），失敗則拒絕 mutation。

**FR-22** Sentinel 模型升級必須走三階段：Shadow → A/B Testing（MAB routing）→ Canary（5%→25%→100%）。任一階段出現 latency / accuracy regression 自動 rollback。

**FR-23** Failure taxonomy 必須分類為 4 層（KB-07），每層對應自動介入：
- L1（生成：hallucination）→ GEPA prompt mutation
- L2（資訊：tool/API gap）→ tool parameter swap via Command()
- L3（協作：coordination loop）→ ServerRuntime 插入 Debugging Specialist 節點
- L4（詮釋：goal drift）→ Meta-strategy FSM shift + goal-alignment verification

### 3.7 文獻與論文生成

**FR-24** 文獻調查 pipeline：S2AG（主）→ OpenAlex（fallback）→ ArXiv（LaTeX source）。不使用 Papers With Code（已下線）。

**FR-25** Citation pipeline 零幻覺：追蹤 S2 Paper ID → semantic_bibtool → BibTeX，LLM 不得自行生成 citation。

**FR-26** LaTeX 生成規則：
- LLM 不得修改 preamble
- 以模組化 section 檔案組織（`\input{sections/method.tex}`）
- Figures 由實驗代碼生成，不由 LLM 生成

---

## 4. 非功能需求 — LLM 行為

### 4.1 成本控制

**LLM-01** 系統以 Claude Code CLI 作為 agent，不直接呼叫 Anthropic API。成本由 Claude Code session 使用量決定。單次實驗的 session 成本目標 < $5；使用者可設定 budget cap，超出時系統暫停並通知。

**LLM-02** Context Firewall（KB-09）：任何會超過 40% context window 的子任務，必須委派給 sub-agent。Sub-agent 回傳 compressed summary + evidence contract（line-number citations），不回傳原始資料。

### 4.2 可靠性

**LLM-05** 每個 agent 的 Pregel super-steps 上限為 15。超過觸發 L3 failure handler。

**LLM-06** Tool failure 時不得 crash graph。必須 format error 為可讀文字 → inject into context → 強制 agent 自我修正（12-Factor Factor 9，KB-09）。

### 4.3 安全性

**LLM-07** 核心系統參數（budget caps、API scopes、prohibited actions）在 startup 時以 cryptographic read-only config 載入，agent 無法在 runtime 修改。

**LLM-08** Soft-limit 違規時使用 Guide() command 引導 agent 回到合規狀態，不得直接 crash graph。

---

## 5. 非功能需求 — 程式碼品質

### 5.1 型別安全

**CODE-01** 所有 Python 檔案必須有完整 type hints。CI 強制執行 `mypy --strict`，零 error 才能 merge。

**CODE-02** LangGraph State 必須使用 `TypedDict`。所有 LLM structured output 必須使用 `pydantic.BaseModel` + `.with_structured_output()`，不得用 raw string parsing。

**CODE-03** Tool schema 必須用 Python dataclass 或 Pydantic model 定義，不得用 hardcoded dict。

### 5.2 測試

**CODE-04** Integration tests 必須打真實 PostgreSQL，**禁止 mock database**。（原因：mock 通過但 prod migration 失敗是已知風險。）

**CODE-05** Reviewer pipeline 的 golden dataset（正常 + edge case + adversarial）必須隨 codebase 一起維護在 `tests/golden_datasets/`。

**CODE-06** Prompt mutation 在 commit 前必須通過完整 golden dataset regression。

**CODE-07** 測試覆蓋率目標：core harness + reviewer ≥ 80%；sentinel + evolution ≥ 60%。

### 5.3 程式碼風格

**CODE-08** Linter + formatter：`ruff`（取代 flake8 + black + isort）。設定統一在 `pyproject.toml`。

**CODE-09** Pre-commit hooks：ruff、mypy、secret 掃描（禁止 commit .env）。

**CODE-10** 不得有 magic number。所有閾值、上限、常數必須定義在 `config/constants.py` 並有說明。

```python
# 正確
MAX_PREGEL_SUPER_STEPS = 15       # KB-07: 防止無限迴圈
EMPIRICAL_SUPREMACY_THRESHOLD = 0.15  # KB-10: 超過此 delta 強制人工審查
CONTEXT_DUMB_ZONE_THRESHOLD = 0.40   # KB-09: 超過此比例 context rot

# 錯誤
if steps > 15:  # hardcoded magic number
```

**CODE-11** 新增 public API（module-level function 或 class）必須有 Google-style docstring。

### 5.4 依賴管理

**CODE-12** 套件管理使用 `uv`，不使用 pip。`pyproject.toml` 為 single source of truth，禁止 `requirements.txt`。

**CODE-13** Docker base image：`python:3.11-slim` + uv。不使用 NGC 或 official PyTorch image。

**CODE-14** Optional dependencies 必須在 `pyproject.toml` extras 中分組：`[dev]`、`[sentinel]`、`[monitoring]`。

### 5.5 架構規則

**CODE-15** 模組依賴方向單向：`config` ← `tools` ← `agents` ← `harness`。禁止反向依賴。

**CODE-16** LangGraph graph 組裝必須在單一入口 `harness/graph.py` 完成。各 agent node 不得互相直接 import。

**CODE-17** 所有外部 API 呼叫（S2AG、OpenAlex、Docker daemon）必須透過 `tools/` 封裝，不得在 agent node 內直接呼叫。

### 5.6 版本紀錄

**CODE-18** `CHANGELOG.md` 必須遵守 [Keep a Changelog](https://keepachangelog.com/) 格式。每個版本記錄：Added / Changed / Fixed / Removed。

**CODE-19** Git commit message 格式：`type(scope): description`（Conventional Commits）。CI 強制 lint commit message。

---

## 6. 非功能需求 — 系統健康度與監測

### 6.1 必須監測的指標

**MON-01** 以下 8 項指標必須持續收集並 export 至 Prometheus：

| 指標 | 警告閾值 | 嚴重閾值 | 來源 KB |
|------|---------|---------|---------|
| Token cost velocity（per sub-agent） | > 2x 基準 | > 5x 基準 | KB-09 |
| Prompt prefix cache hit rate | < 70% | < 50% | KB-05/09 |
| Tool call error rate | > 5% | > 15% | KB-09 |
| Context utilization % | > 35% | > 40% | KB-09 |
| Reviewer score（50-exp rolling avg） | 下降 > 3% | 下降 > 5% | KB-07 |
| GPU memory（DCGM） | > 85% | > 95% | KB-06 |
| Sentinel TTFT 退化 | > 10% | > 20% | KB-07 |
| CRITICAL_FAIL rate（per 10 experiments） | > 30% | > 60% | KB-10 |

**MON-02** GPU 健康使用 DCGM 雙層檢查：memory utilization + temperature。任一超出嚴重閾值，暫停新實驗。

**MON-03** Reviewer score rolling average 連續 3 次下降 > 5% → 自動觸發 `git revert` 至最後一個 verified commit，通知人工確認。

### 6.2 健康檢查端點

**MON-04** 系統必須提供 `GET /health` HTTP endpoint：
```json
{
  "status": "healthy | degraded | unhealthy",
  "components": {
    "postgresql": "ok | error",
    "sentinel_model": "ok | loading | error",
    "docker_daemon": "ok | error",
    "gpu": "ok | warning | critical"
  },
  "queue": {
    "partial_fail_pending": 0,
    "active_experiments": 1
  }
}
```

### 6.3 可觀測性

**MON-05** 每個 LangGraph node 的執行時間、token 消耗、tool 呼叫次數必須以 structured JSON log 輸出，包含 `experiment_id`、`node_name`、`session_id`、`timestamp`。

**MON-06** Harness failure 與 model failure 必須在 log 中明確區分（`failure_type: harness | model | tool`）。

**MON-07** Runbook 文件（`docs/runbooks/`）必須覆蓋以下場景：
- cache hit rate 驟降的診斷步驟
- 手動 git revert 流程
- Sentinel 模型手動替換流程
- PostgreSQL checkpoint 損毀恢復

---

## 7. 介面設計

### 7.1 CLI（必要）

```bash
ai-scientist start --idea "your research idea"
ai-scientist status           # 當前 stage、experiment_id、pending queue
ai-scientist approve          # 確認 Planner 的研究方向
ai-scientist review-queue     # 列出 PARTIAL_FAIL 等待人工審查的實驗
ai-scientist approve-exp <id> # 手動核准某個 PARTIAL_FAIL 實驗
ai-scientist reject-exp <id>  # 手動拒絕
ai-scientist logs [--exp <id>]
ai-scientist health           # 呼叫 /health endpoint
```

### 7.2 Discord Bot（可選，v2）

- Pluggable — 系統必須在沒有 Discord bot 的情況下正常運作
- PARTIAL_FAIL → Discord 通知 + Approve/Reject 按鈕
- 狀態持久化：PostgreSQL（非 in-memory）

---

## 8. 系統限制 (Constraints)

| 編號 | 限制 |
|------|------|
| CON-01 | 平台：Windows（WSL2）/ Linux（Ubuntu 22.04+）同等支援。macOS 支援無 GPU 模式 |
| CON-02 | GPU：RTX 30/40/90 系列。無 MIG 時使用 genv watchdog 做 VRAM partitioning |
| CON-03 | 網路：Experiment Docker container 預設 `--network none`。主 orchestrator 需要對外網路 |
| CON-04 | Python：3.11+。不支援 3.10 以下 |
| CON-05 | 可安裝性：可透過 `pip install ai-scientist` 或 `uv add ai-scientist` 安裝 |
| CON-06 | 成本：單次實驗 Claude Code session 成本目標 < $5。使用者可設定 budget cap |
| CON-07 | Docker：實驗 container 必須設定 `--memory-swap = --memory`（禁用 swap）、`--cap-drop=ALL`、custom seccomp |

---

## 9. MVP 範圍

**MVP 包含：**
- 完整 Planner → Researcher → Reviewer（5-stage）→ Writer pipeline
- Sentinel 監控（Watchdog + Z-score anomaly detection + HiTL 預判）
- Git-centric state + LangGraph PostgresSaver（multi-day recovery）
- Docker experiment sandbox
- Prometheus metrics export + `/health` endpoint
- CLI 人工審查 interface（PARTIAL_FAIL queue）

**MVP 不包含（Phase 2）：**
- 自我演進（DSPy+GEPA / skills 文件優化）— 機制需要針對 Claude Code 架構重新設計
- Discord bot HiTL 整合
- Sentinel 三階段模型升級 rollout（MVP 用 manual promotion）
- Packaging / pip release（MVP 用 `uv pip install -e .`）

---

## 10. 未解決問題 (Open Questions)

| # | 問題 | 影響範圍 | 優先級 | 狀態 |
|---|------|---------|--------|------|
| OQ-01 | PostgreSQL 要 self-hosted 還是支援 managed (RDS/Cloud SQL)？ | 安裝複雜度 | 中 | ✅ Local |
| OQ-02 | PARTIAL_FAIL 人工審查 UI 第一版：CLI 還是 simple web dashboard？ | FR-14 | 高 | ✅ CLI + interrupt() |
| OQ-03 | Experiment output retention policy？硬碟空間管理？ | 實驗目錄大小 | 低 | 未解決 |
| OQ-04 | Multi-user 共享 GPU 環境的 isolation 策略（genv namespace 還是 systemd slice）？ | CON-02 | 中 | 未解決 |
| OQ-05 | 自我演進機制在 Claude Code 架構下如何運作（skills 文件優化的驗證機制）？ | Phase 2 | 低 | Phase 2 前解決 |
