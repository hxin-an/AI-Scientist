# Skill: Experiment Runner

## 觸發時機

當 researcher_node 需要執行 ML 實驗時使用。

## 執行步驟

1. **準備實驗環境**
   - 呼叫 `ai_scientist/tools/docker_runner.py` 的 `build_experiment_container()`
   - 確認 GPU 可用：`check_gpu_health()`（呼叫 monitoring/health.py）
   - 確認 Sentinel VRAM budget 已讓出（`sentinel/model.py` 的 `release_vram_for_experiment()`）

2. **執行實驗**
   - 在 container 內啟動 tmux session（非 host tmux）
   - 呼叫 `run_experiment(config: dict) -> str`，回傳 container_id
   - 監控進度：每 60s 呼叫 `get_experiment_logs(container_id)`

3. **Zero-trust metric extraction（[IMMUTABLE] 原則）**
   - 不接受 agent 自報的數字
   - 直接讀取 `trainer_state.json` 或 `CSVLogger` 輸出
   - 呼叫 `tools/docker_runner.py` 的 `extract_metrics_from_container(container_id)`

4. **失敗處理**
   - 失敗時：`state["failure_count"] += 1`
   - 達到 `MAX_EXPERIMENT_RETRIES`（4次）→ 停止，等待人工干預
   - 每次失敗寫入 `state["error_log"]`，包含 container logs 摘要

5. **成功後**
   - 更新 `state["experiment_results"]`（含 metric_source path）
   - Git commit：`git_ops.commit_experiment_results(run_id)`

## 安全規則

- 實驗只在 Docker container 內執行，禁止在 host 直接跑訓練
- container 無網路存取（seccomp profile）
- 實驗結束後強制清理 container
