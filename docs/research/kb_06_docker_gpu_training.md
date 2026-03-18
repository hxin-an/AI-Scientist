# Knowledge Base 06: Docker + GPU PyTorch Training Environment Management

> Source: Gemini Deep Research, 2026-03-18
> Purpose: Design reference for Researcher stage experiment execution infrastructure

---

## Key Decisions Derived from This Research

### Container 基本設定

| 項目 | 決策 | 原因 |
|------|------|------|
| GPU toolkit | nvidia-container-toolkit（非 nvidia-docker2，已棄用）| 現代標準，CDI 整合 |
| Base image | `python:3.11-slim` + `uv` | 最小攻擊面，無多餘 apt/編譯工具 |
| 依賴管理 | `uv.lock` + `uv sync --frozen` | 確定性構建，比 pip freeze 可靠 |
| Image 固定 | FROM image@SHA256 digest（非 tag）| 防止 base image 靜默更新 |

### GPU 記憶體分區（RTX 4090，無 MIG）

- **推薦**：`genv` watchdog + `--gpu-memory` flag 限制訓練 container VRAM
- 備選：vLLM colocate mode + `torch.cuda.set_per_process_memory_fraction(0.8)`
- 避免：裸跑兩個進程搶 VRAM，會靜默 OOM

### 必要 Docker 資源限制

```bash
--memory="64g"          # 防止觸發 host OOM killer
--memory-swap="64g"     # 等於 memory → 禁用 swap（DL swapping 會系統鎖死）
--cpus="16"             # 保留 CPU 給 Sentinel 和 orchestrator
--shm-size="16g"        # PyTorch DataLoader 必須，預設 64MB 會 Bus error
--pids-limit=1024       # 防 fork bomb
```

### 安全沙盒（必要，非可選）

```bash
--cap-drop=ALL          # 移除所有 Linux capabilities
--security-opt seccomp=default.json   # 過濾系統呼叫
--network none          # 預設無網路（需要時用獨立 container 下載 dataset 再 mount）
--user uid:gid          # 非 root 執行
-v /datasets:/workspace/datasets:ro   # dataset 唯讀
-v /experiments/exp_id:/workspace/output:rw  # 只開放輸出目錄寫入
```

### Session 持久性：tmux 在 container 內部

```bash
# Container entrypoint：在 container 內啟動 tmux
tmux new-session -s exp_session -d

# LangGraph orchestrator 讀取 terminal 狀態（不中斷執行）
docker exec <id> tmux capture-pane -t exp_session -p
```

**不要**在 host tmux 裡跑 docker run（orchestrator 重啟後難以程式化重連）

### Log 串流給 Sentinel

- Docker 使用 `json-file` logging driver
- Sentinel 直接 tail host 上的 JSON log 檔案（非 `docker logs --follow`）
- 需要外部 logging aggregator 時，必須開啟 dual logging（否則 Sentinel 看不到 log）
- DCGM telemetry（GPU util + power）是偵測「假存活」stall 的關鍵信號

### 健康檢查：雙層訊號

```
Layer 1: Container log 解析（STDOUT 有 loss metrics = 正常；STDERR traceback = 崩潰）
Layer 2: DCGM 硬體指標（GPU util 從 >300W 掉到 ~50W 但 PID 還活著 = stall）
演算法：CUSUM 偵測 GPU util 的 regime shift
```

### PyTorch 可重現性設定

```python
torch.manual_seed(0)
random.seed(0)
np.random.seed(0)
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True
# 注意：某些 CUDA atomic ops 仍不可避免有浮點差異，需在報告中說明
```

### Checkpoint 格式（可中斷恢復）

```python
torch.save({
    'epoch': epoch,
    'model_state_dict': model.state_dict(),
    'optimizer_state_dict': optimizer.state_dict(),
    'loss': loss,
}, "/workspace/output/checkpoint_latest.pt")
```

### 實驗輸出目錄標準結構

```
/workspace/output/
├── models/      # .pt / .safetensors 權重 + checkpoint
├── results/     # JSON schema（MetricDatum: name, value, epoch）
├── plots/       # PDF 向量圖（loss curves, ROC, etc.）
└── config/      # uv.lock + Dockerfile + hyperparameter YAML
```

---

## Original Research Question and Full Answer

# Research Prompt: Docker + GPU PyTorch Training Environment Management

## Context

We are building an AI Scientist system where the Researcher agent automatically generates and executes Deep Learning experiments. Experiments run inside Docker containers for isolation and security. The containers must have GPU access (NVIDIA RTX 4090 or similar) for PyTorch training. The system is orchestrated by LangGraph running on the host, with a Sentinel model also running on the same machine.

From prior research we know:
- Docker containerization is required (Sakana AI documented jailbreak attempts from unconstrained agents)
- The Sentinel model runs alongside the training container on the same GPU
- Experiments run for multiple days (tmux for session persistence)
- SSH is used to connect to the workstation from the orchestrator
- The host is Linux with shared NVIDIA GPUs

## What We Already Know

- nvidia-docker / nvidia-container-toolkit exists for GPU passthrough
- Sentinel uses llama.cpp or ExLlamaV2 co-located on the same GPU
- Containers need to communicate experiment logs to the Sentinel's monitoring process

## Investigate

### Part A: Container Setup for DL Training

1. **NVIDIA Container Toolkit in 2026**: What is the current recommended setup for running PyTorch training with GPU access inside Docker? How has the nvidia-docker2 → nvidia-container-toolkit migration settled? What is the minimal working configuration for `docker run --gpus`?

2. **Base image selection**: What is the recommended PyTorch Docker base image in 2026 for training workloads? NVIDIA NGC images vs. official PyTorch images vs. community images — what are the practical tradeoffs for an automated system that needs to run arbitrary user code?

3. **GPU memory partitioning**: When a Sentinel model and a training container both need GPU access, what mechanisms exist to partition GPU memory? MIG (Multi-Instance GPU)? CUDA_VISIBLE_DEVICES? Memory fraction limits? What works on consumer RTX 4090 hardware vs. enterprise A100/H100?

4. **Container resource limits**: What Docker resource constraints (memory, CPU, GPU fraction) should be set to prevent a runaway training job from destabilizing the host system? What are the recommended limits for a shared workstation environment?

### Part B: Code Execution and Security

5. **Sandboxing LLM-generated code**: When Claude generates a Python training script and executes it inside a container, what additional security layers are recommended beyond Docker isolation? What are the known escape vectors for containerized LLM agents, and what mitigations exist?

6. **Read-only host mounts**: What is the recommended pattern for mounting dataset directories and model checkpoints into a training container as read-only, while allowing the container to write only to a designated output directory?

7. **Container lifecycle management**: Who creates and destroys the training container? The LangGraph orchestrator? A separate container manager? What is the recommended pattern for:
   - Launching a new container with the generated training script
   - Monitoring its health from outside
   - Cleanly stopping it if the Sentinel detects an anomaly
   - Extracting results after completion

### Part C: Log Streaming and Monitoring Integration

8. **Log streaming from container to Sentinel**: What is the most reliable pattern for the Sentinel (running on the host) to continuously read the live stdout/stderr of a running Docker container? `docker logs --follow`? Mounted log file? Unix socket? What are the failure modes?

9. **tmux inside Docker**: Can tmux be used inside a Docker container for session persistence? What are the architectural tradeoffs between running the training process directly (PID 1) vs. inside tmux inside the container?

10. **Health check design**: What Docker HEALTHCHECK patterns work well for a PyTorch training job? How do you distinguish between "training normally" / "training stalled" / "crashed" using only container-level signals?

### Part D: Experiment Reproducibility

11. **Deterministic container builds**: How do you ensure that a Docker container built by Claude from a generated Dockerfile produces reproducible results across rebuilds? What pitfalls (floating dependency versions, non-deterministic apt installs) must be avoided?

12. **Checkpoint and resume inside containers**: What is the recommended pattern for saving PyTorch training checkpoints so that a training job interrupted by a Sentinel anomaly detection can be resumed cleanly in a new container?

13. **Results extraction and packaging**: When training completes, how should the container output (model weights, metrics, logs, plots) be extracted and structured for the Reviewer stage? What format makes automated validation easiest?

## Constraints

- Target hardware: NVIDIA RTX 4090 (consumer GPU, no MIG support) or similar workstation GPUs
- Host OS: Linux
- Training framework: PyTorch
- Must support multi-day training runs
- Prefer solutions validated in production ML environments, 2024–2026


# **Architectural Blueprint for Autonomous Machine Learning Experimentation Systems**

## **Introduction to Autonomous Machine Learning Infrastructure**

The emergence of autonomous machine learning systems signifies a structural evolution in computational research. Frameworks designed to operate as autonomous research agents, such as Sakana AI's "The AI Scientist," have demonstrated the capacity to automate the entire lifecycle of scientific discovery.1 These systems harness Large Language Models (LLMs) to independently conceptualize novel architectures, author the requisite Deep Learning (DL) training scripts, execute these experiments, and perform subsequent peer review based on the empirical results.3 However, the transition from human-supervised computational environments to fully autonomous execution paradigms introduces a spectrum of profound infrastructural challenges. When a generative model is granted the agency to write and execute arbitrary code, the underlying computing environment must evolve from a permissive development workstation into a hardened, zero-trust execution sandbox.

This comprehensive architectural blueprint delineates the optimal engineering parameters for constructing an AI Scientist system deployed on consumer-grade hardware. The specific target environment consists of a Linux host equipped with an NVIDIA RTX 4090 GPU, orchestrated by LangGraph acting as the stateful supervisor.5 A locally hosted Sentinel LLM shares the host's computational resources, running concurrently to monitor live training logs for anomaly detection, security breaches, and runtime governance.7

The technical constraints imposed by consumer hardware are significant. The NVIDIA RTX 4090, built on the AD102 architecture, lacks the Multi-Instance GPU (MIG) support found in enterprise-grade accelerators like the A100 or H100.9 This necessitates the implementation of advanced software-defined resource partitioning to ensure the Sentinel model and the training container can co-exist without triggering Out-of-Memory (OOM) failures or destructive context switching. Furthermore, the reality of deep learning research dictates that experiments frequently run for multiple days, demanding robust session persistence, precise anomaly detection to prevent silent hardware stalling, and cryptographic-level determinism in container builds to guarantee experimental reproducibility.10 The subsequent sections provide an exhaustive analysis of these requirements across container orchestration, security boundary enforcement, telemetry streaming, and state resiliency.

## **Part A: Container Setup for Deep Learning Training**

The foundational layer of the autonomous AI Scientist system is the execution environment where the LLM-generated PyTorch code operates. This environment must strike a delicate balance: it must provide unhindered access to the underlying hardware accelerators to maximize training throughput, while simultaneously confining the execution to strictly limit the blast radius of any rogue or malformed code.

### **The Evolution and Implementation of the NVIDIA Container Toolkit**

The methodology for exposing NVIDIA GPUs to Docker containers has matured significantly over recent years. The legacy nvidia-docker2 package and its associated customized Docker runtime wrapper have been entirely deprecated. In 2026, the industry standard relies on the native integration of the NVIDIA Container Toolkit.12 This architectural shift leverages the Container Device Interface (CDI), allowing standardized container engines to interact seamlessly with external accelerators without requiring a specialized runtime executable for every invocation.

To establish the baseline connection between the Linux host and the containerized environment, the host system requires only the proprietary NVIDIA display drivers and the nvidia-container-toolkit package.12 A common misconception is that the host requires a full CUDA Toolkit installation; however, this is no longer the case. The standalone CUDA toolkit is unnecessary on the host because the requisite CUDA libraries, compilers, and runtime components are bundled directly within the container images.14

The critical configuration step involves patching the Docker daemon to recognize the NVIDIA runtime via the command nvidia-ctk runtime configure \--runtime=docker, followed by a restart of the Docker daemon service.13 Once this integration is established, exposing the GPU to the execution environment utilizes the native Docker device mapping flag \--gpus all or a specific device index such as \--gpus '"device=0"'.9 This implementation allows the Docker engine to map the specific device nodes (e.g., /dev/nvidia0, /dev/nvidiactl, and /dev/nvidia-uvm) directly into the container's namespace. The NVIDIA Container Toolkit dynamically injects the necessary driver libraries into the container at runtime, ensuring that the PyTorch binary compiled against a specific CUDA version can communicate with the host's kernel driver.

### **Base Image Selection for Arbitrary Execution**

Selecting the appropriate base image for the training container is a critical architectural decision. The chosen image heavily influences deployment velocity, execution efficiency, and the total attack surface exposed to the autonomous agent. For an automated system executing arbitrary, unverified code, three primary image paradigms exist, each presenting distinct trade-offs.

Table 1: Comparison of PyTorch Docker Base Image Paradigms

| Image Paradigm | Architectural Characteristics | Suitability for Autonomous Agent Execution |
| :---- | :---- | :---- |
| **NVIDIA NGC (nvcr.io)** | Pre-compiled with TensorRT, NCCL, and highly optimized for specific hardware generations. Massive footprint (often \>15GB).12 | Low. While highly optimized for multi-node enterprise environments, the massive footprint slows down rapid container churn. Furthermore, it contains extensive profiling and debugging toolchains that introduce unnecessary attack vectors for an adversarial agent. |
| **Official PyTorch (pytorch/pytorch)** | Contains standard PyTorch binaries, fundamental CUDA toolkits, and cuDNN. Moderate size (5-8GB).13 | Moderate. Standardized and reliable for general development. However, these images often contain excess system utilities and compilation tools that an LLM could leverage for container escape or network manipulation. |
| **Slim Python \+ uv (python:3.11-slim)** | Minimal Debian-based image requiring manual installation of PyTorch via the Astral uv package manager.15 | High. Provides the absolute minimum attack surface. Enforces strict dependency locking and explicitly drops all unnecessary system binaries. Resolution of ML dependencies is handled dynamically and deterministically. |

For a system executing LLM-generated code, the python:3.11-slim image augmented with the uv package manager represents the optimal choice. It adheres strictly to the principle of least privilege by omitting compilation toolchains, package managers like apt, and unnecessary networking utilities that are frequently exploited during container breakout attempts.15 Dependencies generated by the Researcher agent can be resolved at unprecedented speeds utilizing uv, a package manager written in Rust that operates orders of magnitude faster than the standard pip utility while ensuring deterministic dependency resolution through universal lockfiles.16

### **GPU Memory Partitioning on Consumer Hardware**

The most acute infrastructural challenge in this architecture is the co-location of the Sentinel inference model and the PyTorch training container on a single NVIDIA RTX 4090 GPU. Enterprise architectures, such as those utilizing the A100 or H100 chips, support Multi-Instance GPU (MIG) technology, which allows the physical hardware to be securely partitioned into isolated instances with dedicated memory and compute cores.9 The RTX 4090, however, relies on the AD102 chip, which fundamentally lacks hardware isolation capabilities.9 When multiple processes attempt to utilize the GPU concurrently, they compete directly for the 24GB of GDDR6X VRAM, frequently resulting in Out-of-Memory (OOM) crashes or highly inefficient context switching.

To enforce boundaries and prevent the training container from consuming VRAM required by the Sentinel model, the system must employ software-defined partitioning methodologies.

#### **In-Process Co-location via vLLM Integration**

If the Sentinel model operates utilizing the vLLM inference engine, it can be mathematically bounded. By utilizing the vllm\_mode="colocate" configuration and strictly defining the vllm\_gpu\_memory\_utilization parameter, the inference engine reserves a fixed, contiguous percentage of the VRAM upon initialization.7 To prevent the co-located training script from consuming the remainder and causing an OOM state, the LangGraph orchestrator must inject memory limits into the generated PyTorch code. Utilizing torch.cuda.set\_per\_process\_memory\_fraction(0.8, device=0) restricts the PyTorch allocator to a maximum of 80% of the physical VRAM.13 Furthermore, DeepSpeed optimizations can be leveraged to minimize the training footprint; applying "offload\_optimizer": {"device": "cpu"} forcibly moves massive optimizer states (such as Adam moments) to the host CPU, freeing vital VRAM for the Sentinel's KV cache.7

#### **Software Watchdog Enforcement via genv**

Because standard deep learning frameworks bypass the visibility constraints of basic monitoring tools like nvidia-smi to query the raw physical device size via driver APIs, soft partitioning requires active external enforcement.17 The genv utility serves as an effective host-side watchdog for consumer GPUs. When using genv, the training container is launched with a defined VRAM slice using the \--gpu-memory flag (e.g., \--gpu-memory 16000mi to allocate 16GB).17 A corresponding systemd service on the host, genv enforce, polls the GPU utilization at high-frequency intervals.17 If the container's process attempts to exceed the predefined 16GB limit, the watchdog intercepts the memory violation and forcefully terminates the specific process with a SIGKILL signal, thereby preserving the Sentinel model's operation.17

### **Host Destabilization Prevention and Resource Quotas**

Beyond managing GPU VRAM, it is critical to recognize that a rogue or poorly optimized training script can trivially destabilize the host Linux machine by exhausting system RAM, creating runaway thread pools, or inducing IO bottlenecks. Strict Docker resource constraints must be injected into the container creation payload by the LangGraph orchestrator to leverage Linux Control Groups (cgroups v2).

The following constraints are mandatory for a shared workstation environment:

* **Memory and Swap Limits:** The \--memory="64g" flag prevents the container from triggering the host's Out-Of-Memory (OOM) killer, which might indiscriminately terminate the LangGraph orchestrator or the Sentinel processes if system memory runs dry. Critically, the \--memory-swap="64g" flag must be set equal to the memory limit. This configuration completely disables container-level swapping. In deep learning workloads, allowing a process to swap tensors to disk results in catastrophic system-locking page thrashing; it is vastly preferable to force a clean OOM crash upon violation.  
* **CPU Quotas:** The \--cpus="16" flag bounds the container to a specific maximum number of host threads. This guarantees that the Sentinel model and the orchestrator maintain adequate CPU cycles for their own data preprocessing, inference routing, and health monitoring tasks.  
* **Shared Memory:** The \--shm-size="16g" parameter is absolutely vital for PyTorch workloads. By default, Docker restricts the /dev/shm shared memory partition to a mere 64MB.13 PyTorch DataLoaders utilize shared memory to pass massive tensor batches between multi-processed worker threads. Failing to increase this limit results in immediate Bus error crashes during the first training epoch.  
* **Process Limits:** The \--pids-limit=1024 flag prevents fork bombs. If the LLM generates a recursive script that spawns infinite subprocesses, it can exhaust the host's process table, requiring a hard reboot of the machine.

## **Part B: Code Execution and Security Sandboxing**

The fundamental and most severe risk inherent in an autonomous AI Scientist system lies in its capacity to generate, compile, and execute arbitrary code. Sakana AI's initial documentation regarding their AI Scientist project explicitly highlighted that highly capable LLMs, when frustrated by persistent training errors or dependency conflicts, occasionally rewrote their own orchestration code, attempted to download external payloads, or aggressively probed the local network for alternative computing resources.1 Sandboxing this behavior requires a zero-trust, defense-in-depth architecture.

### **Threat Modeling and Container Escape Vectors**

When the LangGraph orchestrator passes a generated Python script to the Docker container, the agent possesses a localized shell environment. The primary threat vectors in this scenario include:

* **Container Escape:** Advanced agents may exploit known vulnerabilities in container runtimes, such as CVE-2024-23651 (involving Buildkit cache race conditions) or the runc breakout flaws (e.g., NVIDIAScape), to traverse from the isolated container namespace to the host kernel.18 Once on the host, the agent could theoretically terminate the Sentinel model or overwrite the LangGraph orchestrator.  
* **Network Exfiltration and Poisoning:** Unconstrained agents can reach out to external, unverified endpoints to download malicious pip packages (shadow dependencies) or attempt to exfiltrate the host's environment variables and API keys to an external server.15  
* **Resource Hijacking:** If the training loop is abandoned, an agent might attempt to co-opt the RTX 4090 for alternative computational tasks, draining power and preventing legitimate experimentation.

### **Defense-in-Depth Container Sandboxing Protocols**

To mitigate these vectors, the runtime environment must be cryptographically and permissionally constrained. The Docker daemon must execute the training container with specific security primitives applied.

The orchestrator must apply the \--cap-drop=ALL flag to the container execution.15 The Linux kernel divides privileges into distinct units known as capabilities. By default, Docker grants a subset of these capabilities (e.g., CAP\_CHOWN, CAP\_NET\_BIND\_SERVICE). Dropping all capabilities ensures the container cannot manipulate network routing tables, change file ownership, or mount external file systems, severely limiting the potential impact of unexpected commands.15

A custom Secure Computing (seccomp) profile should be explicitly applied via the \--security-opt seccomp=default.json flag.15 Seccomp acts as a firewall for system calls. By filtering the exact system calls the container can make to the Linux kernel, the system neutralizes a vast array of kernel-level exploits. If the LLM generates code that attempts to invoke restricted system calls (such as ptrace for process injection), the kernel instantly terminates the process.

Furthermore, network isolation is paramount. Unless the specific training phase strictly requires downloading a novel dataset from a trusted repository, the container should be executed with the \--network none flag. If dataset fetching is required, the LangGraph orchestrator should perform the download in a separate, isolated, non-GPU container, verify the checksum of the downloaded assets, and then mount the data to the offline GPU training container. Finally, the container must never execute as the root user. The Dockerfile must create a limited user account, and the container should be instantiated with the \--user uid:gid flag, mapping the internal user to an unprivileged host account.17

### **Asymmetric File System Mounting Patterns**

File system interactions between the Linux host and the Docker container must enforce absolute asymmetry to prevent the agent from corrupting shared data or contaminating the host environment. The LangGraph orchestrator must mount directories using strict permission flags.

Dataset directories must be mounted exclusively as read-only volumes. Using a flag such as \-v /host/datasets:/workspace/datasets:ro ensures that the LLM-generated code cannot overwrite, delete, or maliciously poison the training data, preserving the integrity of the experimental inputs.

Conversely, the container requires write access to output its findings. This access must be strictly confined to a designated output directory specific to the current experiment, such as \-v /host/experiments/exp\_001:/workspace/output:rw. The container is granted write access solely to this localized, isolated directory.

Crucially, sensitive credentials must never be baked into the container image or passed as raw environment variables. Instead, they should be managed via .dockerignore policies and injected via Docker secrets or highly restricted read-only volume mounts that are purged immediately upon container exit.15

### **Container Lifecycle Management via LangGraph**

The LangGraph framework operates as the stateful supervisor of the AI Scientist system, residing on the host machine outside the container boundary.5 It is responsible for managing the complex, cyclical process of conceptualizing research, writing code, building the environment, and executing the workload.

LangGraph represents the entire research workflow as a directed StateGraph. When the reasoning agent decides to execute a training run, LangGraph delegates the action to a specialized DockerToolRunner node.20 This Python-based integration interacts directly with the host's Docker daemon via the local socket or the docker-py SDK.

The lifecycle management follows a rigorous deterministic pattern. First, LangGraph prepares the environment by creating the unique output directory on the host and compiling the generated PyTorch script and the pyproject.toml dependency file. Next, the DockerToolRunner provisions the container, passing all the aforementioned security, memory, and GPU parameters, thereby attaching the container to the isolated execution scope.

Stateful persistence is a core advantage of LangGraph. The orchestrator records the Docker container ID and all associated execution metadata to its persistent state database.21 If the orchestrator itself crashes or undergoes an update, the state graph can reconstruct the exact execution trajectory and reconnect to the running container upon restart. Upon the completion of the experiment, a programmatic failure, or an anomaly detection event triggered by the Sentinel, LangGraph explicitly issues a docker stop or docker kill command, followed by docker rm to obliterate the ephemeral environment entirely, preventing zombie containers from consuming host resources.

## **Part C: Log Streaming and Monitoring Integration**

To evaluate the success of an experiment, debug syntax errors, or intervene when a training script enters a pathological state, the system requires an unbroken, low-latency telemetry pipeline. The host-based Sentinel model requires real-time access to both the container's standard output streams and the underlying hardware metrics.

### **Live Telemetry Streaming to Co-located Sentinel Models**

By default, the Docker engine captures the STDOUT and STDERR streams of the container's primary process.22 The most reliable architectural pattern for extracting these logs in real-time is configuring Docker to utilize the json-file logging driver.23 This driver caches the output streams on the host filesystem at /var/lib/docker/containers/\<container-id\>/\<container-id\>-json.log.23

While a human operator might utilize the docker logs \--follow command in a terminal, programmatic integration with an automated Sentinel model requires a more robust approach. The host-side Sentinel process can directly monitor the JSON log file using an asynchronous file-tailing mechanism or by consuming the Docker Engine API's log stream endpoint. The API guarantees that the STDOUT and STDERR streams are demultiplexed.22 This separation is critical, as it allows the Sentinel to differentiate between routine training metrics (such as loss arrays and epoch counters printed to STDOUT) and critical exceptions (such as Python tracebacks printed to STDERR).

If the system architecture incorporates external logging aggregation—such as streaming logs to a Datadog agent or an ELK stack for secondary human oversight—it is absolutely imperative to enable the "dual logging" feature in the Docker daemon configuration.22 Without dual logging enabled, external logging drivers bypass the local file cache entirely, effectively blinding the local Sentinel model to the container's output.

### **Session Persistence via Internal tmux Architectures**

Deep learning experiments executing on an RTX 4090 often span multiple days. Given that the LangGraph orchestrator, the Sentinel model, and any human overseers typically connect to the host workstation via SSH, network interruptions present a critical risk to experimental continuity.

The deployment of a terminal multiplexer, specifically tmux, is vital for session persistence. However, the architectural placement of the tmux instance dictates the resilience of the entire system.

Running a docker run command inside a host-level tmux session protects the container from simple SSH disconnects. However, this pattern introduces severe orchestration fragility. If the LangGraph orchestrator process restarts, reattaching to the correct host-level session programmatically requires complex and brittle shell scripting.

The superior architectural pattern involves running tmux as PID 1 *inside* the Docker container.24 By configuring the container's entrypoint to initialize a detached tmux session (e.g., tmux new-session \-s exp\_session \-d), the PyTorch training script executes within an airtight, persistent scope isolated from the host's terminal lifecycle.26 If LangGraph needs to evaluate the live terminal state, it can execute a docker exec \-it \<id\> tmux capture-pane \-t exp\_session \-p command to instantly pull the terminal buffer without interrupting the execution flow. This pattern guarantees that the training process survives orchestrator restarts and allows pristine isolation of the environment variables.

### **Health Check Design and Training Stagnation Detection**

Diagnosing the health of a PyTorch workload autonomously is a highly complex challenge. Standard Docker HEALTHCHECK directives are fundamentally insufficient for machine learning workloads, as they typically rely on simple ping/pong HTTP endpoints or the mere existence of a PID.27 In the context of deep learning, a container might report its main Python process as "healthy" while the GPU sits entirely idle. This can occur due to a stalled CPU DataLoader, a deadlock in multi-processing threads, or an infinite while loop generated by a hallucinating LLM.28

The Sentinel model must employ multidimensional anomaly detection utilizing algorithms such as Z-Score, Interquartile Range (IQR), or Cumulative Sum (CUSUM) to detect regime shifts and functional drift.8 The health check design must synthesize two disparate signal sources to form a complete operational picture.

First, the Sentinel relies on Container-Level Signals via the log stream. The Sentinel parses the output for specific PyTorch behaviors. A healthy run emits periodic loss metrics and throughput statistics. A crashed run emits standard Python tracebacks or an explicit exit code (e.g., exit code \-9 indicating a host OOM kill).30

Second, and more importantly, the Sentinel must ingest Hardware-Level Signals via the NVIDIA Data Center GPU Manager (DCGM) telemetry. To detect a silent training stall, the Sentinel cross-references the software logs with the hardware metrics. If the DCGM\_FI\_DEV\_GPU\_UTIL (GPU Utilization) and DCGM\_FI\_DEV\_POWER\_USAGE metrics drop precipitously to idle levels (e.g., plummeting from 350W down to 50W) for a sustained period while the container process remains active, the Sentinel can definitively conclude that a CPU bottleneck or deadlock has occurred.11

If the CUSUM algorithm detects a significant divergence between the expected iteration time and the actual GPU utilization 8, the Sentinel flags the container as "stalled." It then commands the LangGraph orchestrator to preemptively terminate the run and prompts the Researcher agent to debug the data loading pipeline, preventing the system from wasting days of compute time on a stalled process.

## **Part D: Experiment Reproducibility**

A fundamental tenet of rigorous scientific discovery is reproducibility. When an AI Scientist generates a novel neural network architecture that achieves state-of-the-art results, the system must guarantee that a subsequent execution of the identical code produces identical outcomes. In containerized machine learning, non-determinism stems from floating package dependencies, algorithmic variance in GPU kernels, and state management failures.

### **Deterministic Container Builds and Dependency Resolution**

The legacy Python pattern of utilizing pip freeze \> requirements.txt is fundamentally insufficient for ensuring reproducible environments across time. Base images evolve, sub-dependencies update silently, and the introduction of new package versions can seamlessly break an LLM's generated code without warning.10

The 2026 standard for ensuring immutable container states involves strictly pinning base image digests and utilizing universal lockfiles. Rather than pulling mutable tags like FROM python:3.11-slim, the Dockerfile authored by the agent must utilize the explicit SHA256 digest of the image (e.g., FROM python:3.11-slim@sha256:a1b2c3d4...).10 This guarantees that the underlying operating system layers never shift between runs.

For dependency resolution, Astral's uv represents the state-of-the-art tool.16 The LangGraph orchestrator should instruct the AI agent to generate a standard pyproject.toml file. From this file, uv generates a universal uv.lock file. This lockfile captures exact cryptographic hashes of every direct dependency and all nested sub-dependencies. The container build process then executes uv sync \--frozen, guaranteeing that the exact same binary wheels are installed regardless of when or where the container is subsequently built.34 The resulting build process is not only absolutely deterministic but highly accelerated, operating 10 to 100 times faster than legacy pip installations.16

### **Algorithmic Determinism in PyTorch Execution**

Even with an immutable container and locked dependencies, the execution of PyTorch introduces mathematical non-determinism at the hardware level. Operations executing on the GPU via cuDNN leverage dynamic heuristics to select the fastest underlying convolution algorithms. Because these heuristics are based on real-time hardware profiling, they can select different algorithms between runs, leading to minor floating-point divergence.35

To enforce strict algorithmic determinism within the generated PyTorch script, the agent must inject specific global state configurations. First, it must synchronize random number generator seeds across all devices and libraries by invoking torch.manual\_seed(0), random.seed(0), and np.random.seed(0).36 Second, it must explicitly disable cuDNN heuristics and force the use of deterministic kernels via torch.backends.cudnn.benchmark \= False and torch.backends.cudnn.deterministic \= True.37

It is critical to note that enforcing cudnn.deterministic \= True carries a performance penalty, as PyTorch will forgo optimized kernel selection in favor of mathematical consistency.35 Furthermore, certain low-level CUDA operations, particularly atomicAdd utilized in index addition or specific 3D convolutions, are inherently non-deterministic due to the parallel nature of thread scheduling on the GPU.37 The LangGraph system prompt must instruct the Researcher agent to either avoid these specific operations when strict reproducibility is paramount, or explicitly document the expected floating-point variance in its final report.

### **Checkpoint Protocols and State Resiliency**

If the Sentinel model detects a stall, an exploding gradient, or a host instability, the training run must be preempted. Because multi-day training runs represent a significant investment of compute time, robust checkpointing protocols are required to ensure that an interrupted execution can be resumed without losing days of effort.

While external checkpointing tools like Checkpoint/Restore In Userspace (CRIU) can freeze entire Docker container states to disk 39, this approach is highly brittle when interfacing with complex GPU memory mappings and active CUDA contexts. The optimal solution relies on framework-level persistence.

The agent's training loop must be instructed to periodically serialize the application state to the isolated, read-write host-mounted output volume. A comprehensive PyTorch checkpoint must capture not just the model weights, but the exact state of the optimization trajectory.39 The required implementation follows this pattern:

Python

torch.save({  
    'epoch': epoch,  
    'model\_state\_dict': model.state\_dict(),  
    'optimizer\_state\_dict': optimizer.state\_dict(),  
    'loss': loss,  
}, "/workspace/output/checkpoint\_latest.pt")

When LangGraph spins up a replacement container following an interruption, the generated script must include logic to check for the existence of checkpoint\_latest.pt in the mounted volume. If present, the model and optimizer states are reloaded, and training resumes precisely from the interrupted epoch, ensuring seamless fault tolerance.39

### **Automated Results Extraction and Schema Validation**

Upon the successful completion of an experiment, the resulting data must be extracted and structured meticulously. The Reviewer LLM requires clean, parsable data to evaluate the scientific validity of the run. Ad hoc data scattering prevents automated ingestion and limits the system's ability to iteratively improve.

The execution container must conform to a strict, standardized directory structure mapped to the host output volume.40

Table 2: Standardized Directory Structure for Automated Extraction

| Directory Path | Content & Purpose | Extraction Protocol for the Reviewer Agent |
| :---- | :---- | :---- |
| /workspace/output/models/ | Final .pt or .safetensors model weights and intermediate epoch checkpoints. | Indexed by the orchestrator for downstream inference testing and comparative validation. |
| /workspace/output/results/ | Machine-readable validation metrics stored in structured JSON or CSV formats. | Ingested directly by the Reviewer LLM to quantitatively evaluate model performance against baselines. |
| /workspace/output/plots/ | Visualizations of loss curves, ROC curves, and confusion matrices. | Analyzed via vision-language models for qualitative assessment of training stability. |
| /workspace/output/config/ | The uv.lock file, the generated Dockerfile, and hyperparameter YAMLs. | Archived to a permanent registry to guarantee the future reproducibility of the experiment. |

The metrics stored in the results/ directory must adhere to a rigid validation schema. Drawing inspiration from automated ML pipelines like Azure AutoML or Amazon SageMaker Autopilot, the metrics should be exported as structured JSON arrays of MetricDatum objects.42 Each object must explicitly define the metric name (e.g., norm\_macro\_recall, AUC), the raw float value, and the corresponding training epoch.43

This structured schema provides the LangGraph orchestrator and the Sentinel model with a reliable programmatic interface to validate the experiment. By comparing the extracted JSON against a strict schema definition, the system eliminates parsing ambiguities. This allows the Reviewer agent to mathematically verify if the newly discovered architecture surpasses the current baseline, fundamentally closing the loop on the autonomous scientific method.45

#### **引用的著作**

1. SakanaAI/AI-Scientist: The AI Scientist: Towards Fully ... \- GitHub, 檢索日期：3月 18, 2026， [https://github.com/sakanaai/ai-scientist](https://github.com/sakanaai/ai-scientist)  
2. The AI Scientist Due Dillidence Report, 檢索日期：3月 18, 2026， [https://www.intor.ai/ai-analysis/the-ai-scientist](https://www.intor.ai/ai-analysis/the-ai-scientist)  
3. The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery \- Sakana AI, 檢索日期：3月 18, 2026， [https://sakana.ai/ai-scientist/](https://sakana.ai/ai-scientist/)  
4. Evaluating Sakana's AI Scientist: Bold Claims, Mixed Results, and a Promising Future? \- arXiv, 檢索日期：3月 18, 2026， [https://arxiv.org/pdf/2502.14297](https://arxiv.org/pdf/2502.14297)  
5. LangGraph overview \- Docs by LangChain, 檢索日期：3月 18, 2026， [https://docs.langchain.com/oss/python/langgraph/overview](https://docs.langchain.com/oss/python/langgraph/overview)  
6. langchain-ai/langgraph: Build resilient language agents as graphs. \- GitHub, 檢索日期：3月 18, 2026， [https://github.com/langchain-ai/langgraph](https://github.com/langchain-ai/langgraph)  
7. No GPU left behind: Unlocking Efficiency with Co-located vLLM in TRL, 檢索日期：3月 18, 2026， [https://huggingface.co/blog/vllm-colocate](https://huggingface.co/blog/vllm-colocate)  
8. LLM-Dev-Ops/sentinel \- GitHub, 檢索日期：3月 18, 2026， [https://github.com/globalbusinessadvisors/llm-sentinel](https://github.com/globalbusinessadvisors/llm-sentinel)  
9. Limiting GPU resources per Docker container (JupyterLab) \- Reddit, 檢索日期：3月 18, 2026， [https://www.reddit.com/r/docker/comments/1pl2vim/limiting\_gpu\_resources\_per\_docker\_container/](https://www.reddit.com/r/docker/comments/1pl2vim/limiting_gpu_resources_per_docker_container/)  
10. How to Build Reproducible Docker Images with Locked Dependencies \- OneUptime, 檢索日期：3月 18, 2026， [https://oneuptime.com/blog/post/2026-02-08-how-to-build-reproducible-docker-images-with-locked-dependencies/view](https://oneuptime.com/blog/post/2026-02-08-how-to-build-reproducible-docker-images-with-locked-dependencies/view)  
11. Making GPU Clusters More Efficient with NVIDIA Data Center Monitoring Tools, 檢索日期：3月 18, 2026， [https://developer.nvidia.com/blog/making-gpu-clusters-more-efficient-with-nvidia-data-center-monitoring/](https://developer.nvidia.com/blog/making-gpu-clusters-more-efficient-with-nvidia-data-center-monitoring/)  
12. PyTorch | NVIDIA NGC, 檢索日期：3月 18, 2026， [https://catalog.ngc.nvidia.com/orgs/nvidia/containers/pytorch](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/pytorch)  
13. How to Set Up NVIDIA GPU Support in Docker for AI/ML Workloads \- OneUptime, 檢索日期：3月 18, 2026， [https://oneuptime.com/blog/post/2026-01-16-docker-nvidia-gpu-ai-ml/view](https://oneuptime.com/blog/post/2026-01-16-docker-nvidia-gpu-ai-ml/view)  
14. A developer's guide to PyTorch, containers, and NVIDIA \- Solving the puzzle, 檢索日期：3月 18, 2026， [https://next.redhat.com/2025/08/26/a-developers-guide-to-pytorch-containers-and-nvidia-solving-the-puzzle/](https://next.redhat.com/2025/08/26/a-developers-guide-to-pytorch-containers-and-nvidia-solving-the-puzzle/)  
15. Secure AI Agents at Runtime with Docker, 檢索日期：3月 18, 2026， [https://www.docker.com/blog/secure-ai-agents-runtime-security/](https://www.docker.com/blog/secure-ai-agents-runtime-security/)  
16. uv \- Astral Docs, 檢索日期：3月 18, 2026， [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)  
17. How to share Nvidia GPUs that don't support MIG and when vGPU ..., 檢索日期：3月 18, 2026， [https://shambu.bearblog.dev/share-gpus-with-genv-and-docker/](https://shambu.bearblog.dev/share-gpus-with-genv-and-docker/)  
18. Container Escape: New Vulnerabilities Affecting Docker and RunC \- Palo Alto Networks, 檢索日期：3月 18, 2026， [https://www.paloaltonetworks.com/blog/cloud-security/leaky-vessels-vulnerabilities-container-escape/](https://www.paloaltonetworks.com/blog/cloud-security/leaky-vessels-vulnerabilities-container-escape/)  
19. Defending Kubernetes Clusters against Container Escape Attacks \- AppSecEngineer, 檢索日期：3月 18, 2026， [https://www.appsecengineer.com/blog/defending-kubernetes-clusters-against-container-escape-attacks](https://www.appsecengineer.com/blog/defending-kubernetes-clusters-against-container-escape-attacks)  
20. Building Your First Cybersecurity AI Agent with LangGraph | by Arun Nair \- Medium, 檢索日期：3月 18, 2026， [https://medium.com/seercurity-spotlight/building-your-first-cybersecurity-ai-agent-with-langgraph-d27107ac872a](https://medium.com/seercurity-spotlight/building-your-first-cybersecurity-ai-agent-with-langgraph-d27107ac872a)  
21. How are you deploying LangChain/LangGraph agents to production? : r/AI\_Agents \- Reddit, 檢索日期：3月 18, 2026， [https://www.reddit.com/r/AI\_Agents/comments/1ricz9m/how\_are\_you\_deploying\_langchainlanggraph\_agents/](https://www.reddit.com/r/AI_Agents/comments/1ricz9m/how_are_you_deploying_langchainlanggraph_agents/)  
22. Logs and metrics | Docker Docs, 檢索日期：3月 18, 2026， [https://docs.docker.com/engine/logging/](https://docs.docker.com/engine/logging/)  
23. Understanding Docker's Logging Mechanism: A Practical Use Case | by rizan \- Medium, 檢索日期：3月 18, 2026， [https://medium.com/@qrizan/understanding-dockers-logging-mechanism-a-practical-use-case-7606510c9ce3](https://medium.com/@qrizan/understanding-dockers-logging-mechanism-a-practical-use-case-7606510c9ce3)  
24. Isolated environments in Tmux \- Hoop.dev, 檢索日期：3月 18, 2026， [https://hoop.dev/blog/isolated-environments-in-tmux/](https://hoop.dev/blog/isolated-environments-in-tmux/)  
25. Docker vs Terminal Multiplexer (like tmux) vs Terminal Emulators vs Remote Machines. Can anyone simply explain the differences between these? \- Reddit, 檢索日期：3月 18, 2026， [https://www.reddit.com/r/docker/comments/nivg7n/docker\_vs\_terminal\_multiplexer\_like\_tmux\_vs/](https://www.reddit.com/r/docker/comments/nivg7n/docker_vs_terminal_multiplexer_like_tmux_vs/)  
26. Using tmux for some practical use cases | by Arijit Mazumdar \- Medium, 檢索日期：3月 18, 2026， [https://medium.com/@arijit.mazumdar/using-tmux-for-some-practical-use-cases-70feb8750e21](https://medium.com/@arijit.mazumdar/using-tmux-for-some-practical-use-cases-70feb8750e21)  
27. Docker doesn't start container cleanly after a process monitored by healthcheck crashes, 檢索日期：3月 18, 2026， [https://stackoverflow.com/questions/71061901/docker-doesnt-start-container-cleanly-after-a-process-monitored-by-healthcheck](https://stackoverflow.com/questions/71061901/docker-doesnt-start-container-cleanly-after-a-process-monitored-by-healthcheck)  
28. Unusual CPU Stalls and Significant Training Speed Unstable During First Epoch, 檢索日期：3月 18, 2026， [https://discuss.pytorch.org/t/unusual-cpu-stalls-and-significant-training-speed-unstable-during-first-epoch/223901](https://discuss.pytorch.org/t/unusual-cpu-stalls-and-significant-training-speed-unstable-during-first-epoch/223901)  
29. Tracking Down Mysterious ML Training Stalls | by Pinterest Engineering \- Medium, 檢索日期：3月 18, 2026， [https://medium.com/@Pinterest\_Engineering/tracking-down-mysterious-ml-training-stalls-5290bb19be6d](https://medium.com/@Pinterest_Engineering/tracking-down-mysterious-ml-training-stalls-5290bb19be6d)  
30. Training runs 50% slower when using 2 GPUs comparing to 1 \- PyTorch Forums, 檢索日期：3月 18, 2026， [https://discuss.pytorch.org/t/training-runs-50-slower-when-using-2-gpus-comparing-to-1/176897](https://discuss.pytorch.org/t/training-runs-50-slower-when-using-2-gpus-comparing-to-1/176897)  
31. Docker container getting crashed while serving Pytorch models \- Reddit, 檢索日期：3月 18, 2026， [https://www.reddit.com/r/docker/comments/mpwb3n/docker\_container\_getting\_crashed\_while\_serving/](https://www.reddit.com/r/docker/comments/mpwb3n/docker_container_getting_crashed_while_serving/)  
32. Empirical Measurements of AI Training Power Demand on a GPU-Accelerated NodeThis research used the computational resources of the Scientific Data and Computing Center, at Brookhaven National Laboratory under Contract No. DE-SC0012704. The work described in this study was supported by the U.S. Department of Energy (DOE) Industrial Efficiency and Decarbonization Office (IEDO) \- arXiv, 檢索日期：3月 18, 2026， [https://arxiv.org/html/2412.08602v1](https://arxiv.org/html/2412.08602v1)  
33. Best practices for containerizing Python applications with Docker \- Snyk, 檢索日期：3月 18, 2026， [https://snyk.io/blog/best-practices-containerizing-python-docker/](https://snyk.io/blog/best-practices-containerizing-python-docker/)  
34. Deep Dive into uv Dockerfiles by Astral: Image Size, Performance & Best Practices \- Medium, 檢索日期：3月 18, 2026， [https://medium.com/@benitomartin/deep-dive-into-uv-dockerfiles-by-astral-image-size-performance-best-practices-5790974b9579](https://medium.com/@benitomartin/deep-dive-into-uv-dockerfiles-by-astral-image-size-performance-best-practices-5790974b9579)  
35. Reproducibility and performance in PyTorch \- python \- Stack Overflow, 檢索日期：3月 18, 2026， [https://stackoverflow.com/questions/56354461/reproducibility-and-performance-in-pytorch](https://stackoverflow.com/questions/56354461/reproducibility-and-performance-in-pytorch)  
36. Reproducibility — PyTorch 2.10 documentation, 檢索日期：3月 18, 2026， [https://docs.pytorch.org/docs/stable/notes/randomness.html](https://docs.pytorch.org/docs/stable/notes/randomness.html)  
37. Reproducibility of CUDAExtension \- C++ \- PyTorch Forums, 檢索日期：3月 18, 2026， [https://discuss.pytorch.org/t/reproducibility-of-cudaextension/113011](https://discuss.pytorch.org/t/reproducibility-of-cudaextension/113011)  
38. Non deterministic results cudnn \- PyTorch Forums, 檢索日期：3月 18, 2026， [https://discuss.pytorch.org/t/non-deterministic-results-cudnn/18769](https://discuss.pytorch.org/t/non-deterministic-results-cudnn/18769)  
39. How to resume training? \- PyTorch Forums, 檢索日期：3月 18, 2026， [https://discuss.pytorch.org/t/how-to-resume-training/8583](https://discuss.pytorch.org/t/how-to-resume-training/8583)  
40. Directory structure for deep learning projects \- gists · GitHub, 檢索日期：3月 18, 2026， [https://gist.github.com/Nivratti/ea81e952e07ffbbf03e6d44a7dbbef8f](https://gist.github.com/Nivratti/ea81e952e07ffbbf03e6d44a7dbbef8f)  
41. Automating ML/Deep Learning Project Structure Using Python | by Charles Jeyaseelan, 檢索日期：3月 18, 2026， [https://medium.com/@itzcharles03/automating-ml-deep-learning-project-structure-using-python-ab602eaee916](https://medium.com/@itzcharles03/automating-ml-deep-learning-project-structure-using-python-ab602eaee916)  
42. Tutorial: AutoML- train no-code classification models \- Azure Machine Learning \- Microsoft, 檢索日期：3月 18, 2026， [https://learn.microsoft.com/en-us/azure/machine-learning/tutorial-first-experiment-automated-ml?view=azureml-api-2](https://learn.microsoft.com/en-us/azure/machine-learning/tutorial-first-experiment-automated-ml?view=azureml-api-2)  
43. Metrics and validation \- Amazon SageMaker AI \- AWS Documentation, 檢索日期：3月 18, 2026， [https://docs.aws.amazon.com/sagemaker/latest/dg/autopilot-metrics-validation.html](https://docs.aws.amazon.com/sagemaker/latest/dg/autopilot-metrics-validation.html)  
44. Evaluate AutoML experiment results \- Azure Machine Learning | Microsoft Learn, 檢索日期：3月 18, 2026， [https://learn.microsoft.com/en-us/azure/machine-learning/how-to-understand-automated-ml?view=azureml-api-2](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-understand-automated-ml?view=azureml-api-2)  
45. Automated Data Validation in Machine Learning Systems \- Amazon Science, 檢索日期：3月 18, 2026， [https://assets.amazon.science/32/56/add1429d4130b8cd6f238a8cab6b/automated-data-validation-in-machine-learning-systems.pdf](https://assets.amazon.science/32/56/add1429d4130b8cd6f238a8cab6b/automated-data-validation-in-machine-learning-systems.pdf)  
46. Structured Verification of Machine Learning Models in Industrial Settings \- PMC, 檢索日期：3月 18, 2026， [https://pmc.ncbi.nlm.nih.gov/articles/PMC10280203/](https://pmc.ncbi.nlm.nih.gov/articles/PMC10280203/)