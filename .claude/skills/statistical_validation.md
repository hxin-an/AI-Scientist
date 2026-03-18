# Skill: Statistical Validation

## 觸發時機

Reviewer pipeline 的 Stage 1（Statistical_Validation）。
這是 [IMMUTABLE] 邏輯——不得跳過或修改判斷標準。

## 執行步驟

1. **確認最低執行次數**
   - CV: ≥ 5 runs（`MIN_RUNS_CV`）
   - NLP: ≥ 5 runs（`MIN_RUNS_NLP`）
   - RL: ≥ 10 runs（`MIN_RUNS_RL`）
   - 未達標 → `CRITICAL_FAIL`，原因：insufficient runs

2. **正態性檢定**
   - 呼叫 `reviewer/statistical.py` 的 `shapiro_wilk_test(results)`
   - 正態 → Welch t-test vs baseline
   - 非正態 → Wilcoxon signed-rank test

3. **顯著性判斷**
   - p-value < `STATISTICAL_ALPHA`（0.05）且通過 Benjamini-Hochberg FDR → 顯著
   - 不顯著 → `CRITICAL_FAIL`

4. **Effect size**
   - 計算 Cohen's d / Hedges' g / Cliff's delta（視分佈而定）
   - 記錄到 `validation_report.scores["effect_size"]`

5. **Sanity checks（data integrity）**
   - Data leakage 檢查：train/test split 是否正確
   - Sandbagging 偵測：baseline HP 是否故意調低（3-tiered audit）
   - Metric hallucination：對比 `trainer_state.json` 原始數字

6. **輸出**
   - PASS → 繼續 Stage 2
   - CRITICAL_FAIL → 立即路由回 planner，附上具體失敗原因

## 絕對禁止

- 不得接受 agent 自報的 metric（只讀檔案）
- 不得在「接近顯著」時手動調整 → 直接 CRITICAL_FAIL
