# Skill: Paper Writing

## 觸發時機

Reviewer pipeline 全部通過（PASS）後，writer_node 執行時使用。

## 執行步驟

1. **收集素材**
   - 從 `state["experiment_results"]` 取得所有 metric 和 hyperparameter
   - 從 `state["research_proposal"]` 取得 hypothesis 和 baseline
   - 從 `state["validation_report"]` 取得統計數字（effect size, p-value）

2. **產生 LaTeX 草稿**
   - 呼叫 `tools/latex_writer.py` 的 `generate_paper_draft(state)`
   - 段落順序：Abstract → Introduction → Related Work → Method → Experiments → Conclusion
   - Related Work 必須引用在 literature review 步驟中找到的真實論文（不得捏造）

3. **Citation 驗證（zero-hallucination）**
   - 每一個 `\cite{}` 必須對應到 `state["research_proposal"].novelty_assessment` 中的真實論文
   - 呼叫 `tools/literature.py` 的 `verify_citations(latex_path)` 驗證
   - 找不到的引用 → 移除，不得替換為虛構論文

4. **數字一致性檢查**
   - LaTeX 中的所有數字必須可以 trace 回 `trainer_state.json` 或 `CSVLogger`
   - 呼叫 `reviewer/statistical.py` 的 `verify_numbers_in_latex(latex_path, results)`

5. **輸出**
   - 寫入 `experiments/{run_id}/paper_draft.tex`
   - 更新 `state["paper_draft"]`
   - Git commit：`feat: generate paper draft for {run_id}`

## 品質規則

- 不得在沒有數據支持的情況下做 claim
- Abstract 必須包含：問題、方法、具體數字結果（不得模糊）
- 不得使用「state-of-the-art」等誇大用詞，除非有數字支持
