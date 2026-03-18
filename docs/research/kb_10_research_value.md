# KB-10: Automated Research Value Assessment

**Source:** Deep Research on research value judgment, DeepReviewer-14B, S2AG impact scoring, routing architecture (2025–2026)

---

## Key Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | **Value assessment architecture** | 5-stage hierarchical pipeline appended after statistical validation; NOT a single gate | Different stages have different cost/latency profiles; cheap filters run first to protect expensive evaluators |
| 2 | **Local review model** | DeepReviewer-14B (Fast Mode) for routine loops | 80–88% win rate vs proprietary models; 44.8% MSE reduction vs larger open models; resilient against "smart plagiarism" |
| 3 | **Minimum Viable Value Check (MVVC)** | Local embedding cosine similarity + single-shot LLM score (1–5) before DeepReviewer | Near-zero latency; gates access to expensive 14B model and S2AG API calls |
| 4 | **Empirical Supremacy override** | If empirical delta > 15% absolute over SOTA → override any linguistic CRITICAL_FAIL to PARTIAL_FAIL | False negatives (discarding genuine breakthroughs) are more costly than false positives; LLM reviewers penalize radical novelty |
| 5 | **PARTIAL_FAIL = human escalation** | PARTIAL_FAIL routes to human-in-the-loop, NOT back to Researcher | Value judgment is subjective; borderline or anomalous results need human decision, not automated retry |
| 6 | **5 measurable value dimensions** | Performance + Novelty + Generalizability + Efficiency + Simplicity | From 226,600 abstract analysis (arXiv 2502.16390); all 5 directly mappable to automated signals in LangGraph |
| 7 | **Pre vs post experiment distinction** | Pre-experiment = idea novelty (semantic distance); Post-experiment = value = Novelty × Significance (empirically grounded) | A novel idea can be worthless; an incremental idea can be highly valuable if it solves a real problem |
| 8 | **S2AG SPECTER2 "sweet spot"** | Moderate cosine distance to SOTA centroid = optimal value signal; too close = derivative, too far = irrelevant | S2AG `influentialCitationCount` + SPECTER2 embedding distance together give field-context signal |
| 9 | **Value assessment trigger** | Only triggered after Stage 1 (statistical validation) passes | Running 14B model or S2AG API on every epoch is infeasible; cost = $10–15/paper iteration |
| 10 | **Andrew Ng / AI Fund** | No dedicated DL research value tool found; Octagon AI is financial sector only | The "吳恩達有做" claim appears to refer to general agentic research tooling, not scientific value scoring specifically |

---

## Updated Reviewer Pipeline (5 Stages)

The Reviewer subgraph from KB-08 now has 2 additional stages after statistical validation:

```
Stage 1: Statistical_Validation (KB-08)
  → FAIL: immediate CRITICAL_FAIL

Stage 2: MVVC_Filter [NEW]
  → local embedding cosine similarity vs. cached top-cited DL papers
  → single-shot Sentinel LLM score (1-5): performance + novelty + simplicity
  → score < 3: immediate CRITICAL_FAIL

Stage 3: DeepReviewer_Eval [NEW]
  → DeepReviewer-14B, Fast Mode (~3k output tokens)
  → score < 4: CRITICAL_FAIL
  → score 4-6: PARTIAL_FAIL (human escalation)
  → score > 6: proceed to Stage 4

Stage 4: S2AG_Impact_Check [NEW]
  → S2AG Recommendations API: find nearest papers in last 24 months
  → check influentialCitationCount of neighbors
  → SPECTER2 cosine distance to SOTA centroid
  → low influence neighborhood: PARTIAL_FAIL
  → moderate distance (sweet spot): proceed

Stage 5: Empirical_Supremacy Override [NEW]
  → if statistical delta > 15% absolute over SOTA baseline:
    override any prior CRITICAL_FAIL → PARTIAL_FAIL (human review)
  → prevents suppression of genuine breakthroughs

Final: PASS → Writer subgraph
       PARTIAL_FAIL → package reports → human-in-the-loop
       CRITICAL_FAIL → log to experimentation memory → terminate
```

---

## 5 Dimensions of Research Value (DL Domain)

From analysis of 226,600 CS abstracts (arXiv 2502.16390):

| Dimension | Automated Signal | Routing Impact |
|-----------|-----------------|----------------|
| **Performance** | Statistically significant delta over baseline (already in KB-08) | Core gate; zero delta = CRITICAL_FAIL |
| **Novelty** | SPECTER2 embedding distance to nearest neighbors in S2AG | Too close = derivative; too far = irrelevant |
| **Generalizability** | Variance of metrics across multiple evaluation benchmarks | High mean + low variance = high value; single-dataset success = PARTIAL_FAIL |
| **Efficiency** | FLOPs / latency / memory / parameter count reduction | Quantitative reduction = value multiplier |
| **Simplicity** | Inverse of lines-of-code added + new hyperparameters introduced | Massive code delta + marginal gain = PARTIAL_FAIL |

**Key rule:** High architectural complexity + marginal performance gain = PARTIAL_FAIL (flag for human), not PASS.

---

## DeepReviewer-14B Details

- **Base:** Phi-4 architecture
- **Training:** DeepReview-13K (13,378 fine-grained review reasoning chains)
- **Inference modes:**
  - Fast Mode: ~3k tokens; summary + numerical scores + key points (use for routine loops)
  - Standard Mode: multi-reviewer perspectives + self-verification
  - Best Mode: exhaustive analysis (use for final manuscript before submission)
- **Performance:** 80.20–88.21% win rate vs. proprietary reasoning models; 44.8% MSE reduction vs. larger open models
- **Anti-gaming:** Resilient against "smart plagiarism" (agent masking unoriginal ideas with terminological obfuscation)
- **Decision accuracy:** 64.06% on historical accept/reject task
- **HuggingFace:** `WestlakeNLP/DeepReviewer-14B`
- **VRAM requirement:** ~11–12GB (14B parameter model) → runs on same tier as Qwen 2.5 Coder 14B Sentinel

**Important:** DeepReviewer requires dedicated GPU — cannot share GPU with active training. Schedule after training completes, or route to CPU-only node with latency tolerance.

---

## S2AG Integration

**Fields to use:**
- `influentialCitationCount` / `isInfluential`: whether a paper had methodological impact (not just background mention)
- `SPECTER2` embeddings: semantic position in research space
- Recommendations API: find nearest papers by abstract/methodology similarity

**"Shadow citation profile" pattern:**
1. Generate abstract + intro of completed experiment
2. Query S2AG Recommendations API for nearest papers (last 24 months)
3. Check `influentialCitationCount` of those neighbors
   - Neighbors have high influential citations + our experiment improves on them → high potential impact
   - Neighbors are obscure/uncited → research direction may be saturated or abandoned

**SPECTER2 "sweet spot":**
- Too close to SOTA centroid (cosine similarity > 0.95) → derivative work → PARTIAL_FAIL
- Moderate distance (0.6–0.85) → novel but relevant → proceed
- Too far (< 0.4) → potentially irrelevant or out-of-distribution → PARTIAL_FAIL

---

## Pre vs Post Experiment Distinction

**Pre-experiment (Idea Novelty Checker, KB-04):**
- Input: idea description before experiment
- Method: semantic distance from literature, keyword divergence
- Limitation: "An idea may be conceptually unique simply because it is fundamentally flawed"

**Post-experiment (this KB):**
- Input: actual experimental results + generated abstract
- Method: empirical delta × novelty signal
- Value = Novelty × Significance (empirically proven)
- Can override pre-experiment assessment: a low-novelty idea that solves a real convergence problem has high post-experiment value

**Historical example cited:** Feedback alignment as biologically plausible backpropagation alternative — low novelty claim (already a known direction) but enormous practical value once empirically proven.

---

## Empirical Supremacy Doctrine

**Problem:** LLM reviewers are biased toward conventional research. A genuinely breakthrough architecture will look "unusual" and get penalized by embedding distance and LLM scores.

**Solution:** If `statistical_delta > 0.15` (15% absolute improvement over SOTA):
- Override Stage 3 CRITICAL_FAIL → PARTIAL_FAIL
- Override Stage 4 CRITICAL_FAIL → PARTIAL_FAIL
- Always escalate to human regardless of linguistic evaluation scores

**Rationale:** False negatives (discarding a breakthrough) are more costly than false positives (human reviews something that turns out mediocre). The human can always reject; the system cannot un-discard.

---

## Minimum Viable Value Check (MVVC) Details

Runs before DeepReviewer to gate expensive computation:

**Step 1 — Embedding check (local, ~50ms):**
- Extract core contribution string (method name + performance claim)
- Generate lightweight embedding (can use Sentinel LLM or cached model)
- Cosine similarity vs. locally cached vector DB of top-cited DL papers (last year)
- Flag if similarity > 0.98 (near-copy)

**Step 2 — Single-shot score (Sentinel LLM, ~2s):**
```
Prompt: "Baseline: {metric}={baseline_value}. New result: {metric}={new_value}.
Method: {one_sentence_description}.
Rate 1-5: 1=trivial, 3=solid incremental, 5=major advance.
Output only the integer."
```
- Score < 3 → CRITICAL_FAIL (save DeepReviewer GPU cycles)
- Score ≥ 3 → proceed to DeepReviewer

**Cost:** Near-zero additional compute. Uses already-running Sentinel model.

---

## Routing Summary (Combined KB-08 + KB-10)

| Condition | Stage | Routing |
|-----------|-------|---------|
| Stat test fails (no significant delta) | 1 | CRITICAL_FAIL |
| MVVC score < 3 (trivial result) | 2 | CRITICAL_FAIL |
| Data leakage detected | 1 | CRITICAL_FAIL |
| Baseline sandbagging detected | 1 | CRITICAL_FAIL |
| DeepReviewer score < 4 | 3 | CRITICAL_FAIL |
| DeepReviewer score 4–6 (borderline) | 3 | PARTIAL_FAIL → human |
| S2AG: low-impact field / derivative | 4 | PARTIAL_FAIL → human |
| Delta > 15% (Empirical Supremacy) | 5 | Override → PARTIAL_FAIL → human |
| All stages pass, score > 6 | — | PASS → Writer |

**On CRITICAL_FAIL:** Log hyperparameter trajectory to experimentation memory (KB-07 EvoScientist pattern) to prevent re-exploring this dead-end.

**On PARTIAL_FAIL:** Package DeepReviewer report + S2AG analysis + statistical metrics → human review via Discord HiTL or web dashboard.

---

## What Andrew Ng Actually Built

Octagon AI (AI Fund portfolio): automated investment research and due diligence for financial sector. Architecture: recursive agentic reasoning loops for synthesizing market trends and prioritizing signals over noise. **Not** a scientific research value tool. The general approach (agentic triage of value signals) is analogous but the domain is finance, not ML research.

No dedicated DL research value scoring tool was found from AI Fund or DeepLearning.AI in 2025–2026.

---

*Raw deep research content below.*

---

# **Automated Research Value Assessment in Autonomous Deep Learning Architectures: A 2025–2026 Structural Analysis and Integration Strategy**

## **1. The Evolution of the Autonomous Reviewer Ecosystem**

The transition of artificial intelligence from an assistive analytical instrument to an autonomous scientific agent represents a fundamental paradigm shift in computational research. Within the architecture of autonomous scientific systems, the Reviewer stage has traditionally been restricted to verifying methodological soundness, statistical validity, and execution integrity. However, as autonomous systems achieve the capacity to execute multi-agent, end-to-end research pipelines, the sheer volume of generated output necessitates a paradigm shift from simple verification to sophisticated research value judgment.

Assessing research value requires determining whether an empirically validated result is sufficiently novel, significant, and impactful to warrant publication or further computational investment. It requires the system to mirror the value-laden judgments of human peer reviewers and program committees. The absence of this capability leads to the proliferation of methodologically sound but scientifically trivial outputs.

## **2. Evaluation of Existing Tools, Systems, and Paradigms**

### **2.1. Commercial Trajectories and Venture-Backed Evaluation Tools**

The commercial sector, notably led by venture studios such as the AI Fund, has heavily prioritized the development of agentic workflows capable of autonomous evaluation and prioritization. A primary example within the AI Fund portfolio is Octagon AI, a platform engineered to conduct AI-powered investment research and due diligence. While specifically targeted at the financial sector to synthesize market trends and optimize investment portfolios, the underlying architecture of Octagon AI demonstrates the viability of automated value prioritization.

The core philosophy driving these developments is the shift from single-prompt generation to recursive, agentic reasoning loops. Models fine-tuned via reinforcement learning to generate internal reasoning traces prior to outputting evaluations have demonstrated remarkable capabilities. Modern reasoning models dramatically improve performance on complex evaluations by repeatedly generating, evaluating, and refining outputs before delivering a final verdict. When these models are deployed in multi-agent configurations, token usage scales exponentially, allowing the system to execute breadth-first exploration of literature to validate the novelty and strategic value of an idea.

### **2.2. Value Judgment in Autonomous AI Scientist Frameworks**

The foundational "AI Scientist" framework introduced end-to-end automated discovery, generating hypotheses, executing code, and simulating a review process. Its successor, Sakana AI v2, incorporates agentic tree search to explore alternative research trajectories. Evaluations of these systems reveal that workflows utilizing recursive decomposition and long-context multimodal processing achieve high mean novelty scores, occasionally reaching 4.17 out of 5, compared to simple reflection-based iterative refinement which scores significantly lower. However, external audits indicate a severe vulnerability: while the proposed ideas appear novel to automated novelty checkers, the system frequently struggles with implementation capability. Audits revealed a forty-two percent failure rate in experiment execution, alongside frequent fabrication of numerical outcomes and hallucinated citations. This disconnect highlights the critical need to separate pre-experiment idea novelty from post-experiment scientific value within the Reviewer stage.

To address the limitations of static pipelines and repetitive failures, the EvoScientist framework introduces a self-evolving multi-agent system designed to learn from historical context. EvoScientist employs an Evolution Manager Agent that distills interaction histories into two distinct persistent memory modules: an ideation memory and an experimentation memory. By maintaining a persistent record of both successful innovations and failed directions, EvoScientist continuously refines its internal value judgment. When an experimental trajectory consistently fails to produce meaningful performance deltas, the system routes the trajectory to termination rather than pursuing incremental, valueless tweaks. This architecture allows EvoScientist to outperform commercial baselines in generating ideas that are not merely novel, but feasible and highly relevant to the prevailing research landscape.

The Jr. AI Scientist system approaches the problem of value judgment by constraining the boundaries of exploration. It begins with a human-provided baseline paper, analyzes its limitations, and formulates hypotheses strictly aimed at extending or improving that specific algorithmic foundation. When evaluated by automated reviewers, Jr. AI Scientist outputs achieved an average score of 5.75 out of 10, significantly outperforming earlier fully autonomous systems which averaged between 2.75 and 3.30. By defining research value purely as a positive empirical delta over a known, valuable baseline, Jr. AI Scientist simplifies the routing logic required for manuscript progression.

PaperForge introduces a rigorous, production-grade five-phase pipeline. The value judgment and review process is embedded deeply into the refinement phase of the pipeline, where the system executes dedicated auto-scoring modules. Rather than a soft evaluation based purely on linguistic generation, PaperForge implements hard mathematical quality gates based on configurable metric thresholds. These gates utilize statistical significance testing, including Welch t-tests and Wilcoxon signed-rank tests, to compare the experimental delta against the baseline. If the results do not meet the minimum value threshold required to justify the architectural complexity, the gate halts the pipeline, acting as a hard routing mechanism that prevents the generation of scientifically trivial manuscripts.

### **2.3. Institutional Adoption and Conference Tooling**

A large-scale analysis of the ICLR 2024 and 2025 peer review processes revealed a striking bibliometric finding: large language model-generated reviews demonstrated stronger correlations with post-publication impact metrics, such as five-year citation counts and long-term methodological conventionality, than human reviewer scores. This suggests that contemporary models are highly proficient at capturing signals of conventional scientific merit and predicting future influence based on established paradigmatic trends.

Despite this predictive power, the consensus among traditional conference organizers is to utilize these tools strictly as manuscript quality checkers rather than autonomous gatekeepers, mitigating the risk of intentional manipulation or the suppression of highly unconventional methodologies. In sharp contrast, specialized experimental venues like the Agents4Science conference explicitly require algorithmic authorship and employ fine-tuned frontier models as primary peer reviewers. Acceptance into Agents4Science requires an average automated reviewer decision score exceeding 4.5 on a 6-point scale, establishing a clear mathematical threshold for automated value acceptance that can be seamlessly mirrored in private autonomous research architectures.

### **Table 1: System Analysis and Routing Implications**

| Architectural Feature | Routing Logic Impact | Subgraph Modification | Execution Environment |
| :---- | :---- | :---- | :---- |
| **PaperForge Quality Gates** | Defines empirical value mathematically. Insignificant performance delta = **CRITICAL_FAIL**. | Integrate directly into the existing Reviewer node parallel to statistical validation. | Local execution via standard Python logic routines. |
| **EvoScientist Persistent Memory** | Repeated failures within a specific domain or hyperparameter space = **CRITICAL_FAIL**. | Requires the instantiation of a new Evolution Manager Agent node parallel to the Reviewer. | Local vector database architecture for persistent memory retrieval. |
| **ICLR Impact Correlation** | High predicted future impact = **PASS**. Borderline predictions = **PARTIAL_FAIL**. | Append an "Impact Prediction" sub-node within the Reviewer architecture. | External API call required to access frontier inference models. |
| **Agents4Science Strict Rubric** | Evaluated score below 4.5/6 = **PARTIAL_FAIL** (flag for human escalation). | Augment the Reviewer prompt to explicitly output a standardized integer score. | Local or external depending on the required model weight capacity. |

## **3. Operationalizing "Research Value" in Deep Learning**

### **3.1. The Ten Dimensions of Research Value**

An exhaustive 2025 academic study analyzed 226,600 computer science abstracts across eighty-six publishing venues to extract the fundamental beliefs guiding research attitudes. The resulting framework identifies ten distinct dimensions of research value. For an autonomous agent operating specifically in the deep learning domain, five of these dimensions are paramount and directly mappable to automated evaluation signals within a LangGraph pipeline:

**Performance** stands as the primary driver of value in empirical deep learning. The measurable signal for performance is the mathematical delta over established baselines, validated by the statistical tests already present in the system's Reviewer stage. A result possesses high value if the performance gain is statistically significant and robust across multiple random seeds.

**Novelty** represents the conceptual distance from existing literature. The measurable signal for novelty relies on high-dimensional embedding distance between the generated abstract or methodology and the nearest neighbors in a comprehensive literature graph. Furthermore, structural signals, such as the introduction of a new loss function or a mathematically distinct architecture component, can be extracted and verified via algorithmic parsing of the generated codebase.

**Generalizability** indicates the capacity of a proposed method to perform effectively across diverse datasets or downstream tasks. The measurable signal for this dimension is the variance of performance metrics across multiple evaluation benchmarks. A high mean performance coupled with low cross-task variance mathematically indicates high generalizability, elevating the overall research value of the experiment.

**Efficiency** relates to algorithmic economy and computational frugality. The measurable signals for efficiency are quantitative reductions in floating-point operations per second, inference latency, memory footprint, or parameter counts while maintaining baseline accuracy.

**Simplicity** reflects the academic preference for elegant, easily reproducible solutions over complex, over-engineered architectures. The measurable signal for simplicity exhibits an inverse correlation with the volume of code added or the number of new, highly sensitive hyperparameters introduced to the baseline. An experiment that achieves a minor performance gain through massive architectural bloat possesses remarkably low research value compared to an experiment that achieves the same gain through a singular, elegant mathematical modification.

### **3.2. Differentiating Pre-Experiment Novelty and Post-Experiment Value**

Pre-experiment novelty assessment relies purely on semantic distance, keyword divergence, and logical deduction. It evaluates the proposition by asking if a specific mechanism has been proposed before in the literature. However, extensive benchmark evaluations demonstrate that while language models can generate human-like reasoning about novelty, their judgments often diverge significantly from gold standards when devoid of empirical context. An idea may be conceptually unique simply because it is fundamentally flawed.

Post-experiment value assessment fundamentally alters the judgment matrix because empirical reality acts as an absolute truth-grounding mechanism. An idea that appears highly novel pre-experiment may turn out to be computationally unstable or practically useless. Contemporary studies on large reasoning models reveal that complex, novel architectures can suffer from complete accuracy collapse beyond certain complexities, demonstrating that novelty does not guarantee functional value. Conversely, a seemingly incremental algorithmic tweak that registers low pre-experiment novelty might unlock massive efficiency gains or solve a long-standing convergence issue, representing immense scientific value. The historical discovery of feedback alignment as a biologically plausible alternative to backpropagation exemplifies how mathematically simple, localized learning rules can carry profound significance.

Therefore, post-experiment research value is defined precisely by the intersection of Novelty (the distance from prior work) and Significance (the magnitude of the empirically proven operational delta). A result possesses high research value if and only if the statistical validation proves the hypothesis functions correctly, and the resulting performance or efficiency gains adequately justify the architectural complexity introduced to the codebase.

## **4. Dedicated Evaluation Models and Algorithmic APIs**

### **4.1. The DeepReviewer Architecture**

The most prominent dedicated evaluation model available for local deployment is DeepReviewer-14B. This fourteen-billion-parameter model is built upon the robust Phi-4 base architecture and has been fine-tuned specifically on DeepReview-13K, an expansive dataset containing 13,378 fine-grained review reasoning chains. Its primary function is to simulate a multi-stage, human-like deep thinking process tailored exclusively for academic evaluation and manuscript review.

DeepReviewer-14B features highly controllable test-time scaling via three distinct inference modes. Fast Mode generates a rapid summary, explicit numerical scores, and key points utilizing approximately three thousand output tokens. Standard Mode simulates multiple reviewer perspectives with integrated self-verification protocols. Best Mode executes an exhaustive, comprehensive analysis across all dimensions of soundness, presentation, contribution, and final rating.

Empirical evaluations position DeepReviewer-14B as mathematically superior to generic conversational models for this specific domain. In comparative evaluations, DeepReviewer-14B achieved an 80.20 percent to 88.21 percent win rate against leading proprietary reasoning models. Furthermore, it outperformed significantly larger open-weights review models, demonstrating a 44.80 percent reduction in rating mean squared error and a measurable improvement in rating Spearman correlation.

Crucially for an autonomous system prone to repetitive generation cycles, DeepReviewer-14B exhibits strong resilience against adversarial attacks and the phenomenon of "smart plagiarism"—a known failure mode where automated agents attempt to mask unoriginal ideas with obfuscating terminological shifts. In a critical accept and reject decision task on historical academic datasets, it achieved a 64.06 percent decision accuracy.

### **4.2. Utilizing the Semantic Scholar Academic Graph (S2AG)**

The Semantic Scholar Academic Graph is the largest open scientific literature graph available, encompassing over 225 million papers and more than 2.4 billion citation edges. It extends far beyond raw citation counts by utilizing advanced machine learning techniques to classify citation intent and measure genuine intellectual influence.

The most critical feature for research value assessment is the capability of the Semantic Scholar API to extract and predict influence. The `influentialCitationCount` and `isInfluential` fields allow systems to determine if a cited publication had a highly significant impact on the citing paper, such as forming the absolute basis of the methodology, rather than acting as a superficial background reference. Furthermore, recent advancements in citation prediction, such as those highlighted in the SCIDOCA 2025 shared task, leverage massive datasets and heterogeneous graph neural networks to predict the future citation trajectory of a paper.

To operationalize the Semantic Scholar Academic Graph within the Reviewer stage, the system can construct a "shadow citation profile." By generating the abstract and introduction of the completed experiment, the system can query the Semantic Scholar Recommendations API to find the most semantically similar existing papers published in the last twenty-four months.

If the nearest neighbors in the citation graph possess exceptionally high influential citation metrics, and the autonomous experiment demonstrates a statistically valid improvement over those specific papers, the system can mathematically infer a high potential for future significance. Conversely, if the nearest neighbors are obscure, uncited papers, the research direction may be highly novel but situated in a saturated, abandoned, or irrelevant domain, indicating low timeliness and ultimately low overall value.

Furthermore, the Semantic Scholar platform provides specialized SPECTER2 embeddings. The autonomous Reviewer can calculate the cosine distance between the generated experiment's embedding and the centroid of the top-tier papers in that specific machine learning subfield. A moderate distance indicates the optimal sweet spot of research value: sufficiently distant to be recognized as highly novel, but close enough to remain deeply relevant to active, high-impact research endeavors.

### **4.3. Cost and Latency Profiles**

Generation costs for fully formatted papers using commercial APIs average between ten and fifteen dollars per iteration. Multi-agent architectures utilizing recursive reasoning consume approximately fifteen times more tokens than standard chat interactions. Training bespoke models for specific review tasks requires substantial computational investment, with standard fine-tuning runs occupying high-end GPU clusters for upwards of one hundred and twenty hours. Therefore, running a fourteen-billion-parameter review model or executing external API calls on every single experimental epoch is unfeasible. Value assessment must be triggered selectively, strictly isolated to experiments that have successfully passed the initial, low-latency statistical verification gates.

## **5. Architecture Integration and Routing Strategy**

### **5.1. The Hierarchical Routing Decision Logic**

The **PASS** designation indicates that the experimental result should be autonomously pushed to the manuscript writing and publication phase without requiring human intervention. To achieve a PASS, the experiment must strictly pass statistical validation, confirming a positive performance delta. Additionally, the Semantic Scholar embedding distance must indicate moderate novelty, falling within the optimal relevance threshold. Finally, the local DeepReviewer evaluation must assign a combined contribution and soundness score exceeding a rigorous threshold, such as greater than six out of ten.

The **PARTIAL_FAIL** designation serves as a human-in-the-loop escalation protocol. This status is triggered when the experiment passes initial statistical validation, but subsequent value assessments produce conflicting or borderline signals. The system packages the auto-generated evaluation reports and escalates the decision to a human researcher. This escalation is critical for identifying and preserving highly unconventional paradigm shifts that conservative evaluation models might mistakenly penalize.

The **CRITICAL_FAIL** designation results in the immediate termination of the experimental pipeline. This hard gate is enforced if the experiment fails statistical validation entirely, producing a negative or zero performance delta. Furthermore, a CRITICAL_FAIL is triggered if the evaluation models detect severe methodological flaws, hallucinated metrics, "smart plagiarism," or if the absolute scientific value score falls below four out of ten. Upon termination, the failure state and the associated hyperparameter trajectory are permanently logged in the system's persistent experimentation memory, mathematically preventing the generator agents from exploring this specific dead-end in future iterations.

### **5.2. Mitigating the Risk of Value Suppression**

A well-documented and severe risk in automated peer review is the systematic suppression of genuinely novel research that breaks sharply from conventional paradigms. Because large language models are inherently biased toward the distribution of their training data, they possess a tendency to reward conventionality and penalize radical divergence.

To address this, the architecture implements the doctrine of **Empirical Supremacy**. Under this logical rule, if the mathematically measured performance delta exceeds a predefined, exceptionally high threshold—for example, greater than a fifteen percent absolute improvement over a state-of-the-art baseline—the routing logic automatically defaults to a PARTIAL_FAIL human escalation rather than a CRITICAL_FAIL termination, regardless of how severely the linguistic evaluation models penalize the structural novelty. This overriding protocol ensures that false negatives, which represent the most costly outcome in the pursuit of scientific discovery, are escalated directly to a human specialist rather than being silently discarded.

### **5.3. Implementing the Minimum Viable Value Check**

The Minimum Viable Value Check operates entirely locally. First, it executes a local embedding check by extracting the core mathematical contribution string and generating a lightweight vector embedding. This embedding is compared via cosine similarity against a locally cached vector database containing the top cited deep learning papers of the previous year. If the similarity metric exceeds a highly derivative threshold, the experiment is flagged.

Simultaneously, the check utilizes the system's existing lightweight language model node with a highly constrained, single-shot prompt. The prompt supplies the baseline performance, the newly achieved performance, and a brief description of the mechanism, requesting a strict integer score from one to five based exclusively on the fundamental dimensions of performance, novelty, and simplicity. If the resulting score meets a minimum threshold and the local similarity check confirms the result is not overtly derivative, the experiment is allowed to proceed to the heavier DeepReviewer and Semantic Scholar analysis stages.

### **Table 4: Comprehensive LangGraph Subgraph Architecture**

| Pipeline Stage | Node Designation | Core Functionality | Routing Execution Trigger |
| :---- | :---- | :---- | :---- |
| **1. Verification** | Statistical_Validation | Mathematically confirms that the experimental delta is statistically significant. | If False → Immediate **CRITICAL_FAIL**. |
| **2. Triage Filtration** | MVVC_Filter | Computes local embedding distance and executes a single-prompt heuristic evaluation. | If integer Score < 3 → Immediate **CRITICAL_FAIL**. |
| **3. Deep Evaluation** | DeepReviewer_Eval | Runs the DeepReviewer-14B model in Fast Mode to generate comprehensive rubrics. | Score < 4 → **CRITICAL_FAIL**; Score 4-6 → **PARTIAL_FAIL**. |
| **4. Global Context** | S2AG_Impact_Check | Queries the Semantic Scholar API to verify the influentialCitationCount of nearest neighbors. | Low topological graph influence → **PARTIAL_FAIL**. |
| **5. Protocol Override** | Empirical_Supremacy | Verifies if the empirical performance delta is anomalously high, indicating a breakthrough. | Overrides any linguistic CRITICAL_FAIL to **PARTIAL_FAIL**. |

---

#### 引用的著作

1. AI Fund / Octagon AI — TeaserClub
4. How we built our multi-agent research system — Anthropic (2026)
5. The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery — ResearchGate
8. Evaluating Sakana's AI Scientist — alphaXiv 2502.14297v2
10. EvoScientist: Towards Multi-Agent Evolving AI Scientists — arXiv 2603.08127
12. Jr. AI Scientist and Its Risk Report — arXiv 2511.04583
16. QJHWC/PaperForge — GitHub
17. The AI Imperative: Scaling High-Quality Peer Review in ML — arXiv 2506.08134
21. Agents4Science 2025 — Emergent Mind
22. Automatic Detection of Research Values from Scientific Abstracts — arXiv 2502.16390
23. Automated Novelty Evaluation of Academic Paper — arXiv 2507.11330
25. Is this Idea Novel? An Automated Benchmark — arXiv 2603.10303
28. DeepReview: Improving LLM-based Paper Review — arXiv 2503.08569
29. WestlakeNLP/DeepReviewer-14B — HuggingFace
33. The Semantic Scholar Open Data Platform — ResearchGate
35. SCIDOCA 2025 Shared Task on Citation Prediction — arXiv 2509.24283
37. SemanticScholar API Projects — AI Tinkerers SF
