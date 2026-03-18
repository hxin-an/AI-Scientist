# AI Scientist — Claude Harness 操作手冊

**這份文件是給 Claude 讀的。** 每次新 session 開始，Claude 必須先讀完這份文件才能執行任何操作。

---

## 專案定位（兩句話）

本系統是一個自動化 Deep Learning 研究 pipeline，從想法到論文草稿，支援自我演進。
目標是可安裝、可展示的 working product，非研究論文。

---

## 每次 Session 開始：Mandatory Orientation

在執行任何 task 之前，必須按順序完成：

```
1. 確認工作目錄（pwd）
2. 讀取 task list（tasks.json 或 TODO.md，如存在）
3. 查看最新 git log（git log --oneline -5）
4. 讀取目標模組的 CLAUDE.md（如存在）
```

跳過任何一步都是錯誤。這是 Two-Agent Pattern 的 orientation routine（KB-09）。

---

## 模組地圖（quick reference）

```
ai_scientist/
├── agents/       — LangGraph nodes（planner, researcher, writer, conciliator）
├── harness/      — Graph 組裝、State schema、hooks、熔斷器
├── reviewer/     — 5-stage 研究價值 pipeline
├── sentinel/     — 本地 LLM 監控（Qwen 2.5 Coder，同一台機器）
├── evolution/    — DSPy+GEPA prompt 優化、失敗分類
├── memory/       — 3-tier 記憶體（hot/warm/cold）
├── tools/        — 所有外部 API 的唯一入口（Claude tool schema）
├── monitoring/   — Prometheus metrics、/health、DCGM
└── config/       — settings.py（Pydantic）、constants.py（所有閾值）
```

---

## 相依規則（必須遵守）

```
✅ harness/   → 可以 import 任何模組
✅ agents/    → 只能 import tools/, memory/, config/
✅ reviewer/  → 只能 import tools/, config/
✅ sentinel/  → 只能 import config/
✅ evolution/ → 只能 import harness/, config/
✅ monitoring/ → 只能 import config/
✅ tools/     → 只能 import config/
✅ config/    → 零相依

❌ agents/ 不得 import reviewer/ 或 sentinel/
❌ evolution/ 不得直接 import agents/（必須透過 harness/）
❌ 任何模組不得反向 import（依賴方向只能向下）
```

新增 import 前先確認方向是否合法。如果不確定，查閱 `docs/architecture/system_design.md` 第 3 節。

---

## 開發規則（非可選）

### 實作順序（每個模組）
1. 先寫 tests（pytest）
2. 先定義 Pydantic schema / TypedDict
3. 最後寫實作

### 程式碼規範
- 所有 function / class 必須有 type hints（mypy --strict，零 error）
- 禁止 magic number，所有閾值從 `config/constants.py` 讀取
- 套件管理只用 uv，禁止 pip 或 requirements.txt
- 風格用 ruff（lint + format），commit 前必須通過
- Conventional Commits 格式：`feat:`, `fix:`, `refactor:`, `test:`, `docs:`

### 禁止事項
- 禁止 mock PostgreSQL（integration tests 打真實 DB）
- 禁止在 constants.py 以外寫數字閾值
- 禁止在 tools/ 以外直接呼叫外部 API
- 禁止修改 [IMMUTABLE] 標記的檔案（見下方）

---

## [IMMUTABLE] 禁止修改的檔案

以下檔案由自我演進系統**不得修改**，Claude 在開發時也應謹慎：

```
[IMMUTABLE] harness/circuit_breaker.py     — 熔斷器邏輯（MAX_PREGEL_SUPER_STEPS=15）
[IMMUTABLE] harness/hooks.py               — PreToolUse/PostToolUse firewall
[IMMUTABLE] reviewer/statistical.py        — zero-trust metric extraction
[IMMUTABLE] config/constants.py            — 所有安全閾值
[IMMUTABLE] monitoring/health.py           — /health endpoint
```

如需修改上述檔案，停下來，先與使用者確認。

---

## 關鍵常數（不要重新定義，從 constants.py import）

| 常數 | 值 | 含義 |
|------|-----|------|
| `MAX_PREGEL_SUPER_STEPS` | 15 | LangGraph 熔斷上限 |
| `MAX_EXPERIMENT_RETRIES` | 4 | 實驗失敗重試上限 |
| `EMPIRICAL_SUPREMACY_THRESHOLD` | 0.15 | delta > 15% 覆蓋 CRITICAL_FAIL |
| `CONTEXT_DUMB_ZONE_THRESHOLD` | 0.40 | >40% context = 委派 sub-agent |
| `DEEP_REVIEWER_CRITICAL_THRESHOLD` | 4.0 | DeepReviewer < 4 = CRITICAL_FAIL |
| `DEEP_REVIEWER_PARTIAL_THRESHOLD` | 6.0 | DeepReviewer 4-6 = PARTIAL_FAIL |

完整常數表：`docs/architecture/system_design.md` 第 10 節。

---

## Context 管理規則

當 context 使用量超過 `CONTEXT_DUMB_ZONE_THRESHOLD`（40%）：

1. **停止** 在當前 context 繼續複雜實作
2. 委派給 sub-agent，回傳 compressed summary + evidence contract
3. 不得在 >40% context 做架構決策

---

## 找不到答案時，查哪裡

| 問題類型 | 去哪裡找 |
|---------|---------|
| 架構決策理由 | `docs/architecture/system_design.md` |
| 技術選型依據 | `docs/research/kb_01` 到 `kb_10` |
| 系統功能需求 | `docs/requirements.md` |
| 模組局部規則 | 各模組目錄下的 `CLAUDE.md` |
| 告警 runbook | `docs/runbooks/` |

---

## 模組局部 CLAUDE.md（開發時創建）

每個模組開始實作前，在該模組目錄建立 `CLAUDE.md`，包含：
- 這個模組的唯一職責（一句話）
- 允許 / 禁止的 import
- 關鍵 schema 或介面
- 已知的 gotcha / 陷阱
