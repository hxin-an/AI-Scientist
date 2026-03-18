# Knowledge Base 05: Claude Harness Design Patterns (2025–2026)

> Source: Gemini Deep Research, 2026-03-18
> Purpose: Design reference for Claude agent harness and multi-agent communication

---

## Key Decisions Derived from This Research

### Tool Schema 設計

| 原則 | 做法 |
|------|------|
| 合併相關工具 | 用 `action` 參數整合（e.g., `filesystem.action = read/write/delete`）|
| 定義負邊界 | 明確寫出「此工具不提供什麼」，防止 over-triggering |
| 高訊號過濾 | tool result 回傳前過濾掉 DB ID、多餘 metadata |
| 語意命名空間 | `github_create_pr` 而非 `create_pr`，防止 multi-agent 衝突 |
| 驗證層 | Plan-Then-Execute：先輸出計畫 → validation node 檢查 → 再執行 |

### Tool Result 截斷策略

| 情境 | 策略 |
|------|------|
| 大型結構化資料 | Programmatic Tool Calling：Claude 寫過濾腳本，只回傳摘要 |
| 大型 log/terminal 輸出 | Proxy Middleware：快取完整輸出，回傳 header + tail + error summary + retrieval ID |
| 實驗結果 JSON | Artifact Offloading：存到磁碟，只傳路徑給 Claude |

### System Prompt 架構

| Agent | 核心指令 | Tool 存取 |
|-------|---------|----------|
| **Planner** | 分解任務、更新 Markdown 進度、不直接執行代碼 | 子 agent 喚醒、Filesystem write（tracking only）|
| **Researcher** | 最大化平行 tool calls、輸出寫到磁碟（不寫到 chat history）| 廣泛讀寫、web search、code execution |
| **Reviewer** | 只讀、嚴格 rubric、輸出結構化 rejection（不能模糊批評）| 嚴格唯讀、syntax checker |

**Constraint 注入方式**：
- 用 XML tags 包裹不可違反的規則（Claude 的 attention 對 XML 有優化）
- 規則放在 prompt 的**最開頭和最結尾**（primacy + recency bias）
- 長對話中定期重新注入核心規則

**動態 Context**：每次 cycle 開始時注入 git status + diff + progress file，不依賴靜態長 prompt

### Multi-Agent 溝通

**Handoff 格式**（Planner → Researcher）：
```
傳遞：子目標定義 + 完成標準 + 相關檔案路徑指標
不傳遞：Planner 的完整對話歷史
Researcher 自己讀檔案重建上下文
```

**Blackboard 模式**（共享記憶體）：

| 層 | 實作 | 用途 |
|----|------|------|
| Hot | LangGraph State object | 當前任務、即時 tool output |
| Warm | 本地 RAG vector store | 歷史 cycle 摘要、語意查詢 |
| Cold | MEMORY.md 檔案 | 架構決策、長期追蹤 |

**Oscillation 防護**：
- LangGraph state 追蹤每個 task 的 revision counter
- 超過上限 → Conciliator node 介入 → 強制 Planner 決定是否換方向

### Claude 特定優化

| 功能 | 使用時機 |
|------|---------|
| Extended Thinking (4k–8k token budget) | Planner 任務分解、Reviewer 深度分析、複雜 methodology 撰寫 |
| Thinking block 保留 | tool call 後必須原封不動傳回 thinking block，修改會導致 API error |
| 禁用 Extended Thinking | 簡單 log 解析、routing 決策等機械性節點 |

**架構選型**：
- **LangGraph 負責 macro 編排**（graph edges、state、supervisor）
- **Claude Agent SDK 在節點內部負責 micro 執行**（tool loop、compaction、retry）
- 兩者混合：不需從頭實作 tool execution loop，同時保持架構控制權

**Cost 管理**：
- 模型分層路由：Haiku → 簡單任務；Sonnet → 需要推理的任務
- Prompt caching：靜態 system prompt 放最頂部，工具列表順序必須固定（亂序會破壞 cache hash）
- Token-efficient tool use beta：開啟後大幅減少 tool-heavy workflow 的 output token

---

## Original Research Question and Full Answer

# Research Prompt: Claude Harness Design Patterns (2025–2026)

## Context

We are building a multi-agent AI Scientist system where Claude is the primary reasoning engine. The system uses LangGraph for orchestration, runs for multiple days, and coordinates three specialized agents: Planner, Researcher, and Reviewer. We need to understand the current best practices for designing the Claude "harness" — the scaffold that wraps Claude to make it reliable, efficient, and controllable in a long-running agentic context.

From prior research we know:
- LangGraph is the orchestration framework
- Multi-agent (separate Planner/Researcher/Reviewer) outperforms single-agent (~60% lower hallucination)
- 3-tier memory model (Hot/Warm/Cold)
- Git-centric state management
- Claude 3.7 Sonnet with Extended Thinking for complex tasks
- Tool-call counters and circuit breakers are needed

## What We Already Know

- Basic LangGraph patterns for state machines and cycles
- Claude Extended Thinking API exists (4k–8k token budget)
- Claude has native context pruning tools (clear_tool_uses, clear_thinking)

## Investigate

### Part A: Tool Design for Long-Running Agents

1. **Tool schema best practices**: What is the current best practice for designing Claude tool schemas in a long-running agentic pipeline? How should tools be described to minimize token usage while maximizing reliability? What common mistakes cause Claude to misuse tools?

2. **Idempotent tool design**: How do you design tools that are safe to retry without side effects? What patterns exist for making file I/O, SSH commands, and process management tools idempotent in a Claude harness?

3. **Tool result truncation**: When tool results are large (e.g., tmux log output, experiment results files), what is the recommended strategy for truncating or summarizing before returning to Claude? What information must be preserved vs. what can be discarded?

4. **Tool call validation**: What patterns exist for validating Claude's tool call arguments before execution — catching hallucinated file paths, invalid parameters, or dangerous commands before they reach the system?

### Part B: System Prompt Architecture

5. **System prompt structure for multi-agent systems**: How should system prompts be structured differently for a Planner agent vs. a Researcher agent vs. a Reviewer agent? What role-specific instructions are most critical for each?

6. **Dynamic system prompts**: In a long-running system where context evolves over days, should the system prompt be static or dynamically injected with current state summaries? What are the tradeoffs?

7. **Persona and constraint injection**: What is the most effective way to inject hard constraints (e.g., "never modify the Docker container base image", "always record metrics before marking complete") so that Claude reliably follows them even deep into a long conversation?

### Part C: Multi-Agent Communication

8. **Agent handoff protocols**: When the Planner hands off to the Researcher, what is the recommended format for the state package? How much context should be passed vs. reconstructed? What does a reliable handoff look like in LangGraph?

9. **Shared memory between agents**: In a multi-agent LangGraph system, how do agents share information without polluting each other's context windows? What patterns exist for a shared "blackboard" that all agents can read/write?

10. **Agent disagreement handling**: When the Reviewer rejects the Researcher's output and sends it back for revision, how should the revised context be structured? How do you prevent the Researcher from repeating the same mistake on the second attempt?

### Part D: Claude-Specific Optimizations

11. **Extended Thinking integration in LangGraph**: What is the recommended pattern for integrating Claude's Extended Thinking feature within a LangGraph node? When should it be enabled vs. disabled to balance cost and quality?

12. **claude-code SDK vs raw API**: Is there a meaningful difference between using the Claude Code SDK (claude_agent_sdk) vs. the raw Anthropic API for building a custom harness? What does the Claude Agent SDK provide that raw API calls don't?

13. **Cost management strategies**: For a system running for multiple days with multiple Claude wake-ups, what are the most effective strategies for minimizing API costs while maintaining task quality? Token budgeting, caching, model tier routing?

## Constraints

- Primary LLM: Claude (Anthropic) — must use Claude API or Claude Agent SDK
- Framework: LangGraph
- Must handle multi-day task durations
- Prefer production-validated patterns from 2024–2026


# **Architecting a Resilient Multi-Agent AI Scientist: Best Practices for Claude 3.7 Sonnet and LangGraph Integration**

The paradigm of artificial intelligence engineering has definitively shifted from model-centric prompt engineering to the design of sophisticated agent harnesses and context management systems. As large language models transition from stateless text generators into autonomous operational engines, the limiting factor in complex problem-solving is rarely the foundational intelligence of the model itself. Instead, the boundary of capability is defined by the resilience of the infrastructure surrounding it. Designing a multi-agent "AI Scientist" that operates autonomously over multi-day horizons requires an orchestration layer capable of mitigating context rot, scheduling failures, tool-induced state corruption, and compounded hallucination loops.1

When deploying an asynchronous, long-running agentic workflow utilizing LangGraph as the orchestration engine, the system functions analogously to a modern operating system. The Claude 3.7 Sonnet model acts as the central processing unit, the context window serves as the volatile random access memory, and the LangGraph harness operates as the operating system kernel, managing state transitions, memory paging, and hardware execution via tool calls.1 This architecture is particularly vital for research and scientific discovery, which involves open-ended problems where it is impossible to hardcode a fixed path for exploring complex topics.4 The multi-agent approach, specifically dividing labor into Planner, Researcher, and Reviewer roles, has been empirically shown to outperform single-agent configurations by up to ninety percent on internal research evaluations by separating concerns and parallelizing context windows.4

This comprehensive analysis exhausts the current best practices for designing a robust, production-ready Claude-centric harness. The investigation addresses the critical intersections of tool design for long-horizon stability, dynamic system prompt architecture, asynchronous multi-agent communication protocols, and Claude-specific optimizations designed to balance deep reasoning capabilities with strict cost management.

## **Part A: Tool Design for Long-Running Agentic Operations**

In an autonomous execution loop spanning multiple days, tools form the deterministic boundary between the probabilistic reasoning of the language model and the strict realities of the external environment.6 The design, validation, and schema architecture of these tools dictate whether an agent will successfully navigate a complex codebase or spiral into unrecoverable failure loops driven by context exhaustion and resource mismanagement.

### **Tool Schema Best Practices and Token Efficiency**

Claude 3.7 Sonnet requires meticulously crafted tool schemas to minimize token usage while maximizing execution reliability. The most critical factor in tool performance is the depth, clarity, and structural precision of the plaintext description provided within the JSON schema.7 A frequent cause of agent failure in long-running systems is tool over-triggering, where the model applies a tool to a problem it cannot solve or repeatedly calls a tool with hallucinatory parameters.9 To mitigate this, schemas must clearly articulate the expected return format and explicitly state the negative boundaries of the tool, informing the model exactly what information the tool does not provide.8

The consolidation of operations is a primary strategy for enhancing token efficiency. Rather than registering dozens of distinct, narrowly scoped tools, developers must group related operations into fewer, highly capable tools utilizing an action parameter.7 For example, instead of separate tools for creating, reading, and updating files, a single filesystem manager tool with specific action flags reduces the token overhead of the system prompt and simplifies the model's action-selection space. This approach must be paired with semantic namespacing, where tool names are prefixed with their service domain to prevent namespace collisions as the multi-agent system scales its tool library.7

Furthermore, tool responses must be engineered to return only high-signal information. Bloated internal identifiers, excessive metadata, or deeply nested JSON structures should be stripped by the execution wrapper before the payload is returned to the model.7 While rich descriptions carry the most weight in steering model behavior, complex tools with nested inputs or strict formatting requirements benefit significantly from the inclusion of schema-validated examples. These examples demonstrate valid parameter structures directly to the model, drastically reducing the incidence of malformed execution requests.7

| Schema Optimization Strategy | Implementation Design | Primary Impact on Agent Pipeline |
| :---- | :---- | :---- |
| Action Parameter Consolidation | Merge granular tools into centralized managers using action flags. | Reduces system prompt token bloat and simplifies the agent's decision matrix. |
| Negative Boundary Definition | Explicitly document what the tool cannot do and what data it lacks. | Prevents repetitive over-triggering and reduces hallucinated expectations. |
| High-Signal Filtering | Strip database IDs, raw timestamps, and redundant metadata from returns. | Preserves the context window for actual reasoning rather than data storage. |
| Semantic Namespacing | Use domain prefixes like github\_create\_pr instead of create\_pr. | Eliminates tool collision and ambiguity in multi-agent swarms. |

### **Idempotent Tool Design and Safe Execution**

A core failure mode in multi-day agentic runs is state mutation caused by failed, interrupted, or retried tool executions.11 If a Researcher agent attempts to execute a deployment script, experiences a network timeout, and autonomously retries the operation, a non-idempotent tool could corrupt the environment, duplicate database entries, or trigger cascading rate limits. Tools must be designed so that multiple identical requests yield the exact same system state as a single successful request.11

For file input/output, secure shell commands, and process management, declarative interfaces provide the highest level of safety. Tools should expose declarative commands that ensure a specific state is met, rather than imperative commands that blindly execute a mutation. This philosophy mirrors modern infrastructure-as-code principles, which are inherently safer for autonomous agents navigating unpredictable environments.13 When executing shell scripts, the tooling layer must wrap operations in guarded command patterns. This involves a test-and-action methodology where the tool programmatically verifies if the desired state already exists before executing the mutation, thereby preventing destructive overwrites.12

When idempotency is impossible to guarantee natively at the system level, tools must be engineered to return highly specific, standardized exit codes. Returning a distinct exit code for a "resource already exists" conflict allows the language model to programmatically recognize the state and proceed with its workflow, rather than interpreting the conflict as a critical failure that requires an entirely new problem-solving trajectory.13 Additionally, implementing execution sandboxes using isolated containers ensures that if an agent hallucinates a dangerous command, the blast radius is strictly confined to an ephemeral filesystem, protecting the host machine from catastrophic data loss.14

### **Tool Result Truncation and Context Preservation**

A ubiquitous challenge in long-running AI harnesses is the ingestion of massive tool outputs. When an agent requests a repository diagnostic or compiles a large project, the resulting terminal output can easily exceed tens of thousands of lines. Ingesting this raw data directly into the conversation history causes immediate context window saturation, inducing severe performance degradation and agent amnesia.15

To manage large tool outputs, sophisticated truncation and summarization strategies are mandated at the harness level. Programmatic Tool Calling represents a paradigm shift in this area. It allows the model to write and execute data-filtering scripts inside a secure sandbox before any output is returned to the context window. By delegating computational logic, such as searching through massive log files or aggregating statistical data, to the execution environment, the model receives only the synthesized insights, reducing token consumption by up to eighty-five percent.7

For scenarios where raw output must be captured, proxy truncation middleware is essential. A structural pattern involves inserting a truncation proxy between the tool execution layer and the language model. If a tool output exceeds a defined byte threshold, the proxy compresses the full payload to a local cache and returns only the file header, the tail, and a summary of any error codes to the model, alongside a persistent retrieval identifier. The agent is simultaneously provided with a secondary retrieval tool to fetch specific line ranges if deep inspection is subsequently required, ensuring that context is preserved only when explicitly demanded by the model's reasoning process.17

| Truncation Strategy | Mechanism | Optimal Use Case |
| :---- | :---- | :---- |
| Programmatic Tool Calling | Agent writes custom Python scripts to filter and aggregate data in a sandbox. | Large, structured datasets requiring mathematical aggregation or specific keyword extraction. |
| Proxy Middleware | Intercepts payloads over a specific threshold, caching the full file and returning a summary. | Terminal outputs, massive compiler error logs, and deep directory trees. |
| Artifact Offloading | Saves raw JSON to disk, passing only a file path and brief summary to the agent. | Experiment results and large web-scraped HTML payloads. |
| Automatic Compaction | Triggers a background LLM to summarize the entire conversation history when limits approach. | Multi-day conversational threads with excessive back-and-forth reasoning steps. |

### **Tool Call Validation and Execution Guardrails**

To prevent hallucinated file paths, invalid parameters, or dangerous commands from reaching the execution environment, validation must occur at the orchestrator level prior to tool invocation. Relying solely on system prompts to dictate safety is insufficient against model drift over a multi-day run, as the model's adherence to instructions wanes as the context window expands.18

Structural patterns like the Plan-Then-Execute architecture provide robust validation boundaries. In this model, the language model must first output a structured plan containing its intended tool calls and arguments without actually triggering them. An independent, lightweight validation node in the LangGraph workflow parses this plan against strict programmatic schemas. If the arguments contain invalid patterns, such as attempting directory traversal outside the project root, the validation node rejects the execution entirely and returns a structured error to the agent. This forces the model into a self-correction loop before it can interact with the actual operating system.19

Furthermore, implementing a reference monitor pattern ensures that fine-grained security policies are continuously attached to data flows. If an agent attempts to execute a command utilizing data that the system flags as untrusted or unverified, the execution wrapper intercepts the invocation and blocks it. This dual-layered approach to validation ensures that the multi-agent system remains secure and reliable even when individual agents exhibit unpredictable reasoning paths during complex investigations.19

## **Part B: System Prompt Architecture for Multi-Agent Systems**

In a multi-agent LangGraph system, monolithic system prompts fail because they dilute the model's attention mechanism across competing and often contradictory objectives.21 A system designed for scientific discovery requires distinct roles—the Planner, the Researcher, and the Reviewer—each operating under mutually exclusive, hyper-specialized prompt architectures that govern their specific behaviors and constraints.

### **Role-Specific Instructions: Planner, Researcher, and Reviewer**

The Planner functions as the orchestrator of the entire scientific endeavor. Its system prompt must strictly prohibit direct code execution, deep document reading, or granular implementation tasks. Instead, its instructions prioritize task decomposition, trajectory mapping, and rigorous state tracking. The Planner is instructed to utilize its tools to spawn sub-agents, construct architectural decision records, and continuously update a master progress document. Its prompt must instill human research heuristics, emphasizing the need to start with broad exploratory queries before narrowing down into specific technical investigations. It must also be explicitly programmed with scaling rules to judge the appropriate resource allocation for different sub-tasks, preventing the system from deploying massive computational resources on trivial fact-finding missions.4

The Researcher operates as the primary executor and is heavily biased toward action and exploration. Its prompt must actively encourage parallel tool execution, explicitly instructing the agent to read multiple files simultaneously or run concurrent speculative searches to maximize speed and efficiency.9 The prompt must emphasize rigorous source verification, iterative searching methodologies, and the necessity of writing structured outputs directly to the filesystem. By forcing the Researcher to output to disk rather than returning massive payloads through the conversational interface, the system prevents catastrophic context bloat during the execution phase.4

The Reviewer acts as the critical safeguard and operates in a strictly read-only capacity. Its prompt strips away all file-writing tools and focuses entirely on static analysis, logical consistency, and adherence to predefined constraints.24 The Reviewer's instructions must include strict, objective rubrics for evaluation. Furthermore, the prompt must mandate that any feedback or rejection is returned in a highly structured, machine-readable format designed to be easily parsed by the Planner or Researcher, eliminating vague critiques that lead to agent oscillation.25

| Agent Role | Core Prompt Directives | Tool Access Profile | Failure Mode Mitigation |
| :---- | :---- | :---- | :---- |
| **Planner** | Decompose tasks, track state in Markdown, allocate resources, verify completion. | Sub-agent spawning, filesystem write (for tracking only), repository read. | Prevented from doing deep implementation to avoid losing sight of the macro-level objectives. |
| **Researcher** | Maximize parallel tool calls, verify sources, dump findings to disk. | Broad read/write access, web search, code execution, bash terminal. | Forced to write to artifacts rather than chat history to prevent context window saturation. |
| **Reviewer** | Apply strict rubrics, perform static analysis, format feedback structurally. | Strictly read-only access, analytical tools, syntax checkers. | Mandated structured output prevents vague feedback that causes implementation loops. |

### **Dynamic Context Injection versus Static Instructions**

A fundamental debate in the design of long-running agents is the efficacy of static system prompts versus dynamically injected context. Over a conversation spanning hundreds of turns and multiple days, the influence of a static system prompt severely degrades. This phenomenon occurs due to the language model's attention mechanism, which naturally weights recent conversational tokens more heavily than distant instructional tokens, leading to a gradual loss of persona and constraint adherence.18

Best practices dictate a shift from static prompt templates to dynamic context engineering.26 Rather than front-loading an entire knowledge base into a monolithic system prompt, the core prompt should serve only as a lightweight wrapper containing immutable metadata. At runtime, a dynamic injection layer evaluates the agent's current state in the LangGraph cycle and injects the minimal, high-signal context required strictly for the immediate task.9

For multi-day runs, a Git-centric state management pattern is absolutely paramount. In this architecture, the system relies on the filesystem as the ultimate source of truth rather than the volatile conversational memory. At the initiation of each new LangGraph cycle, the agent's dynamic prompt is populated with the output of repository status commands, differences from the last commit, and the contents of a specialized progress tracking file.9 This allows the agent to maintain deep continuity across thousands of autonomous steps. It can save its state, hibernate, and wake up with a fresh context window, fully oriented to the project's current status without dragging an ever-expanding, token-heavy conversation history.9

### **Constraint Injection and Persona Maintenance**

Injecting hard constraints—such as prohibiting modifications to foundational infrastructure or mandating the recording of metrics before task completion—requires structural enforcement to prevent the model from drifting into non-compliance deep into a long-running session.

The application of XML formatting is one of the most reliable methods for steering Claude's adherence to rules. Wrapping absolute constraints inside specific XML tags allows Claude's attention mechanism, which is highly optimized for parsing XML hierarchies, to unambiguously distinguish immutable rules from volatile conversational context.9 Additionally, the physical placement of these constraints within the prompt payload is critical. The most vital instructions must be placed at both the absolute beginning and the absolute end of the prompt, capitalizing on the primacy and recency bias inherent in large language models to ensure the rules receive maximum attention weight.18

For sessions that extend beyond standard operational thresholds, systems may encounter automated context compaction or system-level reminders that can inadvertently alter the model's persona, making it overly cautious or clinical.29 To counteract this degradation in long conversations, developers implement periodic re-injection. This involves programmatically inserting a condensed version of the core constraints directly into the active conversation history at regular intervals. However, the most robust architectural solution to persona degradation remains aggressive session compaction or initiating a clean LangGraph node execution, utilizing the persistent Git-centric state as a fresh, unpolluted starting point.31

## **Part C: Multi-Agent Communication and State Management**

In a multi-agent LangGraph architecture, individual agents do not operate in a vacuum. The effectiveness of the AI Scientist relies entirely on how efficiently these entities pass state, share memory, and resolve inevitable conflicts. Unstructured multi-agent systems, where the raw output of one agent becomes the direct input of another, can amplify errors exponentially. The coordination layer must therefore be as rigorously engineered as the agents themselves.32

### **Agent Handoff Protocols in LangGraph**

When the Planner delegates a complex task to the Researcher, passing the entire conversation history results in immediate context window bloat, catastrophic token costs, and a high probability of the Researcher becoming distracted by irrelevant planning details.33 LangGraph orchestrates these handoffs utilizing explicitly defined state graphs and command objects to ensure clean transitions.34

A reliable handoff protocol relies on the principle of selective context passing. The LangGraph state schema must define multiple isolated channels of information. When routing execution from the Planner to the Researcher via a conditional edge, the payload transferred should strictly consist of a concise definition of the sub-goal, the specific acceptance criteria for completion, and explicit pointers to the relevant files or artifacts required for the task.36

The Researcher reconstructs the necessary operational context dynamically by reading the specified files through its own tools, rather than inheriting the Planner's massive conversation trace. The transfer mechanism utilizes tool calls that update an active agent state variable. The LangGraph orchestration layer detects this state mutation, suspends the Planner, and routes execution to the corresponding Researcher node. This ensures a deterministic transfer of control that enforces sequential constraints and prevents context contamination between specialized roles.36

### **Shared Memory and the Blackboard Pattern**

For multi-day AI Scientist systems requiring deep collaboration, point-to-point message passing creates brittle dependencies and massive redundant token usage. The industry standard for complex, asynchronous collaboration is the Blackboard pattern, implemented via a shared memory architecture.37

In LangGraph, the Blackboard is implemented as the central state object that all agents can read from and write to via explicitly defined reducer functions.38 The Blackboard acts as a decentralized communal workspace. Instead of the Planner attempting to direct-message the Researcher, the Planner posts a structured hypothesis to the Blackboard. The Researcher independently observes the Blackboard state, retrieves the hypothesis, conducts tool-based validation, and posts its empirical findings back to the board.37

To prevent this shared space from suffering its own context pollution, the memory architecture must be partitioned into a sophisticated three-tier model 39:

| Memory Tier | Architectural Implementation | Primary Function in Multi-Agent System |
| :---- | :---- | :---- |
| **Hot Memory** | The volatile LangGraph State object. | Maintains active task parameters, immediate tool outputs, and current sub-agent assignments for the active cycle. |
| **Warm Memory** | Local semantic vector store (RAG). | Stores observations and summaries from previous execution cycles. Agents utilize a push/pull strategy to inject relevant historical marks into their context. |
| **Cold Memory** | Persistent filesystem tracking (MEMORY.md). | Serves as the permanent ledger of architectural decisions, overarching project trajectory, and promoted recurring patterns. |

This strict separation ensures that agents seamlessly share critical semantic facts and overarching goals without cross-contaminating their procedural context windows with the raw, verbose tool outputs generated by other agents during their specific execution phases.40

### **Agent Disagreement and Oscillation Handling**

A critical failure mode in collaborative architectures is oscillation, where the Reviewer rejects the Researcher's output, the Researcher attempts a flawed fix, the Reviewer rejects it again, and the cycle repeats infinitely without meaningful progress, burning immense computational resources in the process.37

Handling agent disagreement in LangGraph requires structured feedback loops and strict circuit breakers. When sending work back for revision, the Reviewer cannot simply state that the output is flawed. It must be constrained to output a highly structured payload containing the specific issue identified, the exact location in the artifact, and a direct recommendation for remediation. Vague feedback invariably leads to random thrashing by the executing agent.41

To definitively prevent infinite loops, the architecture must introduce specialized Conciliator nodes and iteration caps. The LangGraph state must track a revision counter for every discrete task. If the counter exceeds a predefined limit, the system must trip a circuit breaker. Control is then forcefully routed away from the Researcher and Reviewer back to the Planner node, or to a dedicated Conciliator node. This superior node synthesizes the differing arguments, evaluates the impasse, and issues a final, deterministic directive or forces the system to pivot to an entirely new hypothesis, preventing the system from deadlocking on a fundamentally flawed premise.42

## **Part D: Claude-Specific Optimizations and Cost Management**

Running a frontier model like Claude 3.7 Sonnet autonomously over multiple days introduces profound economic and performance variables. Optimizing the AI Scientist harness requires deep, precise integration with Anthropic's specialized architectural features to balance extreme reasoning capabilities with sustainable operational costs.

### **Integrating Extended Thinking in LangGraph Nodes**

Claude 3.7 Sonnet introduces hybrid reasoning, dynamically switching between standard rapid generation and an Extended Thinking mode.44 For a multi-agent AI Scientist, enabling Extended Thinking allows the model to generate hidden reasoning traces to methodically solve complex logic, mathematics, or deep architectural problems before emitting its final programmatic response.45

A transformative feature of this capability is interleaved tool use. Claude 4.6 and 3.7 Sonnet support the ability to think, request a tool call, receive the tool result, and return to thinking before determining the next step. This is profoundly powerful for a Researcher agent that must evaluate complex API payloads or interpret dense scientific data iteratively.46

Implementing this within a LangGraph node requires specific architectural configurations. The API request must explicitly specify the thinking configuration, often utilizing the adaptive mode which allows the model to determine its own required reasoning depth. Crucially, when an LLM node returns a tool call, the LangGraph state must preserve the exact, unmodified thinking block that preceded the tool call and feed it back into the model alongside the tool results. Modifying or dropping this cryptographic block disrupts the model's reasoning continuity and results in fatal API errors.46 Furthermore, Extended Thinking must be applied selectively. It should be enabled for the Planner during task decomposition and the Reviewer during deep code analysis, but aggressively disabled for simple data extraction nodes, as thinking tokens are billed as output tokens and dramatically increase the time-to-first-token latency.46

### **Claude Agent SDK versus Raw Anthropic API**

When constructing the custom LangGraph harness, engineers face a critical architectural decision: whether to wrap the raw Anthropic API or utilize the purpose-built Claude Agent SDK.

The Claude Agent SDK provides a programmable autonomous loop out of the box. It handles tool execution, context formatting, automatic compaction, and retries natively, operating on the exact same infrastructure that powers the Claude Code product.48 It ships with highly optimized, production-ready tools for bash execution, file reading, and pattern matching, eliminating the need to build these volatile OS-level interactions from scratch. Conversely, utilizing the raw API requires manual implementation of the entire execution loop, meticulously checking stop reasons, and building custom token management middleware.48

However, the Agent SDK is highly opinionated and locks the system exclusively into Anthropic models.49 For a production LangGraph system requiring maximum resilience, the optimal solution is a hybrid architecture. LangGraph must dictate the macro-orchestration—defining the graph edges, managing the Blackboard state, and executing supervisor logic. The individual nodes within that graph, however, instantiate the Claude Agent SDK to handle the micro-execution. This hybrid pattern abstracts away the severe boilerplate of safe tool execution and context compaction while maintaining total architectural control over the multi-agent workflow and allowing for potential multi-model routing at the supervisor level.50

### **Cost Management Strategies for Multi-Day Executions**

A multi-day AI Scientist utilizing frontier models can rapidly consume significant financial resources if token usage is not aggressively managed. Multi-agent architectures inherently burn tokens faster than single-agent chats due to the continuous reprompting of state and the overhead of parallel processing.4 Ensuring the economic viability of the system relies on three interconnected strategies.

First, the system must implement strict model tier routing. LangGraph should not route every node to Claude 3.7 Sonnet. High-complexity tasks demanding deep synthesis must use the frontier model, but low-complexity tasks—such as basic log parsing, web scraping, or routing decisions—should be directed to Claude 3.5 Haiku. This routing strategy offers massive cost reductions for mechanical tasks that do not require extended reasoning capabilities.51

Second, developers must maximize the utility of prompt caching. Anthropic's caching infrastructure allows developers to store massive system prompts, extensive tool schemas, and core project documentation on the server for a fraction of the standard input cost.53 The LangGraph architecture must place static instructions at the absolute top of the prompt payload with explicit cache control blocks. To maintain cache integrity, developers must ensure that tool lists and system instructions are completely deterministic; dynamically shuffling the order of tools between turns will break the cache hash and trigger full-price recomputations, destroying the economic benefits.54

Finally, the system must leverage the token-efficient tool use beta capabilities available for Claude 3.7 Sonnet. Enabling this feature optimizes how the model processes tool inputs and outputs, resulting in highly significant reductions in output token consumption for workflows heavily dependent on continuous environmental interaction.56 By combining intelligent routing, aggressive caching, and optimized tool execution, the AI Scientist can operate continuously over long horizons without generating prohibitive operational costs.

## **Conclusion**

The realization of a multi-agent AI Scientist powered by Claude 3.7 Sonnet and LangGraph represents a graduation from traditional software development into the realm of intelligent systems engineering. Success in this domain is dictated not by the raw intelligence of the underlying model, but by the structural integrity of the harness that contains it. By enforcing strictly idempotent tool schemas, managing massive outputs through programmatic truncation, and replacing static monolithic prompts with dynamic, Git-centric context injection, developers can systematically eliminate the context rot that plagues long-running agents.

The integration of a partitioned Blackboard memory architecture alongside selective context passing ensures that Planner, Researcher, and Reviewer agents can collaborate deeply without polluting their respective operational environments. Furthermore, by strategically blending the macro-orchestration of LangGraph with the robust micro-execution capabilities of the Claude Agent SDK, systems achieve an unprecedented level of autonomy. When paired with rigorous cost management strategies—including prompt caching, model tier routing, and the precise application of Extended Thinking—organizations can deploy resilient, economically viable AI systems capable of executing complex, multi-day scientific and engineering tasks autonomously.

#### **引用的著作**

1. Inside the Claude Agents SDK: Lessons from the AI Engineer Summit \- ML6, 檢索日期：3月 18, 2026， [https://www.ml6.eu/en/blog/inside-the-claude-agents-sdk-lessons-from-the-ai-engineer-summit](https://www.ml6.eu/en/blog/inside-the-claude-agents-sdk-lessons-from-the-ai-engineer-summit)  
2. The Agent Harness Is the Architecture (and Your Model Is Not the Bottleneck) | by Evangelos Pappas | Feb, 2026, 檢索日期：3月 18, 2026， [https://medium.com/@epappas/the-agent-harness-is-the-architecture-and-your-model-is-not-the-bottleneck-5ae5fd067bb2](https://medium.com/@epappas/the-agent-harness-is-the-architecture-and-your-model-is-not-the-bottleneck-5ae5fd067bb2)  
3. The Anatomy of an Agent Harness \- LangChain Blog, 檢索日期：3月 18, 2026， [https://blog.langchain.com/the-anatomy-of-an-agent-harness/](https://blog.langchain.com/the-anatomy-of-an-agent-harness/)  
4. How we built our multi-agent research system \- Anthropic, 檢索日期：3月 18, 2026， [https://www.anthropic.com/engineering/multi-agent-research-system](https://www.anthropic.com/engineering/multi-agent-research-system)  
5. Anthropic: How we built our multi-agent research system, 檢索日期：3月 18, 2026， [https://simonwillison.net/2025/Jun/14/multi-agent-research-system/](https://simonwillison.net/2025/Jun/14/multi-agent-research-system/)  
6. Writing effective tools for AI agents—using AI agents \- Anthropic, 檢索日期：3月 18, 2026， [https://www.anthropic.com/engineering/writing-tools-for-agents](https://www.anthropic.com/engineering/writing-tools-for-agents)  
7. Programmatic tool calling (PTC) \- Claude Developer Platform, 檢索日期：3月 18, 2026， [https://platform.claude.com/cookbook/tool-use-programmatic-tool-calling-ptc](https://platform.claude.com/cookbook/tool-use-programmatic-tool-calling-ptc)  
8. How to implement tool use \- Claude API Docs, 檢索日期：3月 18, 2026， [https://platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use)  
9. Prompting best practices \- Claude API Docs, 檢索日期：3月 18, 2026， [https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)  
10. Skill authoring best practices \- Claude API Docs, 檢索日期：3月 18, 2026， [https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)  
11. Top 10 Agent Tool Patterns (That Won't Melt Your Backend) | by Bhagya Rana \- Medium, 檢索日期：3月 18, 2026， [https://medium.com/@bhagyarana80/top-10-agent-tool-patterns-that-wont-melt-your-backend-2a920e108828](https://medium.com/@bhagyarana80/top-10-agent-tool-patterns-that-wont-melt-your-backend-2a920e108828)  
12. How to write idempotent Bash scripts · Fatih Arslan \- Reddit, 檢索日期：3月 18, 2026， [https://www.reddit.com/r/bash/comments/rc9y3k/how\_to\_write\_idempotent\_bash\_scripts\_fatih\_arslan/](https://www.reddit.com/r/bash/comments/rc9y3k/how_to_write_idempotent_bash_scripts_fatih_arslan/)  
13. Writing CLI Tools That AI Agents Actually Want to Use \- DEV Community, 檢索日期：3月 18, 2026， [https://dev.to/uenyioha/writing-cli-tools-that-ai-agents-actually-want-to-use-39no](https://dev.to/uenyioha/writing-cli-tools-that-ai-agents-actually-want-to-use-39no)  
14. How I Run LLM Agents in a Secure Nix Sandbox \- DEV Community, 檢索日期：3月 18, 2026， [https://dev.to/andersonjoseph/how-i-run-llm-agents-in-a-secure-nix-sandbox-1899](https://dev.to/andersonjoseph/how-i-run-llm-agents-in-a-secure-nix-sandbox-1899)  
15. \[BUG\] Claude Code ingests massive tool outputs without truncation, causing context overflow \#12054 \- GitHub, 檢索日期：3月 18, 2026， [https://github.com/anthropics/claude-code/issues/12054](https://github.com/anthropics/claude-code/issues/12054)  
16. Context Management for Deep Agents \- LangChain Blog, 檢索日期：3月 18, 2026， [https://blog.langchain.com/context-management-for-deepagents/](https://blog.langchain.com/context-management-for-deepagents/)  
17. I made a tiny MCP “truncation proxy” for Claude Code so tool outputs don't nuke my token usage : r/ClaudeCode \- Reddit, 檢索日期：3月 18, 2026， [https://www.reddit.com/r/ClaudeCode/comments/1qbqqip/i\_made\_a\_tiny\_mcp\_truncation\_proxy\_for\_claude/](https://www.reddit.com/r/ClaudeCode/comments/1qbqqip/i_made_a_tiny_mcp_truncation_proxy_for_claude/)  
18. System prompt compliance degrades over long conversations and nobody talks about it enough : r/ClaudeAI \- Reddit, 檢索日期：3月 18, 2026， [https://www.reddit.com/r/ClaudeAI/comments/1rh5l0l/system\_prompt\_compliance\_degrades\_over\_long/](https://www.reddit.com/r/ClaudeAI/comments/1rh5l0l/system_prompt_compliance_degrades_over_long/)  
19. Design Patterns to Secure LLM Agents In Action \- Labs by Reversec, 檢索日期：3月 18, 2026， [https://labs.reversec.com/posts/2025/08/design-patterns-to-secure-llm-agents-in-action](https://labs.reversec.com/posts/2025/08/design-patterns-to-secure-llm-agents-in-action)  
20. ReversecLabs/design-patterns-for-securing-llm-agents-code-samples \- GitHub, 檢索日期：3月 18, 2026， [https://github.com/ReversecLabs/design-patterns-for-securing-llm-agents-code-samples](https://github.com/ReversecLabs/design-patterns-for-securing-llm-agents-code-samples)  
21. Best practices for structuring specialized agents in agentic development? : r/ClaudeCode, 檢索日期：3月 18, 2026， [https://www.reddit.com/r/ClaudeCode/comments/1robhv1/best\_practices\_for\_structuring\_specialized\_agents/](https://www.reddit.com/r/ClaudeCode/comments/1robhv1/best_practices_for_structuring_specialized_agents/)  
22. Claude Multi-Agent System Delivers the Biggest Automation Jump You'll Feel Immediately, 檢索日期：3月 18, 2026， [https://www.reddit.com/r/AISEOInsider/comments/1r1btxs/claude\_multiagent\_system\_delivers\_the\_biggest/](https://www.reddit.com/r/AISEOInsider/comments/1r1btxs/claude_multiagent_system_delivers_the_biggest/)  
23. What is the best tool for long-running agentic memory in Claude Code? : r/ClaudeAI \- Reddit, 檢索日期：3月 18, 2026， [https://www.reddit.com/r/ClaudeAI/comments/1q7mp8m/what\_is\_the\_best\_tool\_for\_longrunning\_agentic/](https://www.reddit.com/r/ClaudeAI/comments/1q7mp8m/what_is_the_best_tool_for_longrunning_agentic/)  
24. Create custom subagents \- Claude Code Docs, 檢索日期：3月 18, 2026， [https://code.claude.com/docs/en/sub-agents](https://code.claude.com/docs/en/sub-agents)  
25. 10 Must-Have Skills for Claude (and Any Coding Agent) in 2026 \- Medium, 檢索日期：3月 18, 2026， [https://medium.com/@unicodeveloper/10-must-have-skills-for-claude-and-any-coding-agent-in-2026-b5451b013051](https://medium.com/@unicodeveloper/10-must-have-skills-for-claude-and-any-coding-agent-in-2026-b5451b013051)  
26. Context Engineering vs Prompt Engineering for AI Agents \- Firecrawl, 檢索日期：3月 18, 2026， [https://www.firecrawl.dev/blog/context-engineering](https://www.firecrawl.dev/blog/context-engineering)  
27. Effective harnesses for long-running agents \- Anthropic, 檢索日期：3月 18, 2026， [https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)  
28. Effective Prompt Engineering: Mastering XML Tags for Clarity, Precision, and Security in LLMs | by Tech for Humans | Medium, 檢索日期：3月 18, 2026， [https://medium.com/@TechforHumans/effective-prompt-engineering-mastering-xml-tags-for-clarity-precision-and-security-in-llms-992cae203fdc](https://medium.com/@TechforHumans/effective-prompt-engineering-mastering-xml-tags-for-clarity-precision-and-security-in-llms-992cae203fdc)  
29. How to free Your Claude from the dreaded "Long Conversation Reminder" \- Reddit, 檢索日期：3月 18, 2026， [https://www.reddit.com/r/ClaudeAI/comments/1nricut/how\_to\_free\_your\_claude\_from\_the\_dreaded\_long/](https://www.reddit.com/r/ClaudeAI/comments/1nricut/how_to_free_your_claude_from_the_dreaded_long/)  
30. Long conversation prompt got exposed : r/ClaudeAI \- Reddit, 檢索日期：3月 18, 2026， [https://www.reddit.com/r/ClaudeAI/comments/1r954gd/long\_conversation\_prompt\_got\_exposed/?tl=en](https://www.reddit.com/r/ClaudeAI/comments/1r954gd/long_conversation_prompt_got_exposed/?tl=en)  
31. Claude Code Best Practices \- GitHub Pages, 檢索日期：3月 18, 2026， [https://rosmur.github.io/claudecode-best-practices/](https://rosmur.github.io/claudecode-best-practices/)  
32. The Multi-Agent Trap | Towards Data Science, 檢索日期：3月 18, 2026， [https://towardsdatascience.com/the-multi-agent-trap/](https://towardsdatascience.com/the-multi-agent-trap/)  
33. How are you handling context sharing in Multi-Agent-Systems(MAS)? Looking for alternatives to rigid JSON states : r/LangGraph \- Reddit, 檢索日期：3月 18, 2026， [https://www.reddit.com/r/LangGraph/comments/1qug9f5/how\_are\_you\_handling\_context\_sharing\_in/](https://www.reddit.com/r/LangGraph/comments/1qug9f5/how_are_you_handling_context_sharing_in/)  
34. How Agent Handoffs Work in Multi-Agent Systems | Towards Data Science, 檢索日期：3月 18, 2026， [https://towardsdatascience.com/how-agent-handoffs-work-in-multi-agent-systems/](https://towardsdatascience.com/how-agent-handoffs-work-in-multi-agent-systems/)  
35. Understanding multi-agent handoffs \- YouTube, 檢索日期：3月 18, 2026， [https://www.youtube.com/watch?v=WTr6mHTw5cM](https://www.youtube.com/watch?v=WTr6mHTw5cM)  
36. Handoffs \- Docs by LangChain, 檢索日期：3月 18, 2026， [https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs)  
37. Patterns for Democratic Multi‑Agent AI: Blackboard Architecture — Part 1 \- Medium, 檢索日期：3月 18, 2026， [https://medium.com/@edoardo.schepis/patterns-for-democratic-multi-agent-ai-blackboard-architecture-part-1-69fed2b958b4](https://medium.com/@edoardo.schepis/patterns-for-democratic-multi-agent-ai-blackboard-architecture-part-1-69fed2b958b4)  
38. Building Production-Ready Multi-Agent AI Systems | by meghna bhardwaj \- Medium, 檢索日期：3月 18, 2026， [https://medium.com/renben-technologies/building-production-ready-multi-agent-ai-systems-bbc6dd62c2f5](https://medium.com/renben-technologies/building-production-ready-multi-agent-ai-systems-bbc6dd62c2f5)  
39. Built a shared memory \+ inter-agent messaging layer for Claude Code swarms (DuckDB \+ Cloudflare RAG) : r/LocalLLaMA \- Reddit, 檢索日期：3月 18, 2026， [https://www.reddit.com/r/LocalLLaMA/comments/1r8bc65/built\_a\_shared\_memory\_interagent\_messaging\_layer/](https://www.reddit.com/r/LocalLLaMA/comments/1r8bc65/built_a_shared_memory_interagent_messaging_layer/)  
40. Memory as infrastructure in multi-agent LangChain / LangGraph systems \- Reddit, 檢索日期：3月 18, 2026， [https://www.reddit.com/r/LangChain/comments/1rdftbj/memory\_as\_infrastructure\_in\_multiagent\_langchain/](https://www.reddit.com/r/LangChain/comments/1rdftbj/memory_as_infrastructure_in_multiagent_langchain/)  
41. Building a Multi-Agent System for Automating Literature Reviews | by Boyuan Wu \- Medium, 檢索日期：3月 18, 2026， [https://medium.com/@boyuanwu01/research-reviewer-agents-building-a-multi-agent-system-for-automating-literature-reviews-f3515c1b3693](https://medium.com/@boyuanwu01/research-reviewer-agents-building-a-multi-agent-system-for-automating-literature-reviews-f3515c1b3693)  
42. Introducing the Conciliator Architecture for AI Agents in LangGraph \- Medium, 檢索日期：3月 18, 2026， [https://medium.com/@juanluis1702/introducing-the-conciliator-architecture-for-ai-agents-in-langgraph-4a112a4daba8](https://medium.com/@juanluis1702/introducing-the-conciliator-architecture-for-ai-agents-in-langgraph-4a112a4daba8)  
43. 97 days running autonomous Claude Code agents with 5109 quality checks. Here's what actually breaks. \- Reddit, 檢索日期：3月 18, 2026， [https://www.reddit.com/r/ClaudeCode/comments/1rkt6k6/97\_days\_running\_autonomous\_claude\_code\_agents/](https://www.reddit.com/r/ClaudeCode/comments/1rkt6k6/97_days_running_autonomous_claude_code_agents/)  
44. Easily integrate Claude Sonnet 3.7 hybrid reasoning with Langchain and AWS Bedrock | by ravindu somawansa | Medium, 檢索日期：3月 18, 2026， [https://medium.com/@ravindu.somawansa/easily-integrate-claude-sonnet-3-7-hybrid-reasoning-with-langchain-and-aws-bedrock-392299f4079e](https://medium.com/@ravindu.somawansa/easily-integrate-claude-sonnet-3-7-hybrid-reasoning-with-langchain-and-aws-bedrock-392299f4079e)  
45. Extended thinking \- Amazon Bedrock \- AWS Documentation, 檢索日期：3月 18, 2026， [https://docs.aws.amazon.com/bedrock/latest/userguide/claude-messages-extended-thinking.html](https://docs.aws.amazon.com/bedrock/latest/userguide/claude-messages-extended-thinking.html)  
46. Building with extended thinking \- Claude API Docs, 檢索日期：3月 18, 2026， [https://platform.claude.com/docs/en/build-with-claude/extended-thinking](https://platform.claude.com/docs/en/build-with-claude/extended-thinking)  
47. Anthropic Claude API Pricing 2026: Complete Cost Breakdown \- MetaCTO, 檢索日期：3月 18, 2026， [https://www.metacto.com/blogs/anthropic-api-pricing-a-full-breakdown-of-costs-and-integration](https://www.metacto.com/blogs/anthropic-api-pricing-a-full-breakdown-of-costs-and-integration)  
48. Agent SDK overview \- Claude API Docs, 檢索日期：3月 18, 2026， [https://platform.claude.com/docs/en/agent-sdk/overview](https://platform.claude.com/docs/en/agent-sdk/overview)  
49. Claude Agent SDK: Subagents, Sessions and Why It's Worth It \- Kyle Redelinghuys, 檢索日期：3月 18, 2026， [https://www.ksred.com/the-claude-agent-sdk-what-it-is-and-why-its-worth-understanding/](https://www.ksred.com/the-claude-agent-sdk-what-it-is-and-why-its-worth-understanding/)  
50. Using Claude SDK inside LangGraph nodes \- hybrid pattern that finally clicked \- Reddit, 檢索日期：3月 18, 2026， [https://www.reddit.com/r/ClaudeAI/comments/1qgax1g/using\_claude\_sdk\_inside\_langgraph\_nodes\_hybrid/](https://www.reddit.com/r/ClaudeAI/comments/1qgax1g/using_claude_sdk_inside_langgraph_nodes_hybrid/)  
51. Claude Haiku 4.5 vs Sonnet 4.5: Building Smarter AI Agents | atal upadhyay, 檢索日期：3月 18, 2026， [https://atalupadhyay.wordpress.com/2025/10/20/claude-haiku-4-5-vs-sonnet-4-5-building-smarter-ai-agents/](https://atalupadhyay.wordpress.com/2025/10/20/claude-haiku-4-5-vs-sonnet-4-5-building-smarter-ai-agents/)  
52. Models overview \- Claude API Docs, 檢索日期：3月 18, 2026， [https://platform.claude.com/docs/en/about-claude/models/overview](https://platform.claude.com/docs/en/about-claude/models/overview)  
53. Prompt caching for faster model inference \- Amazon Bedrock, 檢索日期：3月 18, 2026， [https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html)  
54. Prompt caching \- Claude API Docs, 檢索日期：3月 18, 2026， [https://platform.claude.com/docs/en/build-with-claude/prompt-caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)  
55. Cache engineering : how to build successful Agents : r/ClaudeCode \- Reddit, 檢索日期：3月 18, 2026， [https://www.reddit.com/r/ClaudeCode/comments/1r9dfpx/cache\_engineering\_how\_to\_build\_successful\_agents/](https://www.reddit.com/r/ClaudeCode/comments/1r9dfpx/cache_engineering_how_to_build_successful_agents/)  
56. Claude's Token Efficient Tool Use on Amazon Bedrock | AWS Builder Center, 檢索日期：3月 18, 2026， [https://builder.aws.com/content/2trguomubYb8f3JNzCeBgNvassc/claudes-token-efficient-tool-use-on-amazon-bedrock](https://builder.aws.com/content/2trguomubYb8f3JNzCeBgNvassc/claudes-token-efficient-tool-use-on-amazon-bedrock)