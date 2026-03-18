# KB-07: Self-Evolution Mechanism

**Source:** Deep Research on DSPy, prompt auto-optimization, model lifecycle, workflow self-modification (2025–2026)

---

## Key Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | **Prompt optimization framework** | DSPy + GEPA (Genetic-Pareto) optimizer | GEPA traces failures back through the graph to identify whether failure originated in Planner vs. Researcher; optimizes 3 dimensions simultaneously (not scalar reward) |
| 2 | **Optimization signal** | Composite 3D vector: Reproducibility Pass Rate + Execution Stability Score + Reviewer Quality Rubric | Single scalar gives zero diagnostic info; structured signal enables targeted mutation at exact failure layer |
| 3 | **Prompt regression testing** | LLM-as-Judge + deterministic trace replay with stubbed external calls, before Git commit | Prevents "prompt drift"; isolates prompt change variance from external API variance |
| 4 | **Sentinel model promotion** | Shadow Mode → A/B Testing (MAB routing) → Canary (5%→25%→100%) | Hard cutover risks undetected failure modes corrupting Git state; 3-stage rollout allows rollback at each checkpoint |
| 5 | **Model promotion criteria** | Composite utility: Structured Output Adherence + Domain Golden Dataset Score + Latency/VRAM efficiency — ALL 3 must dominate | Academic benchmarks (MMLU) are poor proxies for operational tasks (JSON parsing, PyTorch log classification) |
| 6 | **Dynamic workflow modification** | LangGraph `Command()` routing for node-level changes; `ServerRuntime` graph factory for topology changes | Allows Reviewer to insert a Debugging Specialist node on L3 coordination failures without restarting the system |
| 7 | **Failure taxonomy** | 4-tier: L1 Generation (hallucination) → L2 Information (tool/API gaps) → L3 Interaction (coordination loops) → L4 Interpretation (goal drift) | Each tier maps to a specific autonomous intervention; prevents brute-force restarts |
| 8 | **Self-modification guardrails** | 5-layer defense: immutable crypto core + DRIFT memory isolation + Guide() steerable runtime + hard circuit breaker (max 15 Pregel super-steps) + Git rollback | Prevents recursive logic corruption, infinite loops, token exhaustion, unrecoverable state |

---

## Part A: Prompt Auto-Optimization

### DSPy + GEPA Algorithm (2025–2026 State)

DSPy treats prompts as optimizable parameters (not static strings). Planner/Researcher/Reviewer are wrapped as **DSPy modules**; Reviewer's structured output serves as the evaluation metric.

**GEPA 4-stage continuous pipeline:**
1. Select candidates from Pareto frontier (balances token efficiency + success rate + Reviewer score)
2. Execute on minibatch of historical failures from PostgreSQL
3. LLM-driven reflection on execution traces → root cause diagnosis → natural language feedback
4. Mutate based on ancestor insights; update Pareto front only if new candidate strictly dominates

**Alternative prompt optimization frameworks:**
- **HRPO (Hierarchical Reflective):** Batch-level structural root cause analysis; prevents volatile over-corrections
- **DEEVO (Debate-driven Evolutionary):** Elo-based crossover/mutation; prevents premature convergence
- **MA-SAPO (Multi-Agent Score-Aware):** Agents collaboratively diagnose Reviewer scores and synthesize refinements

### Optimization Signal Design

**Do NOT use:** Single binary Reviewer accept/reject — zero diagnostic info

**Use:** Composite triplet per experiment:
- `reproducibility_pass_rate`: % of generated code that runs without syntax/dependency errors
- `execution_stability_score`: Consistency across 5 repeated runs with same seed variations (0–100)
- `reviewer_quality_rubric`: Scientific coherence + methodological rigor + novelty + statistical soundness (0–100)

GEPA Pareto frontier: optimize all 3 simultaneously; only accept candidate that dominates incumbent on **all** dimensions.

### Regression Testing (Preventing Prompt Drift)

**Golden Dataset structure:**
- Historical execution traces (Planner input → Researcher output → Reviewer rubric)
- Edge cases: adversarial experiment specs, ambiguous data, conflicting constraints
- Each trace labeled with expected outcome (pass/fail, expected score range)

**Trace Replay Protocol:**
- Intercept external tool calls (web searches, code execution, file I/O)
- Replace with pre-recorded golden stubs — isolates prompt variance from external API variance
- Execute every proposed mutation against full golden dataset before Git commit
- LLM-as-Judge: if pass rate drops or schema violations detected → reject mutation immediately

**Rollback:** Every accepted mutation = Git commit. Rolling 50-experiment average monitored. Any dimension drop triggers `git revert` to last known-good commit.

### Meta-Learning for Strategic Behavior

- **MR-Search:** Trains policy conditioning on past episodes; deep cross-episode exploration via self-reflections stored in persistent context
- **MAGE (Population-Based):** Extracts generalized insights from recurring cognitive biases in past failures; enables autonomous tool-chain deduction
- **MetaAgent (FSM):** Planner maintains evolving meta-policy reading accumulated outcomes from PostgreSQL; adapts orchestration by experiment domain

**Domain-specific FSM behavior:**
- Diffusion model experiments → prioritize literature verification + math derivation tools
- Hyperparameter tuning → prioritize Python execution + syntax validation tools

---

## Part B: Local Model Periodic Replacement

### Automated Benchmarking Pipeline

**Detection:** External monitoring daemon polls model registry (HuggingFace, Ollama) → detects new Llama/Qwen/Mistral variants → triggers headless isolated benchmarking.

**Benchmark sequence (in order):**
1. Hardware Profiling: peak CPU, GPU allocation, RAM/VRAM vs. system constraints
2. Throughput Analysis: Time-to-First-Token (TTFT) and Tokens-Per-Second (TPS)
3. Domain-Specific Batch Execution: Sentinel tasks (parse DL stack traces, summarize Git diffs, classify structured logs)

**Tools:** `promptfoo` or `local-llm-benchmark` (GitHub: kaushall13/local-llm-benchmark) for evaluation across quantizations and context sizes.

### MLOps 3-Stage Rollout

| Stage | Risk | Mechanism | Use |
|-------|------|-----------|-----|
| Shadow Mode | Zero | Duplicate traffic to candidate; isolated DB; output ignored | Measure real-world latency, VRAM under load, output divergence |
| A/B Testing | Moderate | Multi-Armed Bandit routing; track Reviewer acceptance rate downstream | Statistically prove end-to-end superiority |
| Canary | Low | 5%→25%→100% traffic; health metric checkpoints | Safe cutover after passing Shadow + A/B |

**Auto-rollback:** At any stage, if latency spikes >20%, formatting hallucinations, or metric regression → CI/CD invokes rollback + logs failure to update future thresholds.

### Promotion Criteria (All 3 Must Dominate Simultaneously)

1. **Structured Output Adherence:** Valid JSON arrays; no conversational prose, markdown, trailing commas
2. **Domain-Specific Evaluation Score:** Accuracy on internal golden dataset (log classification, stack trace analysis, heuristic error extraction)
3. **Resource & Latency Efficiency:** Equal or superior TTFT/TPS within pre-defined VRAM budget

**Reject if:** Accuracy improvement requires exceeding VRAM budget → automatic rejection regardless of quality gain.

---

## Part C: Workflow Self-Modification

### LangGraph Dynamic Topology

**Command() routing (node-level):**
```python
Command(goto="target_node", update={"state_key": "new_value"})
```
Allows Reviewer to bypass static edges; e.g., route back to Literature Review on theoretical gap detection.

**ServerRuntime (topology-level):**
- Define graph via dynamic factory function
- Reconstruct node set before execution run
- Example: Insert "Debugging Specialist" node on L3 coordination failure
- Safe: PostgreSQL checkpointers persist state; no active threads routed to deprecated nodes

**Limitation:** Cannot route active threads to recently removed nodes — always reconstruct before routing.

### Failure Taxonomy + Autonomous Handlers

| Tier | Name | Example | Auto-Intervention |
|------|------|---------|------------------|
| L1 | Generation (hallucination) | Researcher outputs prose instead of JSON | GEPA prompt mutation + Git commit |
| L2 | Information (tool/API gap) | Code sandbox returns dependency error | Tool parameter swap via Command() |
| L3 | Interaction (coordination loop) | Planner/Researcher loop on same PyTorch compilation | ServerRuntime inserts Debugging Specialist node |
| L4 | Interpretation (goal drift) | Optimizes training speed instead of validation accuracy | Meta-strategy FSM shift; add goal-alignment verification |

**Attribution:** Who&When-style dataset approach to pinpoint exact error step within execution trajectory.

### Self-Modification Guardrails (5 Layers)

| Layer | Mechanism | Protects Against |
|-------|-----------|-----------------|
| L1 | Immutable crypto core specs at startup | Agent modifying budget caps, API scopes |
| L2 | DRIFT framework (memory state masking) | Context poisoning cascading through shared graph state |
| L3 | Guide() steerable commands (not binary deny) | Soft-limit violations without crashing graph |
| L4 | Hard circuit breaker: max 15 Pregel super-steps | Infinite loops, token exhaustion |
| L5 | Git commit tracking + CI/CD auto-revert | Any sustained metric degradation (>3 consecutive experiments below threshold) |

---

## Integration Checklist

- [ ] Wrap Planner/Researcher/Reviewer prompts as DSPy modules
- [ ] Wire GEPA optimizer to PostgreSQL failure log
- [ ] Build golden dataset; implement trace replay with stubbing
- [ ] Implement external model monitoring daemon
- [ ] Implement Shadow → A/B → Canary deployment controller
- [ ] Wire failure classifier (L1–L4) into Reviewer node
- [ ] Enable Command() routing in Planner/Reviewer for dynamic topology
- [ ] Load immutable core specs at startup
- [ ] Implement DRIFT memory masking
- [ ] Set max Pregel super-steps = 15 in LangGraph executor
- [ ] Wire CI/CD monitoring → auto git revert on rolling average degradation

---

## PostgreSQL Schema Requirements

Tables needed for self-evolution:
- `experiments`: id, timestamp, status, reviewer_metrics (3D vector)
- `failures`: failure_type (L1–L4), timestamp, affected_node, traceback, root_cause
- `golden_datasets`: curated traces for regression testing
- `prompts_history`: version, node, content_hash, git_commit, optimizer_metadata
- `model_deployments`: model_name, version, phase, metrics_snapshot, decision_outcome
- `git_commits`: hash, timestamp, change_type, pareto_front_state

---

*Raw deep research content preserved above. Key Decisions table at top for quick reference.*

## **The Emergence of an Infrastructure Discipline**

Between 2025 and early 2026, the artificial intelligence sector underwent a fundamental architectural paradigm shift. For several years, the prevailing methodology for advancing artificial intelligence relied heavily on scaling foundational model parameters and refining pre-training data. The industry measured progress through static leaderboards and single-turn evaluations, inherently assuming that the raw cognitive capability of a large language model (LLM) was the sole determinant of an autonomous agent's success. However, as enterprise software teams and research laboratories attempted to deploy these highly capable models to execute complex, multi-day, real-world workflows, a critical bottleneck became apparent. Models that performed exceptionally well on isolated benchmarks consistently failed in production due to execution drift, context exhaustion, infinite retry loops, and an inability to maintain coherent state over extended time horizons.1

The realization that an agent’s reliability depends significantly more on its surrounding infrastructure than on its internal model weights birthed a distinct engineering discipline: Harness Engineering.3 Formalized in the technical discourse of early 2026, harness engineering is the practice of designing, building, and maintaining the cognitive infrastructure that surrounds an AI model. It provides the persistent memory, structured domain knowledge, tool execution environment, strict boundaries, and deterministic feedback loops that allow an LLM to function as a stable, long-running agent.4 The core philosophy underpinning this discipline dictates that the probabilistic model does not run the system; rather, the deterministic system runs the model.6

To comprehend the full scope of this shift, one must view the AI system not as a standalone brain, but as an assembled computer. In this analogy, the foundational model serves merely as the central processing unit (CPU), providing raw processing power. The context window acts as the random access memory (RAM), offering limited and volatile working space. The agent harness, therefore, operates as the entire operating system and motherboard—managing the file system, orchestrating input and output, enforcing security permissions, and preserving state.2 Without a robust harness, even the most advanced CPU cannot execute a sustained application.

## **Definition, Scope, and Origins**

The term "agent harness" began to permeate developer vernacular informally, but it was rigorously formalized in February 2026 by thought leaders such as Mitchell Hashimoto, who identified that practitioners had been informally building these structures without a unified vocabulary.7 Concurrently, prominent AI engineers such as Viv framed harness engineering as the most critical subset of context engineering, focusing entirely on the configuration surfaces and peripherals that a model utilizes to interact with its environment.5 By late February 2026, the concept reached widespread industry validation when OpenAI's Codex team published an extensive postmortem detailing how they utilized "harness engineering" to generate a one-million-line production codebase with zero human-written code.8

Harness engineering is formally defined as the design and implementation of systems that perform four vital functions for an autonomous agent. First, the harness must constrain the agent, establishing architectural boundaries and dependency rules that mechanically limit permissible actions, thereby preventing the model from exploring infinite dead ends. Second, it must inform the agent by dynamically injecting the exact context it needs—such as machine-readable documentation, repository-local knowledge, and environment mapping—without overflowing the model's context window. Third, the harness must verify the agent's outputs through deterministic gates, which include structured linting, continuous integration validation, and deterministic simulation testing. Finally, it must correct the agent by engineering automated feedback loops and self-repair mechanisms that inject error traces directly back into the agent's reasoning cycle, empowering it to autonomously resolve its own mistakes.9

### **Distinguishing the Engineering Stack**

To fully grasp harness engineering, it is imperative to distinguish it from adjacent AI engineering disciplines. The proliferation of terminology in 2025 led to perceived fragmentation, but by 2026, the industry recognized these labels not as competing frameworks, but as complementary layers of a unified production stack.10

| Engineering Discipline | Scope of Intervention | Primary Focus and Objectives |
| :---- | :---- | :---- |
| **Prompt Engineering** | Single Interaction | Crafting effective natural language instructions; optimizing the immediate phrasing, role-play, and step-by-step logic provided to the model. 9 |
| **Context Engineering** | Model Context Window | System-level design of what information the model sees at inference time; managing retrieval-augmented generation (RAG), intentional compaction, and dynamic context injection. 9 |
| **Harness Engineering** | Entire Agent Environment | Designing the constraints, tool execution runtimes, persistence mechanisms, deterministic feedback loops, and lifecycle management outside the model. 9 |
| **Agentic / Agent Engineering** | Internal Architecture | The overarching production discipline of specifying, routing, and orchestrating non-deterministic AI systems; designing multi-agent coordination. 9 |
| **Platform / LLMOps** | Infrastructure | Deployment, hardware scaling, load balancing, continuous training pipelines, and physical cloud operations. 9 |

While prompt engineering seeks to guide the model by asking the right questions, and context engineering seeks to assist the model by showing the right data, harness engineering assumes that any catastrophic failure by the agent is a systemic failure of the infrastructure.7 Harness engineers treat agent mistakes not as prompts to be retried, but as structural vulnerabilities requiring permanent, mechanical fixes.5

## **Navigating the Architectural Lexicon: Harness vs. Scaffold vs. Framework**

As autonomous system design matured, the industry required precise taxonomy to differentiate the structural components of agent applications. The terms "framework," "scaffold," and "harness" were frequently conflated in early 2024 literature, but established distinct architectural definitions by 2026\.14

A framework represents a general-purpose library or toolkit used to construct agent systems. Solutions like LangGraph, CrewAI, and AutoGen serve as foundational frameworks.14 They provide the theoretical primitives, standardizing how an agent graph is defined, how state is passed between nodes, and how LLM calls are structured. However, a framework does not inherently dictate the final operational environment; it merely provides the scaffolding materials. Frameworks excel in allowing developers to quickly define workflows but leave the burden of production-grade execution entirely to the engineering team.15

A scaffold, by contrast, denotes the specific, often lightweight structure within which an agent operates for a single, bounded task. Scaffolding typically encompasses a prompt template, a simple reasoning loop (such as ReAct), and minimal tool connections. In older literature, the term scaffold was used to describe the immediate context injected around a prompt to help the model solve a problem. Scaffolding is transient and does not provide long-term state management, scheduling, or robust error recovery mechanisms across multiple sessions.14

The harness subsumes and transcends both frameworks and scaffolds. It constitutes the complete, production-grade architectural system that envelops the LLM, managing the entire lifecycle of context from intent capture through persistence.7 A harness provides a concrete runtime environment, executing the underlying code, securely routing tool calls, enforcing compliance gates, monitoring telemetry, and managing the physical filesystem. In essence, while developers use a framework to write their agentic logic, they deploy that logic into a harness to make it reliable at scale.14 The LLM and the framework are interchangeable components; the harness is the permanent product.6

## **Core Principles and Foundational Manifestos**

The transition from theoretical agent frameworks to industrialized harnesses was largely driven by empirical lessons derived from deploying autonomous systems at scale. Two major paradigms define the core principles of the discipline: the "12-Factor Agent" methodology and the architectural lessons derived from OpenAI's million-line codebase experiment.

### **The 12-Factor Agent Methodology**

Drawing direct inspiration from the legacy "12-Factor App" methodology that revolutionized cloud-native software a decade prior, the "12-Factor Agents" manifesto—popularized by Dex Horthy and the HumanLayer engineering team—established the definitive blueprint for building reliable, horizontally scalable LLM applications.17 The principles explicitly reject the notion that complex problems require sprawling, monolithic, highly autonomous agents. Instead, they advocate for modular, stateless, and mechanically controlled designs that isolate risk.18

The fundamental agent loop defined by these factors relies on the LLM functioning purely as a reasoning and routing engine. Rather than engineers writing extensive directed acyclic graphs (DAGs) to handle every edge case, the model is given an objective and a set of permissible tools. The LLM determines the next step, outputting a structured schema. Deterministic code then executes that tool call, appends the objective result to the context window, and re-invokes the LLM.17 This loop relies on treating the agent as a functional component rather than a conscious entity.

| Core 12-Factor Principle | Architectural Application in Harness Design |
| :---- | :---- |
| **Factor 1: Natural Language to Tool Calls** | The harness must restrict the agent's outputs to structured, schema-valid commands (JSON extraction) rather than permitting free-form wildcard text generation. 18 |
| **Factor 3: Own Your Context Window** | The harness must explicitly and mechanically manage what enters the context window, utilizing "intentional compaction" to prevent the accumulation of noise. 19 |
| **Factor 5: Unify Execution and Business State** | Harnesses must cleanly separate the state of the agent's current thought loop from the underlying business data, ensuring distinct lifecycles and recovery protocols. 19 |
| **Factor 6: Launch, Pause, Resume APIs** | The harness must provide mechanisms for agent workflows to be paused, serialized to a database, and resumed across different hardware instances. 16 |
| **Factor 9: Compact Errors into Context** | When a tool fails, the harness must not crash; it must format the error into legible text, inject it into the context, and force the agent to autonomously self-correct. 17 |
| **Factor 10: Small, Focused Agents** | Reliability plummets as sequential steps increase. Harnesses should constrain individual agent invocations to a maximum of 3 to 10 steps, utilizing routing to pass tasks between narrow specialists. 19 |
| **Factor 12: Stateless Reducers** | By externalizing all memory, state, and tool execution to the harness, the agent becomes a pure mathematical function mapping an input array to an output decision, allowing deterministic testing. 18 |

By adhering to these factors, harness engineers ensure that the probabilistic nature of the LLM is strictly bounded by the deterministic, predictable nature of traditional software engineering.

### **OpenAI’s Million-Line Codebase: Legibility and Entropy Management**

In February 2026, OpenAI published the results of a landmark internal experiment that fundamentally validated the harness engineering philosophy. Over five months, a small team of human engineers built a production software application containing roughly one million lines of code, with zero lines typed manually by humans.8 The project was executed entirely by Codex agents operating within a highly engineered harness, yielding an engineering velocity estimated to be ten times faster than human output.8

The experiment demonstrated that when agents write the code, human engineers must shift their focus entirely to increasing "application legibility"—making the codebase inherently readable, navigable, and strictly organized for the machine rather than for human developers.8

To prevent the agent from making structural errors, the OpenAI harness enforced a rigid domain model. Code was mechanically forced to move through strict architectural layers, progressing from Types to Config, to Repo, to Service, to Runtime, and finally to UI.8 These boundaries were mechanically enforced by custom, Codex-generated linters. Crucially, when an agent violated an architectural rule, the harness did not merely return an opaque error code. Instead, it injected highly specific, context-aware remediation instructions directly into the agent's subsequent prompt, creating an autonomous repair loop that allowed the agent to fix its own architectural drift.8 Furthermore, cross-cutting concerns, such as authentication and telemetry, were isolated behind explicit provider interfaces to intentionally limit the agent's blast radius when modifying core business logic.8

The harness also eliminated traditional tribal knowledge by establishing the repository itself as the sole system of record. Recognizing that loading massive, monolithic instruction manuals into an agent's context window leads to severe performance degradation, the harness utilized a compact root document that acted merely as a table of contents.8 The agent was trained to recursively explore a structured documentation directory containing versioned execution plans and architectural decisions. To maintain the accuracy of this knowledge base, the harness utilized background "doc-gardening" agents that continuously scanned the repository, autonomously opening pull requests to update documentation whenever the underlying implementation code changed.8

A critical innovation of this deployment was the handling of code entropy. As autonomous agents generate code at massive scale, they naturally produce suboptimal, verbose, or redundant patterns colloquially referred to as "AI slop".12 The OpenAI harness mitigated this through continuous, automated garbage collection. Human engineers encoded highly opinionated "golden principles"—such as strictly favoring shared utility packages over localized helper functions—into the repository's mechanical rules.8 Background agents ran continuously, scanning the codebase for deviations from these principles, grading code quality, and automatically opening targeted refactoring pull requests to pay down technical debt before it could accumulate.8

### **The Principle of the "Rippable" Harness**

A pivotal design principle within harness engineering is avoiding the over-engineering of control flows. Because foundation models are rapidly improving on a month-to-month basis, complex routing logic or semantic parsing built into a harness to compensate for a model's reasoning deficit may actively hinder a smarter model released in subsequent quarters.9 Therefore, a well-engineered harness must be explicitly "rippable".9 It must be designed in highly decoupled, modular layers so that specific constraints, fallback trees, and cognitive crutches can be easily removed when the underlying model’s native capabilities render them obsolete.9 Treating the harness as a static, permanent artifact is widely cited as a primary failure mode in modern agent design.

## **Architecting Harnesses for Long-Running Agents**

Perhaps the most profound challenge addressed by the discipline of harness engineering is the orchestration of long-running, multi-day agent workflows.22 Due to the inherently stateless nature of LLMs and the hard limits of context windows, an agent cannot simply be instantiated and left to run continuously for a week. Every time an active context window fills up with tool outputs and thought trajectories, the session must be forcefully terminated, summarized, and restarted. Consequently, the agent begins the new session entirely amnesic, blind to the granular details of the work it just completed.22

Anthropic formalized the architectural solution to this problem in their influential 2026 publication, "Effective harnesses for long-running agents," which modeled autonomous workflows after human software engineers working in asynchronous shifts.22

### **The Two-Agent Pattern and State Persistence**

To bridge the operational gap between discrete context windows, Anthropic recommends a strict two-agent architecture natively governed by the harness infrastructure. This pattern completely separates the environment setup phase from the iterative execution phase.

The workflow begins with the **Initializer Agent**. This agent is invoked exclusively during the very first context window of a project lifecycle. Its sole responsibility is environmental scaffolding. Utilizing specialized prompts, the Initializer Agent translates a high-level human directive into a highly granular, structured feature list, typically formatted as a JSON file, which outlines all required project functionality down to the component level.22 Crucially, all features in this JSON file are initially marked as "failing," establishing a clear, machine-readable roadmap that prevents future agents from declaring the project finished prematurely.22 The Initializer Agent is also responsible for writing an initialization shell script to automate server setup and development environment restarts, and it establishes a persistent progress log to serve as the project's long-term memory.22

For every subsequent session, the harness spawns a fresh **Coding Agent**. This agent is mechanically constrained by the harness to focus entirely on incremental progress. Specifically, it is instructed to parse the JSON feature list and pull only one "failing" feature per session. This constraint actively prevents the agent from attempting to "one-shot" the entire application, which invariably leads to exhausted context windows and half-implemented, undocumented code.22

### **The Orientation Routine and the "Clean State"**

A well-engineered harness forces every newly spawned Coding Agent to undergo a mandatory orientation routine. Before the agent is permitted to take any generative action, it must execute a series of validation commands to get up to speed. It must verify its working directory, read the persistent progress file, review the latest version control commit logs, and consult the feature list to prioritize its immediate work.22

To ensure the subsequent agent in the sequence can operate successfully, the current agent must leave the environment in a "clean state" before its context window closes.22 The harness enforces this state by requiring the agent to commit its work to version control with highly descriptive commit messages, creating a chain of save points.22 Furthermore, the agent is required to self-verify its code using end-to-end browser automation tools, acting as a human user would, rather than relying solely on simplistic unit tests. Only after the harness verifies that these end-to-end tests have passed is the agent granted permission to mark a feature as "passing" in the central JSON registry.22

## **The Claude Agent SDK: Opinionated Harness Infrastructure**

The Anthropic Claude Agent SDK, introduced alongside the widely adopted Claude Code CLI, represents the industry standard for "batteries-included" harness infrastructure.2 Unlike unopinionated frameworks that require developers to manually construct the agent loop, state management, and tool routing from scratch, the Claude Agent SDK provides an out-of-the-box runtime environment that manages context compaction, tool dispatch, and session tracking autonomously.7

The SDK embodies Anthropic's specific harness engineering philosophy, making several critical infrastructure decisions by default while leaving specific application logic to the developer.

### **Filesystem-Based Context and Progressive Disclosure**

A defining characteristic of the Claude Agent SDK is its heavy reliance on the local filesystem as the primary vector for context engineering, deliberately eschewing complex external database integrations.23 By configuring the SDK to recognize the project directory as the source of truth, developers can control agent behavior entirely through a standardized hierarchy of markdown files.23

The SDK natively looks for global project context, architectural rules, and specific behavioral instructions within a primary CLAUDE.md file.23 Furthermore, it utilizes a .claude/commands/ directory to store developer-defined slash commands, acting as macros for executing common agent workflows.23

Most significantly, the SDK introduces a native architecture for "Skills," stored as markdown files within the .claude/skills/ directory. This feature allows the harness to practice progressive disclosure.23 Rather than front-loading every possible API contract, coding standard, and database schema into a massive system prompt—which degrades reasoning performance—the harness provides the agent with a lightweight index of available skills. The agent autonomously requests the specific skill file only when it encounters a domain it needs to interact with, drastically reducing baseline context bloat and token expenditure.24

### **Built-In Tool Execution and Deterministic Hooks**

Traditional LLM API integrations require software engineers to write extensive middleware that parses an LLM's JSON output, maps it to a local function, executes the code, formats the output, and returns the result. The Claude Agent SDK eliminates this overhead by providing built-in, autonomous tool execution.23 Out of the box, the harness equips the model with native tools enabling it to read files, execute bash commands, perform global searches, and execute targeted edits, effectively granting the agent secure, direct access to the host's terminal and filesystem.23

To balance this high degree of autonomy with enterprise safety requirements, the SDK harness relies heavily on a deterministic Hook System.23 Hooks—such as PreToolUse, PostToolUse, and SessionStart—allow developers to intercept the agent loop at strictly defined lifecycle events.26 This acts as a deterministic firewall around the model’s probabilistic decision-making. For example, if an agent attempts to execute a potentially destructive shell command, a PreToolUse hook can automatically pause execution, evaluate the command against a predefined permissions matrix, and either block the action entirely or seamlessly escalate the request to require explicit human approval.26

## **Harnessing the AI Scientist: Multi-Agent Research Pipelines**

While much of early harness engineering focused on software development tasks, the discipline rapidly expanded to support complex scientific discovery. Building a harness for an "AI Scientist"—a system designed to formulate hypotheses, design experiments, analyze results, and draft manuscripts—requires significantly more advanced architectural patterns to manage the sheer volume of data and required cognitive diversity.

### **The EvoScientist Framework and Specialized Agents**

The EvoScientist framework, introduced in early 2026, exemplifies state-of-the-art harness engineering for multi-agent research pipelines. It utilizes an evolving architecture designed to continuously improve research strategies through self-evolution and persistent memory, addressing the severe limitations of static, hand-designed pipelines.28

The EvoScientist harness separates the scientific method into distinct computational roles, utilizing three primary agents:

1. **The Researcher Agent (RA):** Tasked exclusively with exploring literature and generating novel scientific ideas.  
2. **The Engineer Agent (EA):** Tasked with the highly technical implementation and execution of the proposed experiments.  
3. **The Evolution Manager Agent (EMA):** A meta-agent responsible for observing the pipeline, distilling insights from previous interactions, and transforming those insights into reusable knowledge artifacts for future sessions.28

To ensure these agents do not repeatedly pursue infeasible ideas or duplicate failed experiments, the harness maintains two highly structured persistent memory modules. The "Ideation Memory" logs feasible research directions and explicitly tracks historically unsuccessful paths, preventing the Researcher Agent from drifting into redundant work.28 The "Experimentation Memory" captures effective data processing strategies and optimal code implementations, allowing the Engineer Agent to dramatically improve its execution success rates over time.28

### **Context Firewalls and Sub-Agent Delegation**

In massive multi-agent research pipelines, the harness must rigorously protect the primary orchestration agent from being overwhelmed by raw empirical data. As a lead agent delegates tasks—such as executing a data analysis script, searching extensive server logs, or performing deep codebase reviews—the returning output can instantly flood the context window.

Industry consensus establishes that when an agent's context window exceeds roughly 40% capacity, the model enters what is termed the "dumb zone," leading to a severe degradation in reasoning quality, instruction-following capabilities, and objective adherence.20

To combat this context rot, advanced harnesses implement Context Firewalls via sub-agent delegation.5 When a massive dataset needs to be processed, the harness spawns an ephemeral worker agent in a completely isolated context window. This sub-agent performs the data-heavy operation, analyzes the noise, and distills the results into a highly compressed, structured summary.30 The harness then passes only this compressed artifact back to the parent orchestrator agent. Often, these summaries require strict line-number citations or an "evidence contract" to ensure the orchestrator can trust the data without needing to verify the raw logs itself.5 This sophisticated map-reduce architecture ensures the parent agent’s context remains pristine, allowing the overarching pipeline to maintain high-level coherency over research tasks spanning weeks or months.5

## **Harness Failure Modes and the Taxonomy of Mistakes**

When building complex autonomous systems, diagnosing the root cause of a task failure is paramount. Harness engineering necessitates a strict diagnostic differentiation between a "model failure"—where the underlying LLM simply lacks the reasoning capacity or parametric knowledge to solve a problem—and a "harness failure"—where the infrastructure fails to adequately support, constrain, or inform the model.1

Industry data overwhelmingly indicates that the vast majority of agent failures in professional workflows are orchestration and harness failures, not knowledge deficits. The models generally possess the necessary information, but the infrastructure fails to maintain execution coherency.3

### **Primary Harness Failure Modes**

**1\. Context Rot and Execution Drift:** As an agent operates over time, its context window naturally fills with terminal outputs, stack traces, and verbose API responses. If the harness lacks a robust compaction mechanism, the ratio of signal to noise rapidly collapses.5 Operating beyond the 40% capacity threshold predictably pushes the model into the aforementioned "dumb zone," resulting in execution drift. The agent forgets its original objective, begins hallucinating capabilities, or loses track of its place in a multi-step sequence.1

**2\. Infinite Looping and the Lethal Trifecta:** When an agent executes an action that produces an opaque error—such as a silent failure or a massive, truncated stack trace—and the harness feeds that exact unparsed error back into the prompt without intervention, the agent will frequently attempt the exact same action again.5 A poorly designed harness allows the agent to drain its token budget in an infinite, recursive loop. A well-engineered harness detects repetitive actions and explicitly injects circuit-breaking context, mechanically instructing the agent to cease the current approach and evaluate the architecture documentation instead.17

**3\. Opaque Observability:** If a harness relies on human-centric documentation—such as architectural decisions stored in proprietary wikis, Confluence pages, or Slack threads—the agent cannot access the data necessary to resolve complex dependency issues.9 The harness fails by effectively blinding the agent to the reality of the codebase, ensuring it can only guess at required solutions rather than implementing verified patterns.

**4\. Premature Victory Declarations:** Without strict self-verification gates, agents exhibit a strong probabilistic bias toward concluding tasks as quickly as possible to satisfy the user's prompt. If the harness allows the agent to self-report success without providing cryptographic proof or passing a deterministic simulation test, the agent will frequently declare complex features "complete" while leaving behind half-implemented logic and silent bugs.22

## **Evaluation, Benchmarking, and Infrastructure Noise**

As the engineering focus shifted from the cognitive model to the execution harness, the methodologies for evaluating AI systems required a fundamental overhaul. Traditional benchmarking paradigms relied on static, single-turn prompts, evaluating code completion or logic puzzles in a vacuum. By 2026, the industry recognized that these static leaderboards provided an illusion of reliability, failing to measure how well an agent could sustain coherent execution across hundreds of steps.2

### **Terminal-Bench 2.0 and Dynamic Evaluation**

The premier standard for measuring agentic harness capabilities became Terminal-Bench 2.0.32 Unlike legacy benchmarks, Terminal-Bench provides agents with a fully operational, containerized terminal sandbox managed via a specialized execution package called Harbor.34 Agents are tasked with resolving 89 highly complex, long-horizon problems derived from real-world software engineering, system administration, and security workflows.36

To succeed on Terminal-Bench, an agent cannot simply generate a block of correct code. It must autonomously navigate the host filesystem, install missing dependencies, execute testing suites, interpret failing stack traces, and iteratively refine its solutions over time.38 Because the benchmark evaluates the entire autonomous system, optimizing the harness architecture—such as implementing more robust bash-error catchers, tuning the context compaction strategy, or providing better diagnostic tools—frequently yields higher leaderboard gains than upgrading to a newer LLM.3

### **Quantifying Infrastructure Noise**

The transition to dynamic, environment-based benchmarking revealed a critical vulnerability in how the industry measures agent performance. A definitive 2026 study published by Anthropic’s engineering team, titled "Quantifying infrastructure noise in agentic coding evals," demonstrated that the physical configuration of the testing harness profoundly distorts benchmark scores.33

Because an agentic evaluation involves compiling code, running intensive development servers, and executing complex test suites, the runtime environment is an active, integrated participant in the agent's problem-solving loop.33 Anthropic researchers discovered that simply altering the CPU and RAM allocations of the Kubernetes pods hosting the Terminal-Bench containers swung the final agent scores by up to 6 percentage points—a margin frequently larger than the stated capability gap between competing state-of-the-art foundation models.38

Agents operating in strictly resource-constrained containers frequently encountered out-of-memory (OOM) kills or CPU throttling timeouts during test execution.33 Crucially, because the agent interprets these infrastructure failures as flaws in its generated code, it wastes its available token budget attempting to "debug" logically correct implementations, ultimately failing the benchmark task.33 This study definitively proved that in the era of autonomous agents, the reliability of the execution harness is mathematically inseparable from the intelligence of the model.

### **Terminal-Bench Science: The Next Frontier**

Building upon the success of software engineering benchmarks, the Stanford Center for Decoding the Universe, in collaboration with industry laboratories, introduced Terminal-Bench Science in 2026\.40 This domain-specific benchmark targets multi-agent research pipelines, moving beyond pure code generation to evaluate agents on genuine scientific discovery workflows.40

The benchmark challenges agents with completing complex workflows across computational biology, high-energy astrophysics, and applied mathematics.40 To ensure rigorous evaluation, tasks must adhere to three strict criteria: they must be scientifically grounded in real research workflows, rather than textbook exercises; they must be objectively verifiable, requiring the agent to produce checkable numerical results, statistical fits, or reproducible data artifacts; and they must be genuinely difficult, specifically targeting tasks that frontier models currently fail to solve 80–90% of the time.40 By exposing the specific architectural gaps in modern research harnesses, Terminal-Bench Science is actively driving the development of robust, multi-day scientific data processing pipelines.

## **Tooling, Observability, and the Verification Loop**

The paradigm shift to harness-centric agent architectures necessitated a fundamental overhaul of industry observability tooling. Traditional application monitoring focuses heavily on latency, application uptime, and crash reporting. Agent observability, however, must capture probabilistic reasoning paths, track context window utilization, and analyze expansive tool execution trajectories.42

### **Observability-Driven Harnesses**

Companies such as Datadog, Honeycomb, and Groundcover pioneered the concept of "LLM Observability," providing dashboards and telemetry specifically designed to debug complex harness failures.44 By integrating platforms like the Datadog AI Agents Console directly with execution environments such as the Claude Agent SDK, engineers gained unprecedented real-time visibility into the entire agent lifecycle.46

Critical observability metrics for harness engineering diverge significantly from traditional software metrics. Engineers track token and cost velocity to monitor the exact financial expenditure of each sub-agent invocation, utilizing this data to identify and terminate runaway loops.46 They rigorously monitor cache hit rates to ensure prompt caching efficiency. If a harness dynamically reorders the system prompt or continuously injects highly variable telemetry data at the beginning of the context window, it destroys prefix caching capabilities, drastically increasing both latency and inference costs.47 Furthermore, tracking tool call error rates allows engineers to identify specific bash commands, API interactions, or database queries that frequently return errors to the agent, indicating an immediate need for improved tool descriptions or automated parameter formatting.46

### **Shifting from Code Review to Harness Review**

The sheer speed at which autonomous agents can generate code and analyze data creates a "scalability inversion": the machine can write software vastly faster than a human team can manually verify it.48 Consequently, the traditional manual code review process quickly becomes an unsustainable bottleneck in the development lifecycle.

Observability-driven harnesses resolve this inversion by completely closing the verification loop through deterministic simulation testing (DST), bounded proofs, and shadow-state oracles.48 The role of the human engineer transitions entirely from inspecting individual lines of code to reviewing the "harness output".48 The engineer is no longer required to parse logic; they merely verify that the agent successfully passed all structured invariants, telemetry checks, and simulation seeds required by the harness.48

This methodology results in a phenomenon known as compounding correctness. While a traditional manual code review only fixes the immediate diff currently in front of the developer, tightening a harness constraint—such as adding a new mechanical linter, expanding the DST coverage matrix, or refining a tool definition—eliminates an entire class of bugs for all future agent iterations.48 The harness itself evolves into a continuously compounding asset, ensuring that quality scales linearly with agent velocity.

### **The Agent that Investigates Itself**

The most advanced observability patterns emerging in late 2026 utilize the agents themselves to debug their own harness failures. In modern production deployments, when an observability alert fires indicating a sudden drop in prompt caching efficiency or a spike in tool execution failures, human engineers no longer manually query the logs.47

Instead, the infrastructure spawns a diagnostic sub-agent, granting it high-level access to the telemetry dashboard, querying languages like LogQL, and the host environment.8 The agent autonomously searches the historical logs, reads its own underlying source code, identifies the specific software regression—such as a recent commit that inadvertently altered a prompt prefix and broke the caching mechanism—and autonomously submits a pull request to repair its own harness infrastructure.47 This capability demonstrates the ultimate maturity of the discipline: an autonomous system capable of maintaining and optimizing the very environment that sustains it.

## **Conclusion**

The formalization of Harness Engineering as a distinct discipline in 2025 and 2026 marks the maturation of artificial intelligence from experimental chatbot applications to industrialized, autonomous knowledge workers. The consensus across the industry—from OpenAI’s generation of a million-line codebase without human intervention to Anthropic’s structured protocols for multi-day agent operations—is absolute: the raw cognitive capabilities of foundation models have reached a plateau of baseline viability. The competitive advantage in deploying these systems is now entirely dependent on the highly engineered infrastructure that surrounds them.

The era of relying on simplistic prompt scaffolding and expecting a probabilistic model to flawlessly navigate multi-step, real-world tasks has been unequivocally replaced by rigid, observability-driven engineering. By constraining agents with strict architectural boundaries, informing them through heavily curated and localized context, verifying their outputs with deterministic simulation testing, and utilizing multi-agent pipelines as robust context firewalls, organizations can successfully deploy agents that operate safely and autonomously for days or weeks at a time.

Ultimately, the foundational model is merely the computational engine. The harness provides the vehicle chassis, the steering mechanisms, and the critical safety systems. As the scale and ambition of autonomous AI systems continue to expand, mastering the rigorous design of this surrounding infrastructure remains the most critical engineering discipline for unlocking the full potential of artificial intelligence in production environments.

#### **引用的著作**

1. Beyond the Model: Why 2026 Is the Year of “Harness Engineering” \- Imbila.AI, 檢索日期：3月 18, 2026， [https://www.imbila.ai/beyond-the-model-why-2026-is-the-year-of-harness-engineering/](https://www.imbila.ai/beyond-the-model-why-2026-is-the-year-of-harness-engineering/)  
2. The importance of Agent Harness in 2026 \- Philschmid, 檢索日期：3月 18, 2026， [https://www.philschmid.de/agent-harness-2026](https://www.philschmid.de/agent-harness-2026)  
3. The Agent Harness Is the Architecture (and Your Model Is Not the Bottleneck) \- Medium, 檢索日期：3月 18, 2026， [https://medium.com/@epappas/the-agent-harness-is-the-architecture-and-your-model-is-not-the-bottleneck-5ae5fd067bb2](https://medium.com/@epappas/the-agent-harness-is-the-architecture-and-your-model-is-not-the-bottleneck-5ae5fd067bb2)  
4. Harness Engineering: The Infrastructure Discipline Autonomous Agents Require \- Medium, 檢索日期：3月 18, 2026， [https://medium.com/@srikanthbellary01/harness-engineering-the-infrastructure-discipline-autonomous-agents-require-c31c8374005b](https://medium.com/@srikanthbellary01/harness-engineering-the-infrastructure-discipline-autonomous-agents-require-c31c8374005b)  
5. Skill Issue: Harness Engineering for Coding Agents | HumanLayer Blog, 檢索日期：3月 18, 2026， [https://www.humanlayer.dev/blog/skill-issue-harness-engineering-for-coding-agents](https://www.humanlayer.dev/blog/skill-issue-harness-engineering-for-coding-agents)  
6. THE CI/CD OF CODE ITSELF. Harness Engineering Looks Like at Every… | by Deb Acharjee | Mar, 2026 | Medium, 檢索日期：3月 18, 2026， [https://medium.com/@DebaA/the-ci-cd-of-code-itself-2c63ce65013e](https://medium.com/@DebaA/the-ci-cd-of-code-itself-2c63ce65013e)  
7. What Is an Agent Harness? The Infrastructure That Makes AI Agents Actually Work, 檢索日期：3月 18, 2026， [https://www.firecrawl.dev/blog/what-is-an-agent-harness](https://www.firecrawl.dev/blog/what-is-an-agent-harness)  
8. Harness engineering: leveraging Codex in an agent-first world | OpenAI, 檢索日期：3月 18, 2026， [https://openai.com/index/harness-engineering/](https://openai.com/index/harness-engineering/)  
9. Harness Engineering: The Complete Guide to Building Systems That Make AI Agents Actually Work (2026) | NxCode, 檢索日期：3月 18, 2026， [https://www.nxcode.io/resources/news/harness-engineering-complete-guide-ai-agent-codex-2026](https://www.nxcode.io/resources/news/harness-engineering-complete-guide-ai-agent-codex-2026)  
10. How Many Types of Agent Engineering Exist Right Now? \- Superagentic AI Blog, 檢索日期：3月 18, 2026， [https://shashikantjagtap.net/how-many-types-of-agent-engineering-exist-right-now/](https://shashikantjagtap.net/how-many-types-of-agent-engineering-exist-right-now/)  
11. Agent Engineering 101 at GDG London: How to Build Reliable AI Systems, 檢索日期：3月 18, 2026， [https://shashikantjagtap.net/agent-engineering-101-at-gdg-london-how-to-build-reliable-ai-systems/](https://shashikantjagtap.net/agent-engineering-101-at-gdg-london-how-to-build-reliable-ai-systems/)  
12. Beyond Prompts and Context: Harness Engineering for AI Agents | MadPlay, 檢索日期：3月 18, 2026， [https://madplay.github.io/en/post/harness-engineering](https://madplay.github.io/en/post/harness-engineering)  
13. orchestration \- LLMOps Database \- ZenML, 檢索日期：3月 18, 2026， [https://www.zenml.io/llmops-tags/orchestration](https://www.zenml.io/llmops-tags/orchestration)  
14. What Is an AI Agent Harness? The Architecture Behind Stripe's 1,300 Weekly AI Pull Requests | MindStudio, 檢索日期：3月 18, 2026， [https://www.mindstudio.ai/blog/what-is-ai-agent-harness-stripe-minions-2](https://www.mindstudio.ai/blog/what-is-ai-agent-harness-stripe-minions-2)  
15. The Best Open Source Frameworks For Building AI Agents in 2026 \- Firecrawl, 檢索日期：3月 18, 2026， [https://www.firecrawl.dev/blog/best-open-source-agent-frameworks](https://www.firecrawl.dev/blog/best-open-source-agent-frameworks)  
16. Picking an agentic framework in 2026: what actually matters \- Rhesis AI, 檢索日期：3月 18, 2026， [https://rhesis.ai/post/picking-agentic-framework-2026](https://rhesis.ai/post/picking-agentic-framework-2026)  
17. GitHub \- humanlayer/12-factor-agents: What are the principles we can use to build LLM-powered software that is actually good enough to put in the hands of production customers?, 檢索日期：3月 18, 2026， [https://github.com/humanlayer/12-factor-agents](https://github.com/humanlayer/12-factor-agents)  
18. 12-Factor Agents: A Blueprint for Reliable LLM Applications \- IKANGAI, 檢索日期：3月 18, 2026， [https://www.ikangai.com/12-factor-agents-a-blueprint-for-reliable-llm-applications/](https://www.ikangai.com/12-factor-agents-a-blueprint-for-reliable-llm-applications/)  
19. The 12-Factor Agent: A Practical Framework for Building Production AI Systems, 檢索日期：3月 18, 2026， [https://dev.to/bredmond1019/the-12-factor-agent-a-practical-framework-for-building-production-ai-systems-3oo8](https://dev.to/bredmond1019/the-12-factor-agent-a-practical-framework-for-building-production-ai-systems-3oo8)  
20. DO NOT OUTSOURCE THE THINKING: Context Engineering & Human-AI Collaboration, 檢索日期：3月 18, 2026， [https://thefocus.ai/reports/aiecode-2025-11/article/context-engineering-human-ai-collaboration.md/](https://thefocus.ai/reports/aiecode-2025-11/article/context-engineering-human-ai-collaboration.md/)  
21. The 8 Levels of Agentic Engineering : r/ClaudeCode \- Reddit, 檢索日期：3月 18, 2026， [https://www.reddit.com/r/ClaudeCode/comments/1rprmgy/the\_8\_levels\_of\_agentic\_engineering/](https://www.reddit.com/r/ClaudeCode/comments/1rprmgy/the_8_levels_of_agentic_engineering/)  
22. Effective harnesses for long-running agents \- Anthropic, 檢索日期：3月 18, 2026， [https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)  
23. Agent SDK overview \- Claude API Docs, 檢索日期：3月 18, 2026， [https://platform.claude.com/docs/en/agent-sdk/overview](https://platform.claude.com/docs/en/agent-sdk/overview)  
24. Claude Agents SDK: Best Practices From the Team That Built It | by Robert Mill \- Medium, 檢索日期：3月 18, 2026， [https://bertomill.medium.com/claude-agents-sdk-best-practices-from-the-team-that-built-it-63580d1a0c3b](https://bertomill.medium.com/claude-agents-sdk-best-practices-from-the-team-that-built-it-63580d1a0c3b)  
25. AutoJunjie/awesome-agent-harness \- GitHub, 檢索日期：3月 18, 2026， [https://github.com/AutoJunjie/awesome-agent-harness](https://github.com/AutoJunjie/awesome-agent-harness)  
26. Why Agent Harness Architecture is Important, 檢索日期：3月 18, 2026， [https://contextua.dev/why-agent-harness-architecture-is-important/](https://contextua.dev/why-agent-harness-architecture-is-important/)  
27. Claude Agent SDK \[Full Workshop\] — Thariq Shihipar, Anthropic \- YouTube, 檢索日期：3月 18, 2026， [https://www.youtube.com/watch?v=TqC1qOfiVcQ](https://www.youtube.com/watch?v=TqC1qOfiVcQ)  
28. EvoScientist: Towards Multi-Agent Evolving AI Scientists for End-to ..., 檢索日期：3月 18, 2026， [https://hgpu.org/?p=30662](https://hgpu.org/?p=30662)  
29. Stop Bloating Your CLAUDE.md: Progressive Disclosure for AI Coding Tools | alexop.dev, 檢索日期：3月 18, 2026， [https://alexop.dev/posts/stop-bloating-your-claude-md-progressive-disclosure-ai-coding-tools/](https://alexop.dev/posts/stop-bloating-your-claude-md-progressive-disclosure-ai-coding-tools/)  
30. Context Firewall Claude Code Skill | Manage Large Context \- MCP Market, 檢索日期：3月 18, 2026， [https://mcpmarket.com/tools/skills/context-firewall](https://mcpmarket.com/tools/skills/context-firewall)  
31. Why AI Agent Reliability Depends More on the Harness Than the Model | HackerNoon, 檢索日期：3月 18, 2026， [https://hackernoon.com/why-ai-agent-reliability-depends-more-on-the-harness-than-the-model](https://hackernoon.com/why-ai-agent-reliability-depends-more-on-the-harness-than-the-model)  
32. \[2601.11868\] Terminal-Bench: Benchmarking Agents on Hard, Realistic Tasks in Command Line Interfaces \- arXiv, 檢索日期：3月 18, 2026， [https://arxiv.org/abs/2601.11868](https://arxiv.org/abs/2601.11868)  
33. Quantifying infrastructure noise in agentic coding evals \- Anthropic, 檢索日期：3月 18, 2026， [https://www.anthropic.com/engineering/infrastructure-noise](https://www.anthropic.com/engineering/infrastructure-noise)  
34. harbor-framework/terminal-bench: A benchmark for LLMs on complicated tasks in the ... \- GitHub, 檢索日期：3月 18, 2026， [https://github.com/harbor-framework/terminal-bench](https://github.com/harbor-framework/terminal-bench)  
35. Introducing Terminal-Bench 2.0 and Harbor, 檢索日期：3月 18, 2026， [https://www.tbench.ai/news/announcement-2-0](https://www.tbench.ai/news/announcement-2-0)  
36. Benchmarks \- Terminal-Bench, 檢索日期：3月 18, 2026， [https://www.tbench.ai/benchmarks](https://www.tbench.ai/benchmarks)  
37. Terminal-Bench: Benchmarking Agents on Hard, Realistic Tasks in Command Line Interfaces | Snorkel AI, 檢索日期：3月 18, 2026， [https://snorkel.ai/research-paper/terminal-bench-benchmarking-agents-on-hard-realistic-tasks-in-command-line-interfaces/](https://snorkel.ai/research-paper/terminal-bench-benchmarking-agents-on-hard-realistic-tasks-in-command-line-interfaces/)  
38. Anthropic reports that agent coding performance varies by several percentage points depending on hardware configuration, and the difference in benchmark scores between high-performance models may be due to the benefit of high-performance hardware. \- GIGAZINE, 檢索日期：3月 18, 2026， [https://gigazine.net/gsc\_news/en/20260206-quantifying-infrastructure-noise-agentic-coding/](https://gigazine.net/gsc_news/en/20260206-quantifying-infrastructure-noise-agentic-coding/)  
39. That Benchmark Lead Might Just Be a Bigger VM: Anthropic's Eye-Opening Study on Infrastructure Noise in Agentic Evals | by ADITHYA GIRIDHARAN | Feb, 2026 | Medium, 檢索日期：3月 18, 2026， [https://medium.com/@AdithyaGiridharan/that-benchmark-lead-might-just-be-a-bigger-vm-anthropics-eye-opening-study-on-infrastructure-f487596de714](https://medium.com/@AdithyaGiridharan/that-benchmark-lead-might-just-be-a-bigger-vm-anthropics-eye-opening-study-on-infrastructure-f487596de714)  
40. Terminal-Bench-Science: Now in Development, 檢索日期：3月 18, 2026， [https://www.tbench.ai/news/tb-science-announcement](https://www.tbench.ai/news/tb-science-announcement)  
41. Big Questions, Bold Ideas: 2026 Winter Forum Recap \- Stanford Data Science, 檢索日期：3月 18, 2026， [https://datascience.stanford.edu/news/big-questions-bold-ideas-2026-winter-forum-recap](https://datascience.stanford.edu/news/big-questions-bold-ideas-2026-winter-forum-recap)  
42. AI News \- xAGI Labs, 檢索日期：3月 18, 2026， [https://xagi.in/ai-news](https://xagi.in/ai-news)  
43. Building reliable dashboard agents with Datadog LLM Observability, 檢索日期：3月 18, 2026， [https://www.datadoghq.com/blog/llm-observability-at-datadog-dashboards/](https://www.datadoghq.com/blog/llm-observability-at-datadog-dashboards/)  
44. CaSE: Conversations about Software Engineering \- Podcast, 檢索日期：3月 18, 2026， [https://www.case-podcast.org/](https://www.case-podcast.org/)  
45. Observability for AI Tools, Improved Connected Apps Flows, and More Self-Serve Options, 檢索日期：3月 18, 2026， [https://www.groundcover.com/whats-new/observability-for-ai-tools-improved-connected-apps-flows-and-more-self-serve-options](https://www.groundcover.com/whats-new/observability-for-ai-tools-improved-connected-apps-flows-and-more-self-serve-options)  
46. Monitor Claude Code adoption in your organization with Datadog's AI Agents Console, 檢索日期：3月 18, 2026， [https://www.datadoghq.com/blog/claude-code-monitoring/](https://www.datadoghq.com/blog/claude-code-monitoring/)  
47. Harness Engineering for Azure SRE Agent: Building the Agent Self-Improvement Loop, 檢索日期：3月 18, 2026， [https://techcommunity.microsoft.com/blog/appsonazureblog/the-agent-that-investigates-itself/4500073](https://techcommunity.microsoft.com/blog/appsonazureblog/the-agent-that-investigates-itself/4500073)  
48. Closing the verification loop: Observability-driven harnesses for building with agents, 檢索日期：3月 18, 2026， [https://www.datadoghq.com/blog/ai/harness-first-agents/](https://www.datadoghq.com/blog/ai/harness-first-agents/)
