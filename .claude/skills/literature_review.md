# Skill: Literature Review

## 觸發時機

當 planner_node 需要評估研究新穎性，或 Researcher 需要了解 SOTA 時使用。

## 執行步驟

1. **搜尋 Semantic Scholar (S2AG)**
   - 呼叫 `ai_scientist/tools/literature.py` 的 `search_semantic_scholar(query, limit=20)`
   - 取得 `influentialCitationCount` 和 SPECTER2 embedding

2. **搜尋 OpenAlex**
   - 呼叫 `search_openalex(query)` 補充 S2AG 沒有的論文

3. **Novelty Check（S2AG Idea Novelty Checker 模式）**
   - 計算提案 embedding 與搜尋結果的 cosine distance
   - sweet spot: 0.60–0.85（constants.py: `S2AG_COSINE_SWEET_SPOT_LOW/HIGH`）
   - < 0.60 → 太接近現有工作，標記為 derivative
   - > 0.85 → 距離主流太遠，標記為 speculative

4. **輸出**
   - 更新 `state["research_proposal"].novelty_assessment`
   - 列出 top-5 相關論文（含 citation count）
   - 明確指出要打敗的 baseline 論文和數字

## 限制

- 不得捏造論文標題或引用數
- 若 API 回傳空結果，記錄到 `state["error_log"]` 並繼續（不中斷 pipeline）
- 每次搜尋後 sleep 1s（API rate limit）
