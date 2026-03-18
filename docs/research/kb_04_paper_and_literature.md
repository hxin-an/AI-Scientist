# Knowledge Base 04: Paper Draft Generation and Literature Review Pipeline

> Source: Gemini Deep Research, 2026-03-18
> Purpose: Design reference for Planner literature review and Researcher paper generation

---

## Key Decisions Derived from This Research

### Literature Review Pipeline（Planner Stage）

**API 策略（三層 fallback）**

| 來源 | 用途 | 速率限制 |
|------|------|---------|
| **Semantic Scholar (S2AG)** | 主要搜索引擎、citation graph、abstract | API key 必要：1 RPS 穩定 |
| **OpenAlex** | Fallback：補 S2 沒有的論文、PDF 下載 | 2026 起使用量計費，有免費額度 |
| **ArXiv** | 原始 LaTeX 原始碼提取（深度方法解析） | 嚴格限速，必須用 exponential backoff |

**Papers With Code 已於 2025 年 7 月關閉**，替代方案：
- **CodeSOTA API**：JSON endpoint，覆蓋 17 個研究領域的 SOTA 數字
- **OpenCodePapers GitLab**：靜態 JSON，直接 fetch，不受 rate limit
- **HuggingFace Daily Papers**：近 30–90 天新論文的 SOTA 追蹤

**Novelty Assessment：Idea Novelty Checker 流程**

```
1. 提取 core concepts → 擴展為查詢語
2. 向 S2AG 取 50–100 篇候選論文（keyword + embedding）
3. embedding 過濾 → top-K 最相似論文
4. Facet-based LLM reranking：逐一比較 Purpose / Mechanism / Evaluation / Application
5. 輸出：novelty score (1–5) + conflicting paper IDs + per-facet rationale
```

**Embedding 模型選擇**

| 模型 | 類型 | 推薦用途 |
|------|------|---------|
| **Qwen3-Embedding-8B** | 開源 | Instruction-aware，ML 論文首選 |
| **BGE-M3** | 開源 | RAG + clustering，穩定 fallback |
| Nomic Embed Text V2 | 開源 | 低儲存需求（Matryoshka 可截斷維度）|

注意：**Embedding 模型一旦選定就不能更換**，換模型需要重新 embed 整個 corpus。

**Literature Synthesis（50 篇 → Related Work）**

```
1. 每篇 abstract → JSON 提取：Methodology / Dataset / Key Finding / Limitations
2. BGE-M3 embedding → HDBSCAN 聚類 → 主題命名
3. 每個 cluster → Hierarchical CoT 合成（主題式，非時序式）
4. Gap 識別：Boolean inclusion criteria per cluster（非開放式提問）
```

---

### Paper Draft Generation（Researcher Stage）

**LaTeX 生成規則（不遵守會 fatal）**

| 規則 | 原因 |
|------|------|
| LLM 不得碰 preamble（\\documentclass, \\usepackage）| 套件衝突會直接無法編譯 |
| 每個 section 獨立 .tex 檔，master 用 \\input{} 組合 | 錯誤隔離，壞掉只重生一節 |
| 圖表由實驗代碼生成（matplotlib），不由 LLM 生成 | LLM 會 hallucinate 不存在的路徑 |
| 數字表格用 Pandas to_latex()，LLM 只寫說明文字 | LLM 格式化 tabularx 的錯誤率極高 |

**Figure 整合流程**

```
實驗代碼 → figures/xxx.pdf（高解析度向量圖）
         → results_manifest.json（路徑 + 核心指標 + 統計顯著性）

Researcher LLM 讀 manifest → 注入 \includegraphics{figures/xxx.pdf}
                            → 撰寫分析文字（不創造視覺資料）
```

**Citation 零 Hallucination 流程**

```
Planner 階段：每篇論文記錄 S2 Paper ID（40 字元）→ LangGraph state
Researcher 階段：semantic_bibtool 批量查 S2 API → 生成 references.bib
LLM 引用格式：\cite{S2ID_649def34f8be}（只用注入的 ID，禁止自創）
```

**寫作模型：Claude + Extended Thinking**

- 用 Claude（非 o1）：長文學術寫作品質更高，成本低 4x
- 複雜 section（literature synthesis、methodology）開啟 Extended Thinking，budget 4000–8000 tokens
- 使用 `think` tool 讓 Claude 在不確定時暫停推理再輸出

**人類編輯友好設計**

- 修改請求用「Edit Trick」：只輸出 diff list，Python script 套用，不重寫整段
- 需要人類判斷的部分留可搜索的 placeholder（統一格式）

---

## Original Research Question and Full Answer

# Research Prompt New-02: Paper Draft Generation and Literature Review Pipeline

## Context

We are building an AI Scientist system where:
1. The **Planner** stage must perform automated literature review to identify research gaps and establish baselines
2. The **Researcher** stage must generate a paper draft in LaTeX from experiment results

From prior research we know:
- Sakana AI uses Semantic Scholar / OpenAlex API for literature search (keyword-based, up to 10 results per query, up to 10 iterations)
- Their novelty detection is binary (True/False) based on keyword matching — known to fail (misclassifies existing work as novel)
- The "Idea Novelty Checker" achieves 13% better agreement with experts using retrieval-augmented LLM + embedding-based filtering
- Paper write-up uses LaTeX templates for ML conference format
- v2 uses reasoning models (o1-class) for single-pass generation + reflection

## What we already know

- Framework: LangGraph
- Literature sources: Semantic Scholar API + ArXiv
- Paper format: LaTeX (ML conference style)
- Known failure: pure keyword matching for novelty is insufficient

## Investigate

### Part A: Literature Review Pipeline

1. **Beyond keyword matching**: What is the current best practice for novelty assessment in automated research pipelines? How does the "Idea Novelty Checker" (ACL 2025) work in practice — what is its pipeline and can it be used standalone?

2. **Semantic Scholar vs ArXiv API**: For an automated pipeline, what are the practical differences? Which provides better programmatic access to abstracts, full text, and citation graphs? What are rate limits and authentication requirements in 2025–2026?

3. **Embedding-based paper search**: What is the recommended approach for finding semantically similar papers given a research idea? Which embedding models work best for ML paper similarity? How do you handle papers not in Semantic Scholar?

4. **Papers With Code integration**: How do you programmatically extract SOTA benchmark results from Papers With Code to establish baselines? Is there an official API or recommended scraping approach?

5. **Literature synthesis**: What is the best pipeline for going from a list of 20–50 retrieved papers to a structured "related work" summary that identifies gaps? What prompting strategies work best for this synthesis step?

### Part B: Paper Draft Generation

6. **LaTeX generation quality**: What is the current best practice for generating a complete ML paper draft in LaTeX using LLMs? What are the most reliable sections vs. sections that require heavy human editing?

7. **Figure and plot integration**: Given that experiment results include loss curves, metric tables, and comparison plots (generated by the Researcher), what is the best pipeline for automatically integrating these into a LaTeX document with proper captions and references?

8. **Citation pipeline**: How do you go from Semantic Scholar paper IDs to properly formatted BibTeX entries in an automated pipeline? What tools handle this reliably?

9. **Reasoning models for writing**: The Sakana v2 system uses o1-class reasoning models for single-pass paper generation. For a Claude-based system, what is the equivalent recommended approach? Extended thinking? Specific prompting patterns?

10. **Human-edit-friendly output**: What structural and formatting choices make a generated LaTeX draft easiest for a human researcher to finalize? What should deliberately be left as placeholders?

## Constraints

- Paper format: ML conference (NeurIPS/ICML/ICLR style)
- Must integrate with LangGraph pipeline
- Literature review must go beyond keyword matching
- Prefer free or low-cost APIs
- Prefer 2024–2026 solutions


# **Architecting the Autonomous AI Scientist: Advanced LangGraph Pipelines for Literature Review and Manuscript Generation**

The pursuit of fully autonomous artificial intelligence systems capable of conducting end-to-end scientific research represents a critical frontier in modern machine learning. Early iterations of these systems, most notably Sakana AI's foundational AI Scientist framework, demonstrated the theoretical feasibility of chaining large language models (LLMs) to brainstorm ideas, execute experimental code, and draft academic manuscripts.1 However, empirical evaluations of these initial systems exposed severe architectural vulnerabilities. Chief among these was the reliance on binary, keyword-based novelty detection mechanisms, which consistently misclassified existing literature as novel, thereby triggering redundant experimental execution.2 Furthermore, the manuscript generation phases frequently suffered from hallucinated citations, broken LaTeX compilation, and shallow literature synthesis.3

Transitioning from experimental prototypes to robust, production-ready AI research systems requires abandoning linear scripts in favor of state-driven, graph-based orchestration frameworks, such as LangGraph, combined with state-of-the-art retrieval-augmented generation (RAG) paradigms. This report exhaustively details the optimal architectural configurations for the two most critical components of an AI Scientist system operating in the 2025–2026 technological landscape: the Planner stage, responsible for deep literature review, baseline extraction, and rigorous novelty assessment; and the Researcher stage, tasked with generating mathematically rigorous, human-editable, publication-ready LaTeX manuscripts.

## **Part A: The Planner Stage and Advanced Literature Review Pipelines**

Within a LangGraph-orchestrated AI Scientist, the Planner stage functions as the cognitive anchor. Its state graph must traverse millions of scholarly documents, extract relevant empirical baselines, identify genuine research gaps, and rigorously validate the novelty of proposed ideas against a vast corpus of existing knowledge before allocating computational resources to experimental execution.

### **Beyond Keyword Matching: Multidimensional Novelty Assessment**

The primary failure mode of early automated research systems was the reduction of novelty assessment to a one-dimensional, binary (True/False) keyword matching exercise.5 Keyword overlap is a fundamentally flawed proxy for scientific similarity. Novel machine learning methodologies frequently share exact vocabularies with prior work—utilizing the same architectures, datasets, or optimization algorithms—while differing profoundly in their theoretical application or objective function.6 The current best practice for automated novelty detection abandons flat keyword matching in favor of a two-stage "retrieve-then-rerank" architecture, best exemplified by the "Idea Novelty Checker" (ACL 2025\) and the broader ScholarEval evaluation framework.5

The Idea Novelty Checker operates through a highly structured, multidimensional pipeline that can be seamlessly integrated as a standalone conceptual node within a LangGraph architecture.8 The pipeline execution unfolds as follows:

First, the system extracts core concepts from the proposed research idea and expands these into natural language queries. It queries scholarly APIs to retrieve a broad candidate pool—typically 50 to 100 papers—utilizing both semantic embeddings and snippet-level retrieval. Snippet retrieval maps approximately 500-word chunks of text to identify localized semantic similarities that might be lost in document-level embeddings.12 Second, this initial candidate pool is aggressively filtered using dense vector embeddings to isolate the top\-![][image1] most semantically aligned papers.12

The third step introduces facet-based LLM reranking, which serves as the critical differentiator from legacy systems. Instead of asking a language model a generalized question regarding the novelty of the idea, the system explicitly decomposes the comparison into highly specific scientific facets: *Purpose*, *Mechanism*, *Evaluation*, and *Application*.8 The reasoning model compares the proposed idea against the retrieved papers across each individual facet independently. Finally, utilizing expert-labeled in-context examples, the LLM generates a structured rationale explaining precisely why an idea diverges from prior art, rather than merely outputting a binary classification score.7

Empirical evaluations demonstrate that this facet-based approach achieves approximately 13% higher agreement with human domain experts compared to baseline zero-shot models.6 Furthermore, advanced evaluation frameworks like ScholarEval expand this paradigm by assessing not just novelty, but also "Soundness"—the empirical validity of the proposed methods—and "Contribution"—the degree of advancement across distinct dimensions relative to prior research.5

For a LangGraph-based AI Scientist, the Planner must invoke a structured evaluation node that accepts the proposed\_idea state variable and returns a heavily structured JSON object. This object must contain a continuous novelty score (e.g., utilizing a 1 to 5 rubric), an array of potentially conflicting Paper IDs, and a detailed, facet-by-facet rationale justifying the methodological divergence from the established literature.15

### **Programmatic Access to Literature: Semantic Scholar, ArXiv, and OpenAlex**

To feed the retrieval engines, the AI Scientist requires highly robust, programmatic access to the global scientific corpus. In the 2025 and 2026 landscape, the ecosystem of scholarly APIs is dominated by the Semantic Scholar Academic Graph (S2AG) API, the ArXiv API, and the rapidly expanding OpenAlex infrastructure. However, their architectural implementations, rate limits, and data payloads dictate strictly divergent use cases within an automated pipeline.

Semantic Scholar represents the optimal primary data source and discovery hub for the Planner stage.16 The S2AG encompasses over 214 million papers and 2.49 billion citation edges, providing a massive, interconnected knowledge graph that spans virtually all scientific disciplines.17 Conversely, ArXiv operates as a specialized preprint server restricted to specific domains such as Computer Science, Mathematics, and Physics.19 While its scope is significantly narrower, its primary advantage lies in the availability of full-text LaTeX source code, which is invaluable for deep mathematical and tabular data extraction.

The following table delineates the practical differences between the primary academic APIs available for integration in 2025 and 2026:

| API Provider | Corpus Size & Scope | Rate Limits & Authentication (2025–2026) | Optimal Pipeline Function |
| :---- | :---- | :---- | :---- |
| **Semantic Scholar (S2AG)** | 214+ Million papers, multidisciplinary 18 | Unauthenticated: 1000 RPS shared global pool. Authenticated (API Key): 1 RPS dedicated, highly reliable.18 | Primary discovery engine, citation graph traversal, abstract retrieval, and "Smart Citation" analysis.16 |
| **OpenAlex** | 250+ Million papers, comprehensive open-access graph 22 | Usage-based pricing introduced in 2026; generous free tiers for researchers. Open CLI tools available.23 | Fallback discovery engine for non-S2 papers, metadata enrichment, and bulk PDF retrieval.22 |
| **ArXiv API** | \~2.5 Million preprints, highly focused on CS/Math/Physics 19 | Unauthenticated. Historically strict; frequent HTTP 429 (Too Many Requests) errors reported in 2026 despite delays.24 | Deep extraction of raw LaTeX source code, mathematical proofs, and complex methodology parsing.25 |

**Architectural Best Practice:** The LangGraph pipeline should execute a federated routing strategy for literature acquisition. Semantic Scholar must be utilized as the primary traversal engine to build the citation graph, retrieve abstracts, and identify influence networks via the /graph/v1/paper/batch endpoint.26 When a paper is identified as highly relevant but its content is not fully accessible via S2AG, the pipeline should gracefully fall back to the OpenAlex API, which provides excellent programmatic access to full-text downloads via its newly released 2026 CLI and semantic search endpoints.23 Finally, when deep methodological extraction is required—such as parsing the intricacies of a novel neural network architecture—the system should cross-reference the ArXiv ID and ping the ArXiv API to download the raw LaTeX source code 25, implementing aggressive exponential backoff algorithms to gracefully handle ArXiv's strict HTTP 429 rate limiting.24

### **Embedding-Based Semantic Search for Machine Learning Literature**

The efficiency and accuracy of the Planner's retrieval-augmented generation relies entirely on the quality of the vector embeddings used to map the semantic space of machine learning research. Simple dense models from previous generations fail to capture the dense, domain-specific terminology, mathematical notation, and specialized jargon inherent in computer science literature.27

In the 2025–2026 machine learning landscape, the Massive Text Embedding Benchmark (MTEB) heavily dictates model selection, assessing models across classification, clustering, retrieval, and semantic textual similarity.29 When evaluating semantic similarity specifically for ML papers, the pipeline must utilize models capable of processing highly technical vocabularies, handling extended context windows, and supporting multi-vector or Matryoshka representation learning.31

The following models represent the vanguard of embedding technologies suitable for the AI Scientist pipeline:

| Embedding Model | Provider / License | Dimensions | Performance Profile & Optimal Use Case |
| :---- | :---- | :---- | :---- |
| **text-embedding-3-large** | OpenAI (Proprietary API) | Up to 3072 | Highest overall semantic understanding score (0.524 SAGE score). Best overall choice for managed pipelines requiring minimal infrastructure.32 |
| **Qwen3-Embedding-0.6B / 8B** | Alibaba (Open Source) | 32 to 1024 | Instruction-aware architecture yields 1% to 5% improvement in accuracy when pre-prompted with specific task instructions. Excellent multilingual support.31 |
| **BGE-M3** | BAAI (Open Source) | 1024 | Highly reliable open-source fallback optimized specifically for RAG and clustering tasks. Ideal for grouping related passages prior to synthesis.32 |
| **Nomic Embed Text V2** | Nomic AI (Open Source) | 256 to 768 | Utilizes a Mixture of Experts (MoE) design and Matryoshka representation learning, allowing dimensionality truncation without severe degradation, minimizing vector DB storage.31 |
| **Voyage-3-Large** | Voyage AI (Proprietary API) | 1024 | Surprising leader in technical document and code-heavy retrieval, providing near-parity with OpenAI models for specialized research tasks.36 |

**Implementation Imperatives:** When designing the retrieval node within LangGraph, handling out-of-network papers is a critical edge case. If a relevant paper exists outside the Semantic Scholar database, the system must retrieve the PDF via OpenAlex or publisher APIs and run it through a dedicated parsing pipeline. Tools such as IBM's Docling or PyMuPDF4LLM are currently the state-of-the-art for extracting clean text, tables, and structured data from offline PDFs without relying on cloud APIs.38 Once parsed, this text is chunked, embedded, and injected into the active vector database.

Furthermore, it is a critical engineering reality that mixing embedding models or altering dimensionality within a vector database drastically alters the geometry of the embedding space.40 Directions, distances, and neighborhood structures shift entirely. Cosine similarity and dot products are only reliably interpretable when comparing embeddings generated by the exact same model trained in the exact same vector space.40 Consequently, the AI Scientist must lock its embedding model architecture during initialization; any subsequent upgrade to a newer model requires a complete re-embedding of the entire locally cached scientific corpus to prevent catastrophic degradation in retrieval precision.40

### **Establishing Baselines: Programmatic Extraction of State-of-the-Art Results**

An AI Scientist cannot establish the empirical validity of its proposed hypotheses without comparing its generated experiments against State-of-the-Art (SOTA) baselines. Historically, automated systems relied on the Papers With Code (PWC) API to programmatically extract these performance metrics. However, Meta unexpectedly sunset the Papers With Code platform in July 2025, redirecting all web traffic to Hugging Face and simultaneously destroying programmatic access to over 9,300 benchmark leaderboards.41

In response to the PWC shutdown, the 2025–2026 standard for automated baseline extraction relies entirely on newly established, independent infrastructure, specifically the **CodeSOTA** API and the **OpenCodePapers** repository.41 To programmatically extract SOTA benchmark results, the Planner stage must implement a resilient, multi-source scraping and API consumption strategy:

1. **CodeSOTA JSON Integration:** CodeSOTA tracks independent machine learning benchmarks across 17 distinct research areas and provides all benchmark data programmatically via structured JSON endpoints (e.g., /data/benchmarks.json).43 The system queries this JSON structure, filtering the data by the specific \<Task, Dataset, Metric\> tuple established by the PWC taxonomy.41 For instance, if the AI Scientist proposes a novel computer vision architecture, the Planner queries the tuple \<Image Classification, ImageNet, Top-1 Accuracy\> to extract the highest-performing numerical baseline and its associated source paper.  
2. **OpenCodePapers GitLab Repository:** Operating as an open-source mirror and continuation of the legacy PWC dataset, OpenCodePapers stores its leaderboards as static JSON files within a public GitLab repository.42 The LangGraph Planner node can bypass rate-limited cloud APIs entirely by fetching raw files directly (e.g., dataset/benchmarks/code-generation-on-conala.json 45) to parse historical baselines locally and deterministically.  
3. **Hugging Face Trending Papers API:** For real-time updates on papers published within the last 30 to 90 days—which may not yet be indexed in static repositories—the AI Scientist must monitor Hugging Face's Daily Papers endpoints.46 By scraping the abstracts of these trending papers and utilizing a lightweight extractor LLM with strict JSON schema enforcement 48, the system can parse the latest metrics (e.g., extracting "achieves 74% SWE-bench at 90% lower cost" into a structured format 43) to dynamically update its internal baseline registry prior to experimental design.

### **High-Volume Literature Synthesis and Gap Identification**

Once the Planner has retrieved and verified a pool of 20 to 50 highly relevant papers, it must synthesize this corpus into a structured, conference-style "Related Work" section while simultaneously identifying explicit, mathematically verifiable research gaps. Pushing 50 academic abstracts directly into an LLM's context window with a generic prompt inevitably results in "lost in the middle" phenomena, hallucinated conceptual connections, and shallow summarization that fails to provide actionable scientific insights.13

The optimal approach utilizes **Hierarchical Prompting** and **Taxonomy-Driven Synthesis**, drawing heavily from recent frameworks like PROMPTHEUS and Science Hierarchography.49 This methodology prevents the LLM from becoming overwhelmed by raw text volume by breaking the synthesis process into discrete, manageable analytical tasks.

The literature synthesis pipeline operates through the following sequence:

1. **Granular Decomposition:** The LLM is prompted to perform zero-shot extraction on each individual abstract within the pool, isolating specific, predefined criteria: *Methodology*, *Dataset Utilized*, *Key Empirical Finding*, and *Stated Limitations*.50 Utilizing a strict JSON output schema ensures absolute uniformity across all processed papers.  
2. **Semantic Clustering:** The extracted methodologies and findings are embedded using a model like BGE-M3 and subsequently clustered using unsupervised algorithms such as HDBSCAN or BERTopic to identify organic thematic overlaps across the literature.49  
3. **Taxonomic Topic Generation:** An LLM is prompted to assign a concise, highly descriptive 1-to-5 word topic title to each resulting cluster (e.g., "Contrastive Learning for Vision-Language Models").49  
4. **Hierarchical Chain-of-Thought (CoT) Synthesis:** Rather than summarizing the papers chronologically—a common hallmark of poor AI writing—the LLM is instructed to draft the related work section thematically based on the generated clusters.51 The prompt dictates a specific narrative flow: introduce the broader theme, cite the supporting papers within the cluster, critically contrast their differing methodological approaches, and explicitly state the limitations of that specific cluster.51

To rigorously and systematically identify research gaps, the prompt engineering must rely on "Hybrid Question Structures" rather than open-ended inquiries.53 Instead of asking the LLM to "find a gap in the literature," the prompt requires the LLM to answer specific Boolean inclusion criteria tailored to the proposed hypothesis (e.g., *"Does the study address multimodal inputs under low-resource constraints? Return TRUE/FALSE"*). Areas where the entire thematic cluster returns FALSE represent verifiable research gaps, allowing the AI Scientist to confidently anchor its proposed hypothesis in uncontested scientific territory without relying on hallucinated assumptions.53

## **Part B: The Researcher Stage and Automated Manuscript Generation**

Following the successful identification of a novel hypothesis and the execution of the experimental code, the Researcher stage is invoked. This stage is responsible for translating raw experimental data, code execution outputs, and the Planner's literature synthesis into a cohesive, publication-ready LaTeX document that strictly conforms to machine learning conference standards (e.g., NeurIPS, ICLR, ICML).3

### **LaTeX Generation Quality and LLM Best Practices**

LaTeX is considered a "boring technology" in the context of machine learning—it has existed for decades, possesses strict syntactic rules, and is massively overrepresented in LLM pre-training data corpuses.56 Consequently, frontier models possess an innate, baseline proficiency in generating standard LaTeX markup. However, empirical studies, such as the comprehensive TeXpert benchmark introduced in 2025, reveal a critical nuance: while models excel at generating standard textual paragraphs wrapped in basic formatting, they suffer catastrophic accuracy drop-offs when tasked with complex document structures, nested multi-column tables, and specialized package integration.4

To ensure the automated generation of compiling, high-quality LaTeX, the Researcher stage must adhere to stringent architectural constraints:

* **Rigid Preamble Isolation:** The LLM must *never* be tasked with generating or modifying the document preamble (i.e., \\documentclass{}, \\usepackage{}, \\geometry{}). Hallucinated packages or colliding dependencies (such as an LLM attempting to import both algorithmic and algorithm2e simultaneously) will instantly and fatally break compilation.4 The system must maintain a static, human-verified template directory (e.g., utilizing iclr2026.sty) and restrict the LLM's text generation strictly to the content between \\begin{document} and \\end{document}.58  
* **Modular Generation:** The pipeline must not prompt the LLM to generate an entire 8-page paper in a single monolithic pass. The generation must be chunked into localized files. The AI Agent writes introduction.tex, methodology.tex, and experiments.tex independently, while a master Python script stitches them together using standard \\input{} statements. This modularity isolates errors and allows the system to regenerate specific failing sections without rewriting the entire document.  
* **Reliability Variance Acknowledgment:** System architects must recognize that LLMs are highly reliable at drafting Introductions, Related Work summaries, and Conclusions, as these sections are heavily prose-based and conceptually fluid.56 Conversely, mathematical proofs, complex tabular formatting (such as tabularx environments), and custom algorithmic macros are highly prone to hallucinated syntax and require strict structural validation scripts before compilation is attempted.4

### **Deterministic Integration of Figures, Plots, and Tables**

A pervasive and often fatal flaw in automated manuscript generation is the LLM attempting to "hallucinate" visual data. When given open-ended prompts, models will frequently output invalid TikZ code that fails to compile, or they will reference file paths that do not exist on the local disk (e.g., inserting \\includegraphics{fake\_plot\_that\_does\_not\_exist.png}).2

The integration of experimental results must be strictly decoupled from the LLM's creative text generation process. The pipeline must operate deterministically, treating the LLM as a layout manager rather than a data creator, utilizing principles derived from systems like SciFig.59

1. **Programmatic Visual Generation:** The experimental execution script (written by the LLM in Python during the coding phase) must handle all visual generation using established libraries like matplotlib or seaborn.60 The script automatically saves high-resolution vector graphics (PDFs) to a predefined, static directory, such as figures/loss\_curve.pdf or figures/ablation\_bar.pdf.61  
2. **Metadata Manifest Creation:** Upon completion of the experiments, the Python script simultaneously generates a results\_manifest.json. This file contains the exact local file paths, core metric highlights, and statistical significance calculations for all generated plots and tables.  
3. **Prompt Injection with Constraints:** When prompting the LLM to draft the Experiments section, the prompt explicitly injects data from the manifest rather than raw logs. The prompt dictates: *"The loss curve demonstrating a 15% convergence improvement is saved at 'figures/loss\_curve.pdf'. Write the analytical text for this result and integrate the figure into the LaTeX document using exactly the command \\includegraphics\[width=\\linewidth\]{figures/loss\_curve.pdf}."*.62  
4. **Hierarchical Layout Parsing:** To ensure professional academic aesthetics, the pipeline can utilize hierarchical layout generation strategies. These systems parse the generated text to identify component relationships and programmatically apply layout rules (e.g., grouping related evaluation plots into subfigures using the subcaption package) rather than relying on the LLM's notoriously poor spatial reasoning capabilities.59  
5. **Tabular Data Generation:** For numerical benchmark results, the LLM should never be trusted to format complex LaTeX tables directly from raw data. Instead, the Python execution script should generate the raw LaTeX table code using utilities like Pandas' to\_latex() function. The LLM is then provided with the pre-formatted table code and instructed only to generate the analytical prose and the appropriate \\caption{}.56

### **The Zero-Hallucination Citation Pipeline: Semantic Scholar to BibTeX**

Citations represent the critical connective tissue of academic writing, establishing the provenance and validity of claims. However, LLMs are notoriously prone to hallucinating authors, fabricating DOIs, and inventing paper titles that sound plausible but do not exist.63 An automated pipeline must entirely remove the LLM's ability to "invent" citations, replacing the generative process with a strict, deterministic retrieval protocol.

The optimal 2026 workflow relies on tracking unique Semantic Scholar IDs (S2 Paper IDs) or OpenAlex IDs to generate a pristine .bib file programmatically, preventing any generative hallucinations 65:

1. **Identifier Tracking:** During the Planner stage, every paper synthesized into the literature review and selected for inclusion has its unique 40-character Semantic Scholar ID recorded in a global state variable within the LangGraph architecture.  
2. **Programmatic BibTeX Conversion:** Once the manuscript content is finalized, a dedicated node containing a Python wrapper—such as semantic\_bibtool—is invoked. This tool queries the Semantic Scholar API using the curated list of S2 IDs and automatically downloads the officially formatted BibTeX entries, natively handling special characters, mathematical symbols in titles, and formatting nuances.65  
3. **Citation Key Mapping:** The LLM is strictly instructed via system prompts to cite papers using a programmatic key injected into its context window (e.g., *"Cite the attention mechanism paper using exactly \\cite{S2ID\_649def34f8be}"*). During the final compilation step, the system maps these keys to the programmatically generated references.bib file. This architecture ensures 100% citation validity and entirely eliminates the hallucination of non-existent literature.65

### **Cognitive Orchestration for Scientific Writing: Claude 3.7 Sonnet versus OpenAI o1**

In the pursuit of single-pass, high-quality manuscript generation, the choice of the underlying foundation model drastically alters the quality, tone, and logical consistency of the output. While OpenAI's o1-class models were initially heralded for their deep reinforcement learning and complex mathematical problem-solving capabilities 69, the 2025–2026 industry consensus strongly favors Anthropic's Claude 3.5 Sonnet and the newly released Claude 3.7 Sonnet for long-form academic drafting.70

OpenAI's o1 models excel in advanced mathematics and isolated, highly complex logical deductions, but they exhibit distinct drawbacks in generative writing: they tend to overengineer solutions, struggle with formatting constraints, and produce prose that feels overly mechanical or unnaturally structured.70 Conversely, Claude 3.7 Sonnet is deeply optimized for long-form content generation, exhibiting a nuanced, highly academic tone that closely mimics professional scientific prose.70 Furthermore, the Claude Sonnet architecture is highly cost-efficient—approximately 4x cheaper than o1 for output tokens—and features significantly lower latency, making it ideal for the iterative, high-volume token generation required to write an 8-page, multi-section conference paper.71

**Implementing Extended Thinking for Complex Drafting:** With the release of Claude 3.7 Sonnet, Anthropic introduced "Extended Thinking," a revolutionary feature allowing developers to explicitly set a token budget for the model to engage in hidden, reinforcement-learning-driven Chain-of-Thought reasoning before outputting the final text.74 This bridges the reasoning gap between standard autoregressive models and OpenAI's o1 architecture.

For the LangGraph-orchestrated AI Scientist, Extended Thinking should be implemented specifically during the most cognitively demanding phases: literature synthesis, methodology drafting, and experimental analysis. The prompt configuration and API integration should adhere to the following paradigms:

1. **Strategic Token Budgeting:** Allocate between 4,000 and 8,000 tokens specifically for the thinking parameter when calling the API for complex sections.76 This provides the model ample computational space to reconcile contradictory experimental data before drafting the analysis.  
2. **Integration of the think Tool:** In complex, multi-agent LangGraph workflows, when Claude reaches a point of uncertainty or requires deep evaluation of a long context window, it can explicitly invoke the think tool. This allows the model to pause, evaluate the available context, and formulate a coherent narrative strategy before committing text to the LaTeX document.77  
3. **Avoiding Prescriptive Steps:** Counterintuitively, when utilizing Extended Thinking, prompts should avoid highly rigid, step-by-step instructions. According to Anthropic's prompt engineering guidelines, the prompt should use general, outcome-oriented instructions (e.g., *"Think thoroughly about the experimental limitations and potential confounders before drafting this section"*) rather than forcing the model into a hand-written plan. This allows the model's internal RL-trained reasoning paths to organically structure the most effective argument.78

### **Designing Human-Centric, Edit-Friendly Output Structures**

A fundamental principle of building an AI Scientist is acknowledging that its output is not infallible. The generated LaTeX draft must be structurally optimized for a human researcher to easily review, finalize, and edit. Monolithic blocks of generated text are exceptionally difficult to debug; therefore, the pipeline must employ specific structural choices to enhance readability, transparency, and editability.

**1\. The "Edit Trick" for Iterative Refinement:** When a human reviewer requests a refinement to a draft, feeding a 5,000-word LaTeX section back into the LLM and asking for a complete rewrite is highly inefficient. It consumes massive token context, increases latency, and introduces the severe risk of the model accidentally deleting previously verified information or breaking LaTeX syntax. Instead, the system should utilize the "Edit Trick" paradigm.79 The LLM is prompted to output only a structured list of specific diffs or edits (e.g., *"Replace line 42 with..."* or *"Insert the following paragraph after section 3.1"*). A lightweight Python script then applies these diffs to the .tex file locally. This preserves human edits and drastically reduces both cost and processing time.

**2\. Strategic Placeholders for Human Intuition:** Certain elements of a scientific paper require human intuition, ethical considerations, or qualitative judgments that AI cannot currently provide reliably. The LLM should be explicitly prompted to use highly visible, easily searchable placeholders in the LaTeX code for these specific sections, utilizing template syntax to ensure consistency.62

* Instead of attempting to hallucinate broader societal impacts or ethical constraints, the model should be instructed to insert a bright red warning block: \\textcolor{red}{\\textbf{}}.62  
* For complex architectural diagrams that cannot be generated via Python scripts or basic TikZ, the model should insert placeholder figure environments to maintain document layout: \\begin{figure} \\centering \\rule{8cm}{4cm} \\caption{} \\end{figure}.61

**3\. Template Syntax and Exhaustive Commenting:** The generated LaTeX code must be heavily and consistently commented to provide an audit trail of the AI's decision-making process. The LLM should be instructed via the system prompt to utilize the % symbol to output comments detailing its reasoning directly within the code. For example, above a generated equation, the LLM might write: % Equation derived based on the assumption of a Gaussian distribution, aligning with the baseline established in. This level of transparency allows the human editor to understand the AI's internal logic and mathematical assumptions without needing to re-prompt or interrogate the system.58

## **Conclusion**

The architecture of a highly capable, autonomous AI Scientist relies less on the sheer generative power of a single, monolithic language model, and more on the rigorous, deterministic engineering of the data pipelines surrounding it. By moving beyond brittle keyword matching to implement facet-based novelty evaluation, transitioning from deprecated platforms like Papers With Code to stable JSON endpoints like CodeSOTA, and carefully orchestrating Claude 3.7 Sonnet's extended thinking capabilities within a LangGraph state machine, the Planner stage can execute literature reviews with precision that rivals human domain experts.

Simultaneously, by strictly decoupling visual generation from text generation, enforcing deterministic BibTeX retrieval via the Semantic Scholar API, and employing modular, placeholder-rich LaTeX templates, the Researcher stage guarantees the production of structurally sound, empirically valid, and highly human-editable scientific manuscripts. This pipeline-driven blueprint fundamentally resolves the hallucination, redundancy, and formatting limitations of earlier systems, paving the way for scalable, reliable, and truly autonomous scientific discovery.

#### **引用的著作**

1. The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery \- Sakana AI, 檢索日期：3月 18, 2026， [https://sakana.ai/ai-scientist/](https://sakana.ai/ai-scientist/)  
2. Evaluating Sakana's AI Scientist for Autonomous Research: Wishful Thinking or an Emerging Reality Towards 'Artificial Research Intelligence' (ARI)? \- arXiv, 檢索日期：3月 18, 2026， [https://arxiv.org/html/2502.14297v2](https://arxiv.org/html/2502.14297v2)  
3. Evaluating The AI Scientist \- by Dr. Nimrita Koul \- Medium, 檢索日期：3月 18, 2026， [https://medium.com/@nimritakoul01/evaluating-the-ai-scientist-63e419e575b8](https://medium.com/@nimritakoul01/evaluating-the-ai-scientist-63e419e575b8)  
4. TeXpert: A Multi-Level Benchmark for Evaluating LaTeX Code Generation by LLMs \- arXiv, 檢索日期：3月 18, 2026， [https://arxiv.org/html/2506.16990v1](https://arxiv.org/html/2506.16990v1)  
5. ScholarEval: Research Idea Evaluation Grounded in Literature \- arXiv, 檢索日期：3月 18, 2026， [https://arxiv.org/html/2510.16234v2](https://arxiv.org/html/2510.16234v2)  
6. Workshop on Scholarly Document Processing (2025) \- ACL Anthology, 檢索日期：3月 18, 2026， [https://aclanthology.org/events/sdp-2025/](https://aclanthology.org/events/sdp-2025/)  
7. Literature-Grounded Novelty Assessment of Scientific Ideas \- arXiv.org, 檢索日期：3月 18, 2026， [https://arxiv.org/html/2506.22026v1](https://arxiv.org/html/2506.22026v1)  
8. Proceedings of the Fifth Workshop on Scholarly Document Processing (SDP 2025\) \- ACL Anthology, 檢索日期：3月 18, 2026， [https://aclanthology.org/2025.sdp-1.pdf](https://aclanthology.org/2025.sdp-1.pdf)  
9. Proceedings of the Fifth Workshop on Scholarly Document Processing (SDP 2025), 檢索日期：3月 18, 2026， [https://aclanthology.org/volumes/2025.sdp-1/](https://aclanthology.org/volumes/2025.sdp-1/)  
10. Literature-Grounded Novelty Assessment of Scientific Ideas \- ACL Anthology, 檢索日期：3月 18, 2026， [https://aclanthology.org/2025.sdp-1.9/](https://aclanthology.org/2025.sdp-1.9/)  
11. 信息检索/信息论/社会&信息网络/CS与社会学2025\_6\_30, 檢索日期：3月 18, 2026， [http://arxivdaily.com/thread/68907](http://arxivdaily.com/thread/68907)  
12. Literature-Grounded Novelty Assessment of Scientific Ideas \- ACL Anthology, 檢索日期：3月 18, 2026， [https://aclanthology.org/2025.sdp-1.9.pdf](https://aclanthology.org/2025.sdp-1.9.pdf)  
13. LLM4Rerank: LLM-based Auto-Reranking Framework for Recommendations | Request PDF \- ResearchGate, 檢索日期：3月 18, 2026， [https://www.researchgate.net/publication/391479170\_LLM4Rerank\_LLM-based\_Auto-Reranking\_Framework\_for\_Recommendations](https://www.researchgate.net/publication/391479170_LLM4Rerank_LLM-based_Auto-Reranking_Framework_for_Recommendations)  
14. ScholarEval: Research Idea Evaluation Grounded in Literature \- OpenReview, 檢索日期：3月 18, 2026， [https://openreview.net/forum?id=0TPKIbihMF](https://openreview.net/forum?id=0TPKIbihMF)  
15. Is this Idea Novel? An Automated Benchmark for Judgment of Research Ideas, 檢索日期：3月 18, 2026， [https://www.researchgate.net/publication/401833666\_Is\_this\_Idea\_Novel\_An\_Automated\_Benchmark\_for\_Judgment\_of\_Research\_Ideas/download](https://www.researchgate.net/publication/401833666_Is_this_Idea_Novel_An_Automated_Benchmark_for_Judgment_of_Research_Ideas/download)  
16. Semantic Scholar Review (2025): TLDR, Reader & Research Feeds Tested \- Skywork, 檢索日期：3月 18, 2026， [https://skywork.ai/blog/semantic-scholar-review-2025/](https://skywork.ai/blog/semantic-scholar-review-2025/)  
17. Mastering Research with the Semantic Scholar API: An Insider's Guide \- Skywork.ai, 檢索日期：3月 18, 2026， [https://skywork.ai/skypage/en/Mastering-Research-with-the-Semantic-Scholar-API-An-Insider's-Guide/1973804064216641536](https://skywork.ai/skypage/en/Mastering-Research-with-the-Semantic-Scholar-API-An-Insider's-Guide/1973804064216641536)  
18. Semantic Scholar Academic Graph API, 檢索日期：3月 18, 2026， [https://www.semanticscholar.org/product/api](https://www.semanticscholar.org/product/api)  
19. On the Use of ArXiv as a Dataset \- Semantic Scholar, 檢索日期：3月 18, 2026， [https://www.semanticscholar.org/paper/On-the-Use-of-ArXiv-as-a-Dataset-Clement-Bierbaum/39e01a6b3a1e8e2150f571bd3d5ed5c847eb7096](https://www.semanticscholar.org/paper/On-the-Use-of-ArXiv-as-a-Dataset-Clement-Bierbaum/39e01a6b3a1e8e2150f571bd3d5ed5c847eb7096)  
20. Exploring semantic-scholar-fastmcp-mcp-server: A Deep Dive for AI Engineers \- Skywork, 檢索日期：3月 18, 2026， [https://skywork.ai/skypage/en/Exploring-semantic-scholar-fastmcp-mcp-server-A-Deep-Dive-for-AI-Engineers/1972589539619827712](https://skywork.ai/skypage/en/Exploring-semantic-scholar-fastmcp-mcp-server-A-Deep-Dive-for-AI-Engineers/1972589539619827712)  
21. Best Literature Review Tools in 2026: 15 AI-Powered & Traditional Options Compared, 檢索日期：3月 18, 2026， [https://www.readwonders.com/blog/best-literature-review-tools-2026-ai-vs-traditional](https://www.readwonders.com/blog/best-literature-review-tools-2026-ai-vs-traditional)  
22. Best Google Scholar Alternatives in 2026 — Compared (Ocean of Papers vs. 8 Tools), 檢索日期：3月 18, 2026， [https://oceanofpapers.com/blog/google-scholar-alternatives](https://oceanofpapers.com/blog/google-scholar-alternatives)  
23. New Features and Usage-Based Pricing \- OpenAlex blog, 檢索日期：3月 18, 2026， [https://blog.openalex.org/openalex-api-new-features-and-usage-based-pricing/](https://blog.openalex.org/openalex-api-new-features-and-usage-based-pricing/)  
24. Request for guidance on arXiv API rate limits / higher-throughput access \- Google Groups, 檢索日期：3月 18, 2026， [https://groups.google.com/a/arxiv.org/g/api/c/ycq8giRdZsQ](https://groups.google.com/a/arxiv.org/g/api/c/ycq8giRdZsQ)  
25. Current SOTA for extracting data from PDFs? : r/LocalLLaMA \- Reddit, 檢索日期：3月 18, 2026， [https://www.reddit.com/r/LocalLLaMA/comments/1f43f2k/current\_sota\_for\_extracting\_data\_from\_pdfs/](https://www.reddit.com/r/LocalLLaMA/comments/1f43f2k/current_sota_for_extracting_data_from_pdfs/)  
26. Academic Graph API \- Semantic Scholar, 檢索日期：3月 18, 2026， [https://api.semanticscholar.org/api-docs/](https://api.semanticscholar.org/api-docs/)  
27. Evaluating NLP Embedding Models for Handling Science-Specific Symbolic Expressions in Student Texts \- arXiv.org, 檢索日期：3月 18, 2026， [https://arxiv.org/html/2505.17950v2](https://arxiv.org/html/2505.17950v2)  
28. Benchmarking Pretrained Molecular Embedding Models For Molecular Representation Learning \- arXiv, 檢索日期：3月 18, 2026， [https://arxiv.org/html/2508.06199v2](https://arxiv.org/html/2508.06199v2)  
29. Top embedding models on the MTEB leaderboard \- Modal, 檢索日期：3月 18, 2026， [https://modal.com/blog/mteb-leaderboard-article](https://modal.com/blog/mteb-leaderboard-article)  
30. MTEB Leaderboard \- a Hugging Face Space by mteb, 檢索日期：3月 18, 2026， [https://huggingface.co/spaces/mteb/leaderboard](https://huggingface.co/spaces/mteb/leaderboard)  
31. The Best Open-Source Embedding Models in 2026 \- Bento, 檢索日期：3月 18, 2026， [https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models](https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models)  
32. Top Embedding Models in 2025 — The Complete Guide \- Artsmart.ai, 檢索日期：3月 18, 2026， [https://artsmart.ai/blog/top-embedding-models-in-2025/](https://artsmart.ai/blog/top-embedding-models-in-2025/)  
33. SAGE: A Realistic Benchmark for Semantic Understanding \- arXiv, 檢索日期：3月 18, 2026， [https://arxiv.org/html/2509.21310v1](https://arxiv.org/html/2509.21310v1)  
34. Best Embedding Models for RAG in 2026: A Comparison Guide \- StackAI, 檢索日期：3月 18, 2026， [https://www.stack-ai.com/insights/best-embedding-models-for-rag-in-2026-a-comparison-guide](https://www.stack-ai.com/insights/best-embedding-models-for-rag-in-2026-a-comparison-guide)  
35. 5 Best Embedding Models for RAG: How to Choose the Right One \- GreenNode, 檢索日期：3月 18, 2026， [https://greennode.ai/blog/best-embedding-models-for-rag](https://greennode.ai/blog/best-embedding-models-for-rag)  
36. Best Embedding Models (2026) \- PE Collective, 檢索日期：3月 18, 2026， [https://pecollective.com/tools/best-embedding-models/](https://pecollective.com/tools/best-embedding-models/)  
37. The Best Embedding Models for Information Retrieval in 2025 \- DEV Community, 檢索日期：3月 18, 2026， [https://dev.to/datastax/the-best-embedding-models-for-information-retrieval-in-2025-3dp5](https://dev.to/datastax/the-best-embedding-models-for-information-retrieval-in-2025-3dp5)  
38. Convert PDFs to Clean Markdown or JSON (2025 Guide) | CodeSOTA, 檢索日期：3月 18, 2026， [https://www.codesota.com/ocr/docling](https://www.codesota.com/ocr/docling)  
39. Building a Multimodal LLM Application with PyMuPDF4LLM \- Artifex, 檢索日期：3月 18, 2026， [https://artifex.com/blog/building-a-multimodal-llm-application-with-pymupdf4llm](https://artifex.com/blog/building-a-multimodal-llm-application-with-pymupdf4llm)  
40. Different Embedding Models, Different Spaces: The Hidden Cost of Model Upgrades, 檢索日期：3月 18, 2026， [https://garystafford.medium.com/different-embedding-models-different-spaces-the-hidden-cost-of-model-upgrades-899db24ad233](https://garystafford.medium.com/different-embedding-models-different-spaces-the-hidden-cost-of-model-upgrades-899db24ad233)  
41. Papers with Code Alternative 2025 | CodeSOTA \- ML Benchmarks That Stay Current, 檢索日期：3月 18, 2026， [https://www.codesota.com/papers-with-code](https://www.codesota.com/papers-with-code)  
42. \[P\] PapersWithCode's new open-source alternative: OpenCodePapers : r/MachineLearning, 檢索日期：3月 18, 2026， [https://www.reddit.com/r/MachineLearning/comments/1p0b96k/p\_paperswithcodes\_new\_opensource\_alternative/](https://www.reddit.com/r/MachineLearning/comments/1p0b96k/p_paperswithcodes_new_opensource_alternative/)  
43. CodeSOTA \- Independent ML Benchmarks & State-of-the-Art Tracking, 檢索日期：3月 18, 2026， [https://www.codesota.com/](https://www.codesota.com/)  
44. dataset/benchmarks/coreference-resolution-on-winograd-schema, 檢索日期：3月 18, 2026， [https://gitlab.com/OpenCodePapers/OpenCodePapers/-/blob/main/dataset/benchmarks/coreference-resolution-on-winograd-schema.json](https://gitlab.com/OpenCodePapers/OpenCodePapers/-/blob/main/dataset/benchmarks/coreference-resolution-on-winograd-schema.json)  
45. dataset/benchmarks/code-generation-on-conala-ext.json ... \- GitLab, 檢索日期：3月 18, 2026， [https://gitlab.com/OpenCodePapers/OpenCodePapers/-/blob/main/dataset/benchmarks/code-generation-on-conala-ext.json](https://gitlab.com/OpenCodePapers/OpenCodePapers/-/blob/main/dataset/benchmarks/code-generation-on-conala-ext.json)  
46. Daily AI papers \- GitHub, 檢索日期：3月 18, 2026， [https://github.com/gabrielchua/daily-ai-papers](https://github.com/gabrielchua/daily-ai-papers)  
47. Daily Papers \- Hugging Face, 檢索日期：3月 18, 2026， [https://huggingface.co/papers?q=TACO%20benchmark](https://huggingface.co/papers?q=TACO+benchmark)  
48. Benchmarking the Most Reliable Document Parsing API | by Sarah Guthals, PhD | Tensorlake AI | Medium, 檢索日期：3月 18, 2026， [https://medium.com/tensorlake-ai/benchmarking-the-most-reliable-document-parsing-api-b8065686daff](https://medium.com/tensorlake-ai/benchmarking-the-most-reliable-document-parsing-api-b8065686daff)  
49. PROMPTHEUS: A Human-Centered Pipeline to Streamline Systematic Literature Reviews with Large Language Models \- MDPI, 檢索日期：3月 18, 2026， [https://www.mdpi.com/2078-2489/16/5/420](https://www.mdpi.com/2078-2489/16/5/420)  
50. Scientific Literature Hierarchy Construction and Organization \- arXiv, 檢索日期：3月 18, 2026， [https://arxiv.org/html/2504.13834v1](https://arxiv.org/html/2504.13834v1)  
51. Evaluating Prompting Strategies and Large Language Models in Systematic Literature Review Screening: Relevance and Task-Stage Classification \- arXiv.org, 檢索日期：3月 18, 2026， [https://arxiv.org/html/2510.16091v1](https://arxiv.org/html/2510.16091v1)  
52. CHIME: LLM-Assisted Hierarchical Organization of Scientific Studies for Literature Review Support, 檢索日期：3月 18, 2026， [https://llwang.net/assets/pdf/2024\_hsu\_chime\_acl.pdf](https://llwang.net/assets/pdf/2024_hsu_chime_acl.pdf)  
53. Development and evaluation of prompts for a large language model to screen titles and abstracts in a living systematic review \- PMC, 檢索日期：3月 18, 2026， [https://pmc.ncbi.nlm.nih.gov/articles/PMC12306261/](https://pmc.ncbi.nlm.nih.gov/articles/PMC12306261/)  
54. Transforming literature screening: The emerging role of large language models in systematic reviews | PNAS, 檢索日期：3月 18, 2026， [https://www.pnas.org/doi/10.1073/pnas.2411962122](https://www.pnas.org/doi/10.1073/pnas.2411962122)  
55. ICML 2026 Author Instructions, 檢索日期：3月 18, 2026， [https://icml.cc/Conferences/2026/AuthorInstructions](https://icml.cc/Conferences/2026/AuthorInstructions)  
56. LaTeX, LLMs and Boring Technology \- Eli Bendersky's website, 檢索日期：3月 18, 2026， [https://eli.thegreenplace.net/2025/latex-llms-and-boring-technology/](https://eli.thegreenplace.net/2025/latex-llms-and-boring-technology/)  
57. TeXpert: A Multi-Level Benchmark for Evaluating LATEX Code Generation by LLMs \- ACL Anthology, 檢索日期：3月 18, 2026， [https://aclanthology.org/2025.sdp-1.2.pdf](https://aclanthology.org/2025.sdp-1.2.pdf)  
58. AI-Powered LaTeX Writing: How Artificial Intelligence is Revolutionizing Academic Document Creation \- inscrive.io, 檢索日期：3月 18, 2026， [https://inscrive.io/articles/ai-latex-writing](https://inscrive.io/articles/ai-latex-writing)  
59. SciFig: Towards Automating Scientific Figure Generation \- arXiv, 檢索日期：3月 18, 2026， [https://arxiv.org/html/2601.04390v1](https://arxiv.org/html/2601.04390v1)  
60. Integrating R or python plots to latex document \- TeX, 檢索日期：3月 18, 2026， [https://tex.stackexchange.com/questions/322153/integrating-r-or-python-plots-to-latex-document](https://tex.stackexchange.com/questions/322153/integrating-r-or-python-plots-to-latex-document)  
61. Auto-claude-code-research-in-sleep (ARIS \- GitHub, 檢索日期：3月 18, 2026， [https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep)  
62. LaTeX Academic Paper Format \- Prompts \- DocsBot AI, 檢索日期：3月 18, 2026， [https://docsbot.ai/prompts/writing/latex-academic-paper-format](https://docsbot.ai/prompts/writing/latex-academic-paper-format)  
63. Developing an AI-Powered Tool for Automatic Citation Validation Using NVIDIA NIM, 檢索日期：3月 18, 2026， [https://developer.nvidia.com/blog/developing-an-ai-powered-tool-for-automatic-citation-validation-using-nvidia-nim/](https://developer.nvidia.com/blog/developing-an-ai-powered-tool-for-automatic-citation-validation-using-nvidia-nim/)  
64. New Nature paper claims to have developed a LLM that can produce lit reviews at higher quality than PHD students : r/academia \- Reddit, 檢索日期：3月 18, 2026， [https://www.reddit.com/r/academia/comments/1qwed3p/new\_nature\_paper\_claims\_to\_have\_developed\_a\_llm/](https://www.reddit.com/r/academia/comments/1qwed3p/new_nature_paper_claims_to_have_developed_a_llm/)  
65. rdyro/semantic\_bibtool: Automatic generation of bibs from a single title or a list of titles with semantic scholar API. \- GitHub, 檢索日期：3月 18, 2026， [https://github.com/rdyro/semantic\_bibtool](https://github.com/rdyro/semantic_bibtool)  
66. DevScholar: Bringing Academic Citations Into the IDE | by Sudhakar Pallaprolu | Medium, 檢索日期：3月 18, 2026， [https://medium.com/@spallaprolu/devscholar-bringing-academic-citations-into-the-ide-c62c87de1a50](https://medium.com/@spallaprolu/devscholar-bringing-academic-citations-into-the-ide-c62c87de1a50)  
67. sdabhi23/bibtexgen: A simple cli tool to generate a list of references of any paper available on Semantic Scholar as a .bib file \- GitHub, 檢索日期：3月 18, 2026， [https://github.com/sdabhi23/bibtexgen](https://github.com/sdabhi23/bibtexgen)  
68. \[PDF\] Literature-Grounded Novelty Assessment of Scientific Ideas \- Semantic Scholar, 檢索日期：3月 18, 2026， [https://www.semanticscholar.org/paper/30121edad0f2c5f935a53a08bd0d56267d3c3598](https://www.semanticscholar.org/paper/30121edad0f2c5f935a53a08bd0d56267d3c3598)  
69. Model Analysis: OpenAI o1 vs Claude 3.5 \- PromptLayer Blog, 檢索日期：3月 18, 2026， [https://blog.promptlayer.com/model-analysis-openai-o1-vs-claude-3-5/](https://blog.promptlayer.com/model-analysis-openai-o1-vs-claude-3-5/)  
70. OpenAI o1 vs Claude 3.5 Sonnet: Which One's Really Worth Your $20? \- Composio Dev, 檢索日期：3月 18, 2026， [https://composio.dev/content/openai-o1-vs-claude-3-5-sonnet](https://composio.dev/content/openai-o1-vs-claude-3-5-sonnet)  
71. I spent 8 hours testing o1 Pro ($200) vs Claude Sonnet 3.5 ($20) \- Here's what nobody tells you about the real-world performance difference : r/OpenAI \- Reddit, 檢索日期：3月 18, 2026， [https://www.reddit.com/r/OpenAI/comments/1h82pl3/i\_spent\_8\_hours\_testing\_o1\_pro\_200\_vs\_claude/](https://www.reddit.com/r/OpenAI/comments/1h82pl3/i_spent_8_hours_testing_o1_pro_200_vs_claude/)  
72. Claude 3.7 Sonnet and Claude Code \- Anthropic, 檢索日期：3月 18, 2026， [https://www.anthropic.com/news/claude-3-7-sonnet](https://www.anthropic.com/news/claude-3-7-sonnet)  
73. Claude 3.5 Sonnet vs OpenAI o1: A Comprehensive Comparison \- Helicone, 檢索日期：3月 18, 2026， [https://www.helicone.ai/blog/claude-3.5-sonnet-vs-openai-o1](https://www.helicone.ai/blog/claude-3.5-sonnet-vs-openai-o1)  
74. Claude's extended thinking \- Anthropic, 檢索日期：3月 18, 2026， [https://www.anthropic.com/news/visible-extended-thinking](https://www.anthropic.com/news/visible-extended-thinking)  
75. Anthropic releases Claude 3.7 Sonnet with extended thinking mode \- LessWrong, 檢索日期：3月 18, 2026， [https://www.lesswrong.com/posts/qkfRNcvWz3GqoPaJk/anthropic-releases-claude-3-7-sonnet-with-extended-thinking](https://www.lesswrong.com/posts/qkfRNcvWz3GqoPaJk/anthropic-releases-claude-3-7-sonnet-with-extended-thinking)  
76. Extended thinking \- Amazon Bedrock \- AWS Documentation, 檢索日期：3月 18, 2026， [https://docs.aws.amazon.com/bedrock/latest/userguide/claude-messages-extended-thinking.html](https://docs.aws.amazon.com/bedrock/latest/userguide/claude-messages-extended-thinking.html)  
77. The "think" tool: Enabling Claude to stop and think in complex tool use situations \- Anthropic, 檢索日期：3月 18, 2026， [https://www.anthropic.com/engineering/claude-think-tool](https://www.anthropic.com/engineering/claude-think-tool)  
78. Prompting best practices \- Claude API Docs, 檢索日期：3月 18, 2026， [https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)  
79. The Edit Trick: Efficient LLM Annotation of Documents | by Waleed Kadous | Medium, 檢索日期：3月 18, 2026， [https://waleedk.medium.com/the-edit-trick-efficient-llm-annotation-of-documents-d078429faf37](https://waleedk.medium.com/the-edit-trick-efficient-llm-annotation-of-documents-d078429faf37)  
80. Template Syntax Basics for LLM Prompts \- Latitude, 檢索日期：3月 18, 2026， [https://latitude.so/blog/template-syntax-basics-for-llm-prompts](https://latitude.so/blog/template-syntax-basics-for-llm-prompts)  
81. LaTeX AI Tools: Comprehensive Guide for Academic Writing \- Underleaf, 檢索日期：3月 18, 2026， [https://www.underleaf.ai/blog/latex-ai-tools-comprehensive-guide](https://www.underleaf.ai/blog/latex-ai-tools-comprehensive-guide)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAZCAYAAADnstS2AAAA3klEQVR4Xu2RqwoCQRSGj6CgeEcRBN/BZDFbLBaLGGziI/gEFrv4DmLWYtgomHwExWo1CF7+fy7LMs4Wm+AHXziX2T1zRuS3acIzvMOJU/ugCg/wBltOzcsVrmHSLfh4wambjOMJO5E4AVOROCQPL7BhYs59hFuYs02WHpzBNpzDDOzCPSxG+hRsXMEFzJocR6iHHQYWd6IvyPUNRX/ZC+fkvGU4hg+4lJgVcgPcBOFlAngSPcLI5BQ8zYfggxA7UgALcGDyioroFbFo6Ys+vBHPnksw7eT465qT+/Mdb4V+ITKqENUhAAAAAElFTkSuQmCC>