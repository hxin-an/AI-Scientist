# AI Scientist — System Design

**版本:** 0.1.0
**日期:** 2026-03-18
**基於:** KB-01 至 KB-10、requirements.md v0.2.0

---

## 1. 系統定位（一句話）

自動化 Deep Learning 研究 pipeline：從想法到論文草稿，以最少人工干預、可重現、可自我演進的方式完成。

---

## 2. 模組職責表

每個模組只做一件事。職責不得外溢。

| 模組 | 唯一職責 | 關鍵參考 |
|------|---------|---------|
| `harness/` | 組裝 LangGraph graph、管理 State、執行 hooks、熔斷器 | KB-02, KB-09 |
| `agents/planner.py` | 輸出結構化研究提案（含量化目標 + baseline） | KB-01, KB-04 |
| `agents/researcher.py` | 在 Docker container 內執行 ML 實驗 | KB-06 |
| `agents/writer.py` | 將實驗結果轉成 LaTeX 論文草稿 | KB-04 |
| `agents/conciliator.py` | 防止 Reviewer ↔ Researcher 震盪迴圈 | KB-05 |
| `reviewer/` | 5-stage 研究價值判斷 pipeline | KB-08, KB-10 |
| `sentinel/` | 本地 LLM 監控 + 異常偵測（同一台機器） | KB-03 |
| `evolution/` | DSPy+GEPA prompt 優化、失敗分類、regression 測試 | KB-07 |
| `memory/` | 3-tier 記憶體管理（hot/warm/cold） | KB-02 |
| `tools/` | 所有外部 API 的唯一入口（Claude tools schema） | KB-05 |
| `monitoring/` | Prometheus metrics、/health endpoint、DCGM | requirements.md |
| `config/constants.py` | 全部具名常數，禁止 magic number | requirements.md |

---

## 3. 模組相依規則（禁止反向 import）

```
harness/ → 可以 import 任何模組
agents/  → 只能 import tools/, memory/, config/
reviewer/ → 只能 import tools/, config/
sentinel/ → 只能 import config/（不得 import agents 或 reviewer）
evolution/ → 只能 import harness/, config/（不得修改 reviewer/ 或 sentinel/）
monitoring/ → 只能 import config/（不得 import agents 或 evolution）
tools/   → 只能 import config/（零相依）
config/  → 零相依（最底層）
```

**原則：** 依賴方向只能向下。`evolution/` 優化 harness，不得繞過 harness 直接操作 agents。

---

## 4. LangGraph State 結構

```python
class AIScientistState(TypedDict):
    # --- 研究核心 ---
    research_proposal: ResearchProposal | None
    experiment_results: ExperimentResults | None
    paper_draft: PaperDraft | None

    # --- Reviewer pipeline ---
    validation_report: ValidationReport | None   # PASS / PARTIAL_FAIL / CRITICAL_FAIL
    reviewer_stage: int                           # 1–5，紀錄卡在哪個 stage

    # --- 控制流 ---
    pregel_step_count: int                        # 熔斷器：上限 MAX_PREGEL_SUPER_STEPS=15
    failure_count: int                            # 實驗失敗次數：上限 MAX_EXPERIMENT_RETRIES=4
    human_review_pending: bool                    # PARTIAL_FAIL 時設為 True，等待 interrupt()

    # --- 自我演進 ---
    evolution_signal: EvolutionSignal | None      # 3D composite signal
    last_gepa_run: datetime | None

    # --- 追蹤 ---
    session_id: str
    git_commit_hash: str                          # 每個決策點的 checkpoint
    error_log: list[str]
```

State 只能透過 `harness/state.py` 定義的 reducer 修改，nodes 不得直接 mutate。

---

## 5. LangGraph Graph 結構

```
START
  │
  ▼
[orientation_node]          ← 強制 mandatory orientation routine（FR-05）
  │
  ▼
[planner_node]              ← 輸出 ResearchProposal
  │
  ▼ (human_approval_interrupt)
[researcher_node]           ← Docker container 內執行
  │
  ├─ failure_count >= 4 ──→ [human_escalation_node] → END
  │
  ▼
[reviewer_subgraph]         ← 5-stage pipeline（見下）
  │
  ├─ CRITICAL_FAIL ───────→ [planner_node]（重新規劃）
  ├─ PARTIAL_FAIL ────────→ [human_review_interrupt] → (approve) → [writer_node]
  │                                                   → (reject)  → [planner_node]
  │
  ▼ (PASS)
[writer_node]               ← LaTeX 論文草稿
  │
  ▼
[evolution_node]            ← DSPy+GEPA（非同步，不阻塞主流程）
  │
  ▼
END

--- Reviewer Subgraph ---
[statistical_validation] → [mvvc_filter] → [deep_reviewer] → [s2ag_check] → [empirical_supremacy]
每個 stage 短路：CRITICAL_FAIL / PARTIAL_FAIL 立即路由，不執行後續 stage
```

熔斷器位置：`harness/circuit_breaker.py` 在每個 super-step 前檢查 `pregel_step_count`。

---

## 6. 關鍵資料流

### 6.1 Happy Path

```
Planner 輸出 ResearchProposal
  → 人工確認（interrupt）
  → Researcher 執行實驗 → trainer_state.json / CSVLogger（zero-trust metric extraction）
  → Reviewer 5-stage 全通過
  → Writer 生成 LaTeX
  → Evolution node 更新 prompt 優化 signal
```

### 6.2 PARTIAL_FAIL 審查流程

```
Reviewer 輸出 ValidationReport(status=PARTIAL_FAIL)
  → LangGraph.interrupt() 暫停，狀態寫入 PostgreSQL
  → CLI: `ai-scientist review list` 顯示待審項目
  → CLI: `ai-scientist review approve <run_id>` 或 `reject`
  → PostgresSaver 恢復 graph，路由至 writer_node 或 planner_node
```

### 6.3 Self-Evolution 觸發

```
每次實驗完成後，evolution_node 計算 3D composite signal：
  reproducibility_pass_rate × execution_stability_score × reviewer_quality_rubric

signal 低於閾值 → DSPy+GEPA mutation pipeline（L1–L4 failure taxonomy）
→ Golden dataset trace replay regression testing
→ Shadow → A/B → Canary rollout（Sentinel model 升級適用）
→ 5-layer guardrail 檢查（不得修改 [IMMUTABLE] 節點）
```

---

## 7. 技術決策摘要

| 決策 | 選擇 | 理由 | 來源 |
|------|------|------|------|
| 主框架 | LangGraph | Pregel message-passing、PostgresSaver、Command() routing | KB-02 |
| Agent | Claude Code CLI | CLI 本身就是 agent；Python package 只提供工具和狀態 | KB-09, 架構決策 |
| 本地 Sentinel | Qwen 2.5 Coder（VRAM 分層） | 動態 VRAM 預算；同機器需讓出資源給實驗 | KB-03 |
| Reviewer | DeepReviewer-14B Fast Mode | 80-88% win rate vs proprietary；抗 smart plagiarism | KB-10 |
| Checkpointing | PostgreSQL local（PostgresSaver） | LangGraph 原生支援；支援 interrupt() 恢復 | KB-02 |
| 套件管理 | uv | 速度、lockfile、pyproject.toml 單一 source | requirements.md |
| 實驗隔離 | Docker + tmux in container | 可重現、安全沙盒、非 host tmux | KB-06 |
| 文獻搜尋 | S2AG + OpenAlex | SPECTER2 embedding；influentialCitationCount | KB-04, KB-10 |
| 人工審查 UI | CLI + interrupt() 非同步 | 不需 web infra；LangGraph 天然支援 | OQ-02 決策 |

---

## 8. Sentinel 設計

### 8.1 三個職責

| 職責 | 說明 | 觸發條件 |
|------|------|---------|
| **Watchdog** | 獨立 process 監控 Claude Code session 是否意外終止或卡住 | session 無輸出超過 N 秒 |
| **Z-score 偵測** | 監控實驗 metrics（loss、accuracy）是否發散，提早終止廢棄的跑 | EMA + Z-score > 3σ |
| **HiTL 預判** | PARTIAL_FAIL 發生時先做可行性預評估，降低人工審查負擔 | `validation_report.status == PARTIAL_FAIL` |

Sentinel 觸發後直接呼叫 Python callback 更新 LangGraph State，**不使用 HTTP webhook**。

### 8.2 VRAM 分層（可用 VRAM = 總 VRAM − 實驗佔用）

| 可用 VRAM | 載入模型 | 可用職責 |
|----------|---------|---------|
| < 6 GB | Qwen 2.5 Coder 3B (Q4_K_M) | Watchdog + Z-score |
| 6–12 GB | Qwen 2.5 Coder 7B (Q4_K_M) | Watchdog + Z-score + 基本 HiTL |
| > 12 GB | Qwen 2.5 Coder 14B (Q4_K_M) | 全功能 |

實驗進行中 Sentinel 優先讓出 VRAM；平時盡量以最小模型常駐做 Watchdog。

```
VRAM 規則（constants.py）：
  SENTINEL_VRAM_BUDGET_RATIO = 0.20   # Sentinel 最多佔剩餘 VRAM 的 20%
  EXPERIMENT_VRAM_RESERVE_GB = 2.0    # 實驗執行時保留的緩衝
```

DCGM watchdog：memory 使用率 > 90% 或 temperature > 85°C → alert + 強制降級 Sentinel。

### 8.3 Shadow → A/B → Canary（post-MVP）

Sentinel 模型升級路徑，MVP 階段直接換模型即可。

---

## 9. Self-Evolution 不可變邊界（IMMUTABLE）

以下元件由 evolution 系統**不得修改**：

```
[IMMUTABLE] harness/circuit_breaker.py     — MAX_PREGEL_SUPER_STEPS = 15
[IMMUTABLE] harness/hooks.py               — PreToolUse / PostToolUse firewall
[IMMUTABLE] reviewer/statistical.py        — 統計驗證邏輯（zero-trust metric extraction）
[IMMUTABLE] config/constants.py            — 所有安全閾值常數
[IMMUTABLE] monitoring/health.py           — /health endpoint
[IMMUTABLE] CLAUDE.md（所有層級）           — Harness 操作規則

可修改（需通過 5-layer guardrail）：
  agents/ 的 system prompt
  reviewer/ 的 scoring rubric（不含統計邏輯）
  harness/ 的 routing 條件（不含熔斷器）
  evolution/ 自身的 mutation pipeline
```

---

## 10. 常數來源對照表

所有閾值只能從 `config/constants.py` 讀取，不得 hardcode。

| 常數名 | 值 | 來源 KB |
|--------|-----|--------|
| `MAX_PREGEL_SUPER_STEPS` | 15 | KB-07 |
| `MAX_EXPERIMENT_RETRIES` | 4 | KB-01 |
| `EMPIRICAL_SUPREMACY_THRESHOLD` | 0.15 | KB-10 |
| `CONTEXT_DUMB_ZONE_THRESHOLD` | 0.40 | KB-09 |
| `DEEP_REVIEWER_CRITICAL_THRESHOLD` | 4.0 | KB-10 |
| `DEEP_REVIEWER_PARTIAL_THRESHOLD` | 6.0 | KB-10 |
| `MVVC_SIMILARITY_CRITICAL` | 0.98 | KB-10 |
| `MVVC_SENTINEL_SCORE_MIN` | 3 | KB-10 |
| `S2AG_COSINE_SWEET_SPOT_LOW` | 0.60 | KB-10 |
| `S2AG_COSINE_SWEET_SPOT_HIGH` | 0.85 | KB-10 |
| `SENTINEL_VRAM_BUDGET_RATIO` | 0.20 | KB-03 |
| `ROLLBACK_REVIEWER_SCORE_DROP` | 0.05 | requirements.md |
| `ROLLBACK_CONSECUTIVE_DROPS` | 3 | requirements.md |

---

## 11. Open Questions（已解決）

| ID | 問題 | 決策 |
|----|------|------|
| OQ-01 | LangGraph vs 自訂 orchestration | LangGraph |
| OQ-02 | PARTIAL_FAIL 人工審查 UI | CLI + LangGraph interrupt() 非同步 |
| OQ-03 | Sentinel 同機器 vs 獨立機器 | 同一台機器，VRAM 動態讓出（見第 8 節） |
| OQ-04 | PostgreSQL local vs managed | Local |
