# Knowledge Base 02: Agent Architecture for Long-Running Research Pipelines

> Source: Gemini Deep Research, 2026-03-18
> Purpose: Design reference for AI Scientist system architecture

---

## Key Decisions Derived from This Research

| Decision | Adopted Pattern | Reason |
|----------|----------------|--------|
| Orchestration framework | **LangGraph** | Supports cycles (Reviewer → Researcher), node-level checkpointing, explicit state machine |
| State management | **Git-centric** | Auditable timeline, time-travel recovery, delta-based context reconstruction |
| Agent structure | **Multi-agent** (Planner / Researcher / Reviewer separated) | ~60% lower hallucination, better token efficiency, isolated failure domains |
| Memory model | **3-tier** (Hot / Warm / Cold) | Prevents context rot (performance degrades >50k tokens) |
| Context management | **Hierarchical summarization** + Claude native pruning tools | Compress tool logs; keep decisions |
| HiTL with Discord | **ApprovalRequired pattern** + Redis/PostgreSQL state persistence | State must survive while waiting for human approval |
| Tool design | **Idempotent tools** with checksum/state checks | Prevents double-execution on retry |

## State File: Essential vs Reconstructible

| Element | Classification | Format |
|---------|---------------|--------|
| Research roadmap + success metrics | Essential | JSON / Markdown |
| Current task index / stage | Essential | Key-value |
| Key findings log (distilled) | Essential | Markdown episodic log |
| Environment state (SSH IDs, tmux names, file pointers) | Essential | YAML |
| Full tool logs / raw tmux output | Reconstructible | Do NOT serialize — page from filesystem |
| Intermediate reasoning | Reconstructible | Summarize, don't keep raw |

## 3-Tier Memory Model

```
Hot   (in-context)   → current task + last 10-15 turns
Warm  (file system)  → experiment logs, code, results — paged via grep/cat
Cold  (vector DB)    → literature, historical runs, failure memory — semantic search
```

## Resilience: Key Mechanisms

| Pillar | Implementation |
|--------|---------------|
| Circuit Breakers | Fail fast on tool timeout; no infinite retry |
| Backpressure | Queue incoming triggers; prevent sentinel storms |
| Durable Workflows | LangGraph checkpointing at every node |
| Rate Limiting | Priority queue: Planner > Researcher for API access |
| Model Fallbacks | Secondary model if primary API fails |
| Tool-call Counter | Same tool 5+ times without state change → force intervention |
| Periodic Cleanup | Cleanup node removes temp files, updates progress summary |

## Framework Comparison (2025)

| Framework | Best For | State Mechanism | Our Use |
|-----------|----------|----------------|---------|
| **LangGraph** | Iterative research cycles with cycles/retries | Reducer-driven checkpointing | **Selected** |
| PydanticAI + Temporal | High-stakes enterprise; replay-based fault tolerance | Durable execution | Reference for resilience patterns |
| CrewAI | Role-based content generation | Sequential task handoffs | Not suitable for long-running |

## Common Production Failure Patterns

1. **"Declare Victory Too Early"**: agent marks complete on superficial result → require self-verified feature list before closing
2. **"Infinite Tool Loop"**: agent calls `ls` 5+ times on inaccessible directory → tool-call counter
3. **"Environment Drift"**: temp files accumulate over days → periodic cleanup nodes

---

## Original Research Question and Full Answer

# **Architectural Frameworks for Long-Horizon Agentic Systems: A Comprehensive Study on the Production-Grade AI Scientist**

The rapid evolution of agentic artificial intelligence in 2025 has transitioned the field from experimental chat interfaces to durable, long-running pipelines capable of executing complex research tasks over multiple days. This shift necessitates a sophisticated architectural approach that prioritizes state persistence, resilient tool orchestration, and hierarchical memory management. For a system designed to function as an autonomous "AI Scientist"—utilizing a Planner → Researcher → Reviewer pipeline—the engineering requirements move beyond simple prompt-response cycles toward a robust infrastructure capable of surviving API failures, process restarts, and context limitations. The integration of Claude as the primary reasoning engine, supported by localized monitoring models and human-in-the-loop oversight, represents the current state-of-the-art for enterprise-grade autonomous research.1

## **Advanced Architectures for Production-Grade Pipelines**

In 2025, building a production-grade agentic pipeline requires moving away from "black-box" orchestrators toward modular, observable frameworks. The landscape is currently dominated by three primary architectural patterns: stateful graphs, durable execution workflows, and role-based hierarchical teams. For a multi-day research pipeline, the consensus among systems architects favors frameworks that provide explicit control over state transitions and failure recovery mechanisms.4

### **Comparative Analysis of Agentic Frameworks in 2025**

The following table provides a technical comparison of the leading frameworks utilized for long-running Claude-based agents.

| Framework | Core Philosophy | State Management Mechanism | Resilience Strategy | Optimal Use Case |
| :---- | :---- | :---- | :---- | :---- |
| **LangGraph** | Directed Acyclic/Cyclic Graphs | Reducer-driven checkpointing 5 | Built-in node-level retries and persistent history 4 | Iterative research cycles (Research-Review-Revise) 7 |
| **PydanticAI** | Type-safe, Software-Centric | Durable execution via Temporal/DBOS 8 | Replay-based fault tolerance and transactional tasks 10 | High-stakes enterprise automation (Finance, Legal) 3 |
| **CrewAI** | Role-based Orchestration | Sequential/Hierarchical task handoffs 4 | Task-level delegation and agent-to-agent feedback 11 | Content generation and collaborative brainstorming 7 |
| **ADK (Google)** | Multi-Agent Patterns | Shared session state with output keys 13 | AutoFlow mechanism for dynamic intent routing 13 | High-throughput data processing pipelines 13 |

LangGraph has emerged as a premier choice for research-oriented pipelines because it treats workflows as explicit state machines. In a Planner → Researcher → Reviewer cycle, LangGraph allows for "cycles" where a Reviewer agent can reject a draft and route the workflow back to the Researcher node. The framework’s ability to checkpoint the state at every node ensures that the system can resume from the exact point of interruption if the host process crashes or if Claude hits a rate limit.5

PydanticAI offers a different but equally compelling value proposition through its integration with durable execution engines like Temporal. This approach separates the deterministic logic of the workflow from the non-deterministic interactions with LLMs and external tools. If a network failure occurs during a multi-day research task, Temporal's replay mechanism ensures the agent picks up exactly where it left off, avoiding the cost and latency of re-executing previously successful steps.9

## **State Serialization and Resumption Engineering**

A long-running agent must be "stateless" at the model level but "stateful" at the application level. Because Claude is woken up periodically by external triggers, the system must serialize its entire operational context into a format that allows the model to fully regain situational awareness.15

### **Essential vs. Reconstructible State**

In designing a serialization schema, engineers must distinguish between critical state variables and context that can be generated on-demand. Overloading the resumption prompt with irrelevant history leads to "context rot" and increased token costs.16

| State Element | Classification | Reason for Classification | Serialization Format |
| :---- | :---- | :---- | :---- |
| **Research Roadmap** | Essential | Defines the overarching goal and current progress 18 | JSON / Markdown |
| **Current Task Index** | Essential | Prevents the agent from repeating completed steps 13 | Integer / Key-Value |
| **Key Findings Log** | Essential | Stores the "distilled" knowledge acquired so far 15 | Markdown / Episodic Log |
| **Full Tool Logs** | Reconstructible | Can be summarized; raw logs consume too many tokens 15 | Summarized Narrative |
| **Environment State** | Essential | Active SSH sessions, tmux IDs, and file pointers 20 | Environment variables / YAML |

Research from 2025 indicates that serialization format significantly impacts LLM performance. The QASU benchmark demonstrated that structured formats like HTML or JSON can improve answer lookup and structural understanding by up to 8.8% compared to plain text or Turtle (TTL) formats.22 For a research agent, a "progress file" (often named claude-progress.json or research-state.md) serves as the "anchor" for resumption.18

### **The Git-Centric State Pattern**

An innovative pattern involves utilizing Git as a primary state management tool. By treating the research environment as a repository, the agent can commit its progress, code, and notes incrementally. This creates an auditable "timeline" of the research. In this model, the serialized state includes the current Git commit hash. Upon resumption, the agent reads the commit logs to understand the delta between sessions, allowing for a "time-traveling" recovery if a specific research path proves fruitless.18

## **Hierarchical Memory and Context Window Optimization**

Managing the context window for a task that spans days is a significant engineering challenge. While Claude Sonnet 4.6 and Opus 4.5 support 200,000+ tokens, model performance often degrades significantly between 50,000 and 150,000 tokens—a phenomenon known as "context rot".17

### **The 3-Tier Memory Model**

To maintain infinite-feeling context within a finite window, 2025 architectures employ a tiered memory system.3

1. **Hot Memory (In-Context):** This tier includes the current task description, the system prompt, and the most recent interaction history (typically the last 10-15 turns). It is highly volatile and frequently pruned.3  
2. **Warm Memory (File System):** For agents with computer-use capabilities, the file system serves as a "virtual memory" layer. Tools like grep, ls, and cat allow Claude to "page" through large datasets or codebases without loading them into the active window.23  
3. **Cold Memory (Vector/Relational DB):** Long-term knowledge, such as previous research papers, historical experiment results, and user preferences, is stored in a vector database like Qdrant or Pinecone. This data is retrieved via semantic search only when the agent specifically requests it.3

### **Context Pruning Strategies**

Claude 4 models introduce native tools for context management, such as clear\_tool\_uses\_20250919 and clear\_thinking\_20251015. These tools allow the application to programmatically remove large tool outputs or historical "thinking blocks" from the conversation history while keeping the model's conclusions.15

Another effective strategy is "Hierarchical Summarization," where an independent "Summarizer Agent" periodically compresses the verbose conversation logs into a dense narrative summary. This ensures the "Planner" agent retains the high-level goals and findings without being distracted by the "Researcher" agent's low-level debugging logs.25

## **Multi-Agent Specialization and Handoff Logic**

A critical architectural debate involves the choice between a single "God-Agent" Claude instance and a multi-agent team. In 2025, production data strongly supports the multi-agent approach for long-running research.2

### **Modularity vs. Coherence**

| Metric | Single-Agent Approach | Multi-Agent Specialization |
| :---- | :---- | :---- |
| **Hallucination Rate** | Higher due to context bloat 2 | \~60% Lower due to specialized prompts 2 |
| **Token Efficiency** | Poor; entire history is always present 17 | High; context is isolated per role 19 |
| **Error Recovery** | Difficult; failures can pollute the plan 27 | Reliable;Reviewer can catch Researcher errors 28 |
| **Orchestration** | Simple; single loop 27 | Complex; requires handoff logic 4 |

For an AI Scientist, the Planner, Researcher, and Reviewer should be separate "nodes" in a graph. The Planner maintains the high-level strategy and is shielded from the Researcher's low-level technical failures. The Reviewer agent acts as an independent auditor, often using a higher-temperature setting to find flaws in the Researcher's work. This separation of concerns mirrors professional research teams and prevents the "cascading failure" seen in single-agent systems where a small coding error can cause the entire system to lose sight of the research goal.29

## **Tool Design for Resilience and Reliability**

In a multi-day pipeline, tools are not just API wrappers; they are the mechanism by which the agent interacts with a persistent environment. The design of these tools must prioritize idempotency and structured feedback.31

### **SSH and Terminal Persistence with tmux**

A research agent must often execute long-running scripts or simulations. If the terminal session dies when Claude "goes to sleep," the progress is lost. The use of tmux (Terminal Multiplexer) is the foundational tool for persistence.20

* **tmux Workflow:** The agent interacts with a tmux session rather than a raw bash shell. This allows the host system to wake Claude up, have it attach to the session, inspect the progress of a running script, and detach. This "persistent terminal" approach ensures that background tasks are never interrupted by LLM session cycles.20  
* **MCP SSH Servers:** The Model Context Protocol (MCP) provides a standardized way to connect Claude to remote infrastructure. Tools like claude-ssh-server enable the agent to manage Linux servers, check system status, and upload/download artifacts securely through a unified interface.21

### **Idempotency and Safety**

Tools must be designed to be "idempotent"—meaning they can be called multiple times with the same parameters without unintended side effects. For example, a write\_file tool should include a checksum or a specific line-insertion logic to prevent the agent from accidentally double-appending code during a retry attempt.34

## **Background Monitoring and Wake-up Triggers**

The efficiency of a multi-day pipeline relies on the "Wake-on-Anomaly" or "Wake-on-Completion" pattern. It is economically inefficient to keep a frontier model like Claude Opus active while waiting for a 6-hour simulation to finish. Instead, a hierarchical monitoring system is implemented.29

### **The Sentinel Model Pattern**

A small, local model (e.g., Llama 3 or Gemma) runs as a "Sentinel." This model does not perform reasoning but is trained/prompted for anomaly detection in time-series data or log files.29

1. **Statistical Baseline:** The sentinel establishes a baseline for "normal" operation (e.g., expected CPU usage, log frequency, or growth rate of a data file).  
2. **Detection Logic:** Using statistical methods like Z-score analysis (![][image1]), the sentinel monitors for spikes or drift. If the Z-score exceeds a threshold (typically ![][image2]), an anomaly is flagged.38  
3. **Triggering Claude:** Upon detection, the sentinel sends a webhook to the orchestrator (e.g., LangGraph or PydanticAI), which then "wakes up" the Claude Planner to investigate the root cause.29

This pattern allows the system to remain "dormant" and cheap for 90% of its runtime, only consuming expensive tokens when high-level reasoning is required to handle a deviation from the research plan.38

## **Human-in-the-Loop: Discord Bot Approval Layers**

For high-stakes research, giving an agent full autonomy over sensitive operations (e.g., deleting data, incurring high API costs) is risky. A Discord bot layer provides a seamless "approval gate" for human oversight.41

### **The ApprovalRequired Pattern**

In PydanticAI and LangGraph4j, the ApprovalRequired exception or InterruptionMetadata is used to pause the graph. When an agent proposes a "sensitive" tool call, the following flow occurs:

* **Proposal:** The agent generates a DeferredToolRequest.  
* **Notification:** The system sends a formatted message to a Discord channel via a webhook. This message includes the agent's reasoning, the proposed command, and the estimated impact.42  
* **Persistence:** The entire agent state (including the message history of sub-agents) is saved to a persistent store (e.g., Redis or PostgreSQL).43  
* **Resumption:** Once a human clicks an "Approve" button in Discord, the system retrieves the state, injects the DeferredToolResult(approved=True), and the agent continues its execution.42

This pattern ensures that the agent can run for days with "governed autonomy," where it handles the mundane work independently but waits for human guidance on critical decisions.28

## **Failure Recovery and System Resilience**

In long-running pipelines, the "Crisis of Cascade Failure" is a significant threat. A retry storm—where an agent repeatedly retries a failing tool until it exhausts its token budget—can destroy the project's ROI.3

### **Resiliency Blueprints**

Production systems in 2025 utilize the following "Eight Pillars" of resilience:

| Pillar | Mechanism | Impact |
| :---- | :---- | :---- |
| **Circuit Breakers** | Fails fast when a tool (e.g., web search) times out 3 | Prevents resource exhaustion during downtime. |
| **Backpressure** | Queue system for incoming alerts or tasks 3 | Prevents "sentinel storms" from overwhelming the orchestrator. |
| **Durable Workflows** | Checkpointing state in a DBOS or Temporal store 8 | Guarantees resumption after system-level crashes. |
| **Shadow Mode** | Running agent output against human baselines for validation 3 | Enables safe testing of new research strategies. |
| **Rate Limiting** | Tiered access to LLM APIs based on task priority 3 | Ensures critical Planner tasks have priority over Researcher tasks. |
| **Model Fallbacks** | Automatically switching to a secondary model if primary fails 28 | Maintains system uptime during provider outages. |

## **Lessons from Existing Long-Running Systems**

Beyond Sakana AI's *The AI Scientist*, several other systems have provided critical insights into the realities of multi-day agentic workflows.

### **Claude Code and Cursor: Context Management**

The development of Claude Code and the Cursor IDE has revealed that "overwrought" memory systems—such as those relying purely on complex vector embeddings—often fail to provide the precision required for deep technical work. Instead, these systems have pivoted toward "Unix-based Memory," where the agent is given powerful primitive tools (grep, find, sed) to manage its own memory within the file system. The insight is that the agent is often better at "paging" its own context than a top-down algorithm.17

### **Anomaly Hunter: Consensus over Single-Model**

The *Anomaly Hunter* project demonstrated that multi-agent consensus is far more reliable for research than single-model analysis. By having a "Pattern Analyst" (GPT-5), a "Change Detective" (Claude 4.5), and a "Root Cause Agent" (Claude 4.5) work in parallel, the system achieved a 100% detection rate on critical anomalies. When agents disagreed, the orchestrator flagged the uncertainty for human review, dramatically reducing false positives.29

### **Common Failure Patterns in Production**

1. **The "Declare Victory Too Early" Bug:** Agents often mark a research task as complete if they find a superficial answer. Solution: Implementing a "feature list" JSON file that must be self-verified with tests before the session can close.18  
2. **The "Infinite Tool Loop":** Agents may get stuck repeatedly calling ls on a directory they cannot access. Solution: Implementing a tool-call counter in the state schema that triggers a Reviewer intervention if the same tool is called 5+ times consecutively without state change.2  
3. **The "Environment Drift" Issue:** Over days, the local file system can become cluttered with temp files, confusing the agent. Solution: Periodic "cleanup nodes" in the graph that prune the file system and update the progress summary.18

## **Conclusion: The Blueprint for the Autonomous Scientist**

The construction of a long-running, multi-stage research pipeline with Claude requires a departure from traditional "scripted" logic toward a "state machine" logic. By utilizing LangGraph or PydanticAI for durable execution, implementing a 3-tier memory model to combat context rot, and employing local sentinel models for cheap background monitoring, organizations can build systems that execute high-level research with minimal human intervention. The transition to production-grade agents is ultimately an exercise in distributed systems engineering, where the LLM provides the "brain" but a robust, stateful infrastructure provides the "nervous system" required for sustained, autonomous performance.1

#### **引用的著作**

1. The State of Agentic AI in 2025: A Year-End Reality Check \- Arion Research, 檢索日期：3月 18, 2026， [https://www.arionresearch.com/blog/the-state-of-agentic-ai-in-2025-a-year-end-reality-check](https://www.arionresearch.com/blog/the-state-of-agentic-ai-in-2025-a-year-end-reality-check)  
2. AI Agent Architecture in 2025: Core Principles, Tools, and Real-World Use Cases \- Vigyaan, 檢索日期：3月 18, 2026， [http://vigyaan.com/2025/12/ai-agent-architecture-in-2025-core-principles-tools-and-real-world-use-cases/](http://vigyaan.com/2025/12/ai-agent-architecture-in-2025-core-principles-tools-and-real-world-use-cases/)  
3. Building Production-Grade AI Agents in 2025: The Complete ..., 檢索日期：3月 18, 2026， [https://pub.towardsai.net/building-production-grade-ai-agents-in-2025-the-complete-technical-guide-9f02eff84ea2](https://pub.towardsai.net/building-production-grade-ai-agents-in-2025-the-complete-technical-guide-9f02eff84ea2)  
4. Stop wasting time choosing the wrong AI framework\! LangGraph vs. CrewAI, 檢索日期：3月 18, 2026， [https://aipmbydesign.substack.com/p/stop-wasting-time-choosing-the-wrong](https://aipmbydesign.substack.com/p/stop-wasting-time-choosing-the-wrong)  
5. Pydantic AI vs LangGraph: Features, Integrations, and Pricing ..., 檢索日期：3月 18, 2026， [https://www.zenml.io/blog/pydantic-ai-vs-langgraph](https://www.zenml.io/blog/pydantic-ai-vs-langgraph)  
6. Mastering LangGraph State Management in 2025 \- Sparkco AI, 檢索日期：3月 18, 2026， [https://sparkco.ai/blog/mastering-langgraph-state-management-in-2025](https://sparkco.ai/blog/mastering-langgraph-state-management-in-2025)  
7. LangGraph vs. CrewAI: Which Framework Should You Choose for Your Next AI Agent Project? | by Shashank Shekhar pandey | Medium, 檢索日期：3月 18, 2026， [https://medium.com/@shashank\_shekhar\_pandey/langgraph-vs-crewai-which-framework-should-you-choose-for-your-next-ai-agent-project-aa55dba5bbbf](https://medium.com/@shashank_shekhar_pandey/langgraph-vs-crewai-which-framework-should-you-choose-for-your-next-ai-agent-project-aa55dba5bbbf)  
8. Durable Execution \- Pydantic AI, 檢索日期：3月 18, 2026， [https://ai.pydantic.dev/durable\_execution/overview/](https://ai.pydantic.dev/durable_execution/overview/)  
9. Prefect \- Pydantic AI, 檢索日期：3月 18, 2026， [https://ai.pydantic.dev/durable\_execution/prefect/](https://ai.pydantic.dev/durable_execution/prefect/)  
10. Temporal \- Pydantic AI, 檢索日期：3月 18, 2026， [https://ai.pydantic.dev/durable\_execution/temporal/](https://ai.pydantic.dev/durable_execution/temporal/)  
11. The 2026 AI Agent Framework Decision Guide: LangGraph vs CrewAI vs Pydantic AI, 檢索日期：3月 18, 2026， [https://dev.to/linou518/the-2026-ai-agent-framework-decision-guide-langgraph-vs-crewai-vs-pydantic-ai-b2h](https://dev.to/linou518/the-2026-ai-agent-framework-decision-guide-langgraph-vs-crewai-vs-pydantic-ai-b2h)  
12. What's the best way to build conversational agents in 2025? LLMs, frameworks, tools?, 檢索日期：3月 18, 2026， [https://www.reddit.com/r/AI\_Agents/comments/1mfmgdf/whats\_the\_best\_way\_to\_build\_conversational\_agents/](https://www.reddit.com/r/AI_Agents/comments/1mfmgdf/whats_the_best_way_to_build_conversational_agents/)  
13. Developer's guide to multi-agent patterns in ADK, 檢索日期：3月 18, 2026， [https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/)  
14. langchain-ai/langgraph: Build resilient language agents as graphs. \- GitHub, 檢索日期：3月 18, 2026， [https://github.com/langchain-ai/langgraph](https://github.com/langchain-ai/langgraph)  
15. Memory & context management with Claude ... \- Claude Console, 檢索日期：3月 18, 2026， [https://platform.claude.com/cookbook/tool-use-memory-cookbook](https://platform.claude.com/cookbook/tool-use-memory-cookbook)  
16. Memory and State in LLM Applications \- Arize AI, 檢索日期：3月 18, 2026， [https://arize.com/blog/memory-and-state-in-llm-applications/](https://arize.com/blog/memory-and-state-in-llm-applications/)  
17. Anthropic: Building Production AI Agents: Lessons from Claude Code and Enterprise Deployments \- ZenML LLMOps Database, 檢索日期：3月 18, 2026， [https://www.zenml.io/llmops-database/building-production-ai-agents-lessons-from-claude-code-and-enterprise-deployments](https://www.zenml.io/llmops-database/building-production-ai-agents-lessons-from-claude-code-and-enterprise-deployments)  
18. Effective harnesses for long-running agents \\ Anthropic, 檢索日期：3月 18, 2026， [https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)  
19. The ultimate LLM agent build guide \- Vellum AI, 檢索日期：3月 18, 2026， [https://www.vellum.ai/blog/the-ultimate-llm-agent-build-guide](https://www.vellum.ai/blog/the-ultimate-llm-agent-build-guide)  
20. tmux Workflow for AI Coding Agents \- Agent of Empires, 檢索日期：3月 18, 2026， [https://www.agent-of-empires.com/guides/tmux-ai-coding-workflow/](https://www.agent-of-empires.com/guides/tmux-ai-coding-workflow/)  
21. Claude SSH Server | MCP Servers \- LobeHub, 檢索日期：3月 18, 2026， [https://lobehub.com/mcp/jasondsmith72-claude-ssh-server](https://lobehub.com/mcp/jasondsmith72-claude-ssh-server)  
22. Questionnaire meets LLM: A Benchmark and Empirical Study of Structural Skills for Understanding Questions and Responses \- arXiv, 檢索日期：3月 18, 2026， [https://arxiv.org/html/2510.26238v1](https://arxiv.org/html/2510.26238v1)  
23. Hierarchical Memory Management In Agent Harnesses \- Arize AI, 檢索日期：3月 18, 2026， [https://arize.com/blog/hierarchical-memory-management-in-agent-harnesses/](https://arize.com/blog/hierarchical-memory-management-in-agent-harnesses/)  
24. Hierarchical Memory Claude Code Skill | AI Persistence \- MCP Market, 檢索日期：3月 18, 2026， [https://mcpmarket.com/tools/skills/hierarchical-memory-system](https://mcpmarket.com/tools/skills/hierarchical-memory-system)  
25. NexusSum: Hierarchical LLM Agents for Long-Form Narrative Summarization \- arXiv.org, 檢索日期：3月 18, 2026， [https://arxiv.org/html/2505.24575v1](https://arxiv.org/html/2505.24575v1)  
26. llm\_tools\_with\_schema.md \- Gist \- GitHub, 檢索日期：3月 18, 2026， [https://gist.github.com/imaurer/d6c033d436177b69ac0ceac8e6816df4](https://gist.github.com/imaurer/d6c033d436177b69ac0ceac8e6816df4)  
27. Agent system design patterns | Databricks on AWS, 檢索日期：3月 18, 2026， [https://docs.databricks.com/aws/en/generative-ai/guide/agent-system-design-patterns](https://docs.databricks.com/aws/en/generative-ai/guide/agent-system-design-patterns)  
28. AI Agents in 2025: A Practical Guide for Developers, 檢索日期：3月 18, 2026， [https://www.getmaxim.ai/articles/ai-agents-in-2025-a-practical-guide-for-developers/](https://www.getmaxim.ai/articles/ai-agents-in-2025-a-practical-guide-for-developers/)  
29. bledden/anomaly-hunter: Multi-agent anomaly detection ... \- GitHub, 檢索日期：3月 18, 2026， [https://github.com/bledden/anomaly-hunter](https://github.com/bledden/anomaly-hunter)  
30. Comparing the Top 5 AI Agent Architectures in 2025: Hierarchical, Swarm, Meta Learning, Modular, Evolutionary \- MarkTechPost, 檢索日期：3月 18, 2026， [https://www.marktechpost.com/2025/11/15/comparing-the-top-5-ai-agent-architectures-in-2025-hierarchical-swarm-meta-learning-modular-evolutionary/](https://www.marktechpost.com/2025/11/15/comparing-the-top-5-ai-agent-architectures-in-2025-hierarchical-swarm-meta-learning-modular-evolutionary/)  
31. Best Practices to Build LLM Tools in 2025 \- Tech Info, 檢索日期：3月 18, 2026， [https://techinfotech.tech.blog/2025/06/09/best-practices-to-build-llm-tools-in-2025/](https://techinfotech.tech.blog/2025/06/09/best-practices-to-build-llm-tools-in-2025/)  
32. Agentic AI: The Agent Loop & Tools for Building Autonomous Agents \- You.com, 檢索日期：3月 18, 2026， [https://you.com/resources/the-agent-loop-how-ai-agents-actually-work-and-how-to-build-one](https://you.com/resources/the-agent-loop-how-ai-agents-actually-work-and-how-to-build-one)  
33. mixelpixx/SSH-MCP: A Model Context Protocol (MCP) server that provides SSH access to remote servers, allowing AI tools like Claude Desktop or VS Code to securely connect to your VPS. · GitHub, 檢索日期：3月 18, 2026， [https://github.com/mixelpixx/SSH-MCP](https://github.com/mixelpixx/SSH-MCP)  
34. An Autonomous, Agentic, AI Assistant, Meet Alfred and this is how I built him. \- Dev.to, 檢索日期：3月 18, 2026， [https://dev.to/joojodontoh/an-autonomous-agentic-ai-assistant-meet-alfred-and-this-is-how-i-built-him-4e7m](https://dev.to/joojodontoh/an-autonomous-agentic-ai-assistant-meet-alfred-and-this-is-how-i-built-him-4e7m)  
35. How Do Autonomous AI Agents Transform Development Workflows | Augment Code, 檢索日期：3月 18, 2026， [https://www.augmentcode.com/learn/how-do-autonomous-ai-agents-transform-development-workflows](https://www.augmentcode.com/learn/how-do-autonomous-ai-agents-transform-development-workflows)  
36. GitHub \- wonderwhy-er/DesktopCommanderMCP: This is MCP server for Claude that gives it terminal control, file system search and diff file editing capabilities, 檢索日期：3月 18, 2026， [https://github.com/wonderwhy-er/DesktopCommanderMCP](https://github.com/wonderwhy-er/DesktopCommanderMCP)  
37. How to Implement Effective Real-Time Monitoring for AI Agents | by Navya \- Medium, 檢索日期：3月 18, 2026， [https://medium.com/@yadav.navya1601/how-to-implement-effective-real-time-monitoring-for-ai-agents-fa2c2ff743c5](https://medium.com/@yadav.navya1601/how-to-implement-effective-real-time-monitoring-for-ai-agents-fa2c2ff743c5)  
38. Building an AI Agent to Detect and Handle Anomalies in Time-Series Data, 檢索日期：3月 18, 2026， [https://towardsdatascience.com/building-an-ai-agent-to-detect-and-handle-anomalies-in-time-series-data/](https://towardsdatascience.com/building-an-ai-agent-to-detect-and-handle-anomalies-in-time-series-data/)  
39. How does AI Agent perform real-time anomaly detection and alarm? \- Tencent Cloud, 檢索日期：3月 18, 2026， [https://www.tencentcloud.com/techpedia/126638](https://www.tencentcloud.com/techpedia/126638)  
40. CodeAD: Synthesize Code of Rules for Log-based Anomaly Detection with LLMs \- arXiv.org, 檢索日期：3月 18, 2026， [https://arxiv.org/html/2510.22986v1](https://arxiv.org/html/2510.22986v1)  
41. State of Agentic AI in 2025: Challenges, Opportunities, and Enterprise Adoption \- Syren, 檢索日期：3月 18, 2026， [https://syrencloud.com/state-of-agentic-ai-2025/](https://syrencloud.com/state-of-agentic-ai-2025/)  
42. LangGraph4j \- Implementing Human-in-the-Loop at ease | Welcome to Bartolomeo Blog, 檢索日期：3月 18, 2026， [https://bsorrentino.github.io/bsorrentino/ai/2025/07/13/LangGraph4j-Agent-with-approval.html](https://bsorrentino.github.io/bsorrentino/ai/2025/07/13/LangGraph4j-Agent-with-approval.html)  
43. Human in the Loop Approval for Multi Agent Systems · Issue \#3274 \- GitHub, 檢索日期：3月 18, 2026， [https://github.com/pydantic/pydantic-ai/issues/3274](https://github.com/pydantic/pydantic-ai/issues/3274)  
44. DBOS \- Pydantic AI, 檢索日期：3月 18, 2026， [https://ai.pydantic.dev/durable\_execution/dbos/](https://ai.pydantic.dev/durable_execution/dbos/)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHsAAAAYCAYAAADap4KLAAAEoElEQVR4Xu2Za6hOWRjHH7nkmnGJkREmX4RMuZRy+WI0k3xBofFBCYUvaGaK1EG+KHKNcUlM4oNCucyUdEyKoqSIRuqQ8kGTmqIkl+f3rnc56zx77W2f9xz7Pe/p/dU/+6y1937XXs+znudZi0idOnXqdBS6qgaoutiOGqIt39BHKnuu5uiu2q6abztqDIy1QbWufJ2Xoao9ql62oxIWqz4Geq96XhbXtB36fHfxMEG7pHUT1FHBcU+qFtiODLDPattYCUzgcdUz1Y/iQo1nquqV6qqqf9BeJONUt1WjbUcNM151UzXCdkToptqnGms7KmG4uB9mUkN4+RPVv6qRpq8ocMT9ZXWGVe3BgKdVDaY9BnY4KO6ZNjNbtcm0YVyM/FI12fQVCY7IOBhjZ+MXcRGLgi0LwjdhvF2YIy1DBOGasE34JoxXE4xMdPnOdpQh/80si2tS0CTV9PJ10UyQZBRkXFTSlomqp6optiOAguyoZKcw3k8BN8zom/CmGP7lFGWtKSC+Fr+rGlV9TTswqedUK1V7VddVR1S/qv5W7Wy+tRCIQk2qjUGbD9fnVT2CdsAgGDtrhzFNtUPiKQwH2i3NBbQVCzbmZCXwkMPibvxN4j+QxhjVHXFFXl4tKT2ZzQnVWUnmK5yS3QG/C6zm1+JyINHgg7iiszXf0FaIJm9VPwdtrDgiU+gAHhy4UZxDp0F6/ck2SnP0vauaIc7xT6n+E+cgOFJsgZRgUjAwkxQamkn+QZwjVAOMjSwYmb2qhwlmoplwvJnVnhb6IS30xTRE8qUEjPZC9X3QxnhwwljN4Y3N+UEMcjnfPti0YxtW9H1xY/Pg8P9LS2dLwMOLxIUDVnZoWAZO2W9XVlGkGdvChDWJC6V5wIH51jziMGNU6al0eqouSTJ0xhzA441N2oyBgzTYRnH1FSt4rWnHsd6p5pn2FpCbMXRsL80LV5m2GHg+XmZXRZZSw0xAHmP7SYuF+6Lw+TpcpYyFMVkH8GSFcRYguXqa7RBnzDeSLOywE06Quh/3hyb/qL41feSBG+IOAL4EHzNXtbAVSh1UAJMXmyxC9Blxh0De08NJWyFul1EUvk4Ii63QAQaJKxh7B/2EabZe64M2D89Sc8QWBMZ+Km7BeKhh/hIXJaIO7/fSKNwuEMZnqR6Ke0G7nMdWCN76QJJ5iwmikFyuWla+9uGLb/lT3AQXBY7GGNg7g6+BaMMBKLLCGgNwWIq3WD7POh5l8T0q/wv+t+5JcttXgpVyRZLlupXNC0VD0fFYklGA/MTHUYEeV20T5xTHVBckef/XxOdr//8Jm1UXVWvERSX62H7ZgpFvYMy2zmBlHpD0iIpxcYQ74mqKRtUfqoHBPTUJNcQtaV4xIYQ4Vq/fOdi/iyIM14yB8IoDgK9l/N8hDeKcwIbdvEUx7wx/q1OwVHVZqptOsiAMs6oztzwGnPKauD2yhXqj3Y5Haw1WC2GRYqwjkrW9SgMH5lDInl/kOR7t9FB4kIujBUiVwTgc2+YNp2PE1UuxbyFPb5XiU1GHg6JriyTPmKsNeTmvcfqJy+22WPOwXZxlG+vUqVOnJZ8Apd/gPUG8Xj4AAAAASUVORK5CYII=>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAD0AAAAYCAYAAABJA/VsAAAClElEQVR4Xu2XT4hNURzHv0KRfwtSSs2MUEo2xFbIZjI0FCUbs2AhiiJiJUligWYiTUnZmJoFxUIRG8vZjIVYkA0lGzbkz/fb7x7OPffc5/6rO/K+9el1z3vvvvO555zfOQ/o5v/LPDI9bKyYmWRO2DgVc5YsCRsrZi05GDZOxXSS7iPvyE+PD+Qt+ZxcvySLk8+3La0Z20+GyRWyFTb7MukkPUC+kZNIT9sF5BH5RNZ77W1KzyV3ySHYIKwjr8kDWH9TyZOeRkaRlZD8bfKd7AzeKyqtEVEtaTJbyA8yQmYkbedgs/GA+5BLnvQimLT/lDRVbsBudAz2YPwUlZ5NLpH7ZA2y96mSjbCBGCezkrZTsL4eTa5/J0+6l+zwrtWx47CnqddYR4tKuywkF8kzsgn1dhH1R/dzwnqwD8kXWL9SyZP2oxvuhj1JjXS0OKC8tMt8cpo8J9tRT17R94dgwlrjmQEqIq21K2EVr0xR8FJV2kX14gh5QfbDRqts9PvaXd6TM8g5N/xNWtVZVToUXgFb937qSrtIVtJ15PWdMVgFXxW811F6OWwfFj1eu6rjVbLMa1Oakla0hPaRV0jXljIZhBWyewgeXJ60JCUb7sXKanILf4qGSxPSbpQnkteio7yZXCZLvTb1R+v6DQLHmLR/+ND+58dtWyoQYepIu/WsYrYH+cUyFh1MnsBG9YTXvi1pm0SwFENpJxUePlQBe8kd8hE22mGqSDexbWm53YTNTO37ivorN3emSCWUPoz0WTuG9r/YtCsjrd+8Rh6TDYhsKyWjaf0UdhTdS86Tr+QCIrMmlK6TotLq4HU0dxpz0SxRpd4Fm9qaRdG0Id16utI1889ID6HD3C+ZlbD/4N1002J+ASpIf187na8XAAAAAElFTkSuQmCC>