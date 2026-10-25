# Evaluation Results

Summary of retrieval evaluation results across development set (v1) and held-out evaluation set (v2).

## 1. Development Set (v1) Results

Evaluated on `eval/questions.jsonl` (31 answerable questions, 9 unanswerable questions, N=31).

| Retriever | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---|---|---|---|
| Vector-only (`bge-small-en-v1.5`) | 0.6774 (21/31) | 0.8387 (26/31) | 0.9355 (29/31) | 0.7683 |
| Full-text only (Postgres `ts_rank_cd`) | 0.2258 (7/31) | 0.4839 (15/31) | 0.5806 (18/31) | 0.3613 |
| Hybrid-Fulltext (deterministic RRF) | 0.5484 (17/31) | 0.7742 (24/31) | 0.7742 (24/31) | 0.6505 |
| BM25-only (Okapi, k1=1.5, b=0.75) | 0.5806 (18/31) | 0.8710 (27/31) | 0.8710 (27/31) | 0.7151 |
| **Hybrid-BM25** (pool=50, rrf_k=60) | **0.7097 (22/31)** | **0.9032 (28/31)** | **0.9355 (29/31)** | **0.8091** |

---

## 2. Held-Out Evaluation Set (v2) Results

Evaluated on `eval/questions_v2.jsonl` (20 answerable questions, 11 unanswerable questions, N=20). Candidate parameters were frozen in `eval/PREREGISTRATION.md` prior to running v2 evaluations.

| Retriever | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---|---|---|---|
| Vector-only (`bge-small-en-v1.5`) | 0.5000 (10/20) | 0.7500 (15/20) | 0.8500 (17/20) | 0.6450 |
| BM25-only (diagnostic) | 0.5000 (10/20) | 0.7500 (15/20) | 0.8000 (16/20) | 0.6183 |
| **Hybrid-BM25** (pool=50, rrf_k=60) | **0.6500 (13/20)** | **0.8000 (16/20)** | **0.9000 (18/20)** | **0.7392** |

Hybrid improved 6 questions and regressed 2 (v001, v006); Hit@1 differs by 3 questions, Hit@5 by 1.

---

## 3. Pre-Registration Verdict

Under the decision rule specified in `eval/PREREGISTRATION.md`:
> *"hybrid-bm25 is reported as an improvement only if its MRR on v2 is higher than vector-only AND its Hit@5 is not lower. Otherwise the result is reported as no improvement."*

- **MRR**: Hybrid-BM25 MRR (**0.7392**) > Vector-Only MRR (**0.6450**) — higher by +0.0942.
- **Hit@5**: Hybrid-BM25 Hit@5 (**0.9000**, 18/20) $\ge$ Vector-Only Hit@5 (**0.8500**, 17/20) — not lower (+0.0500, +1 hit).

**Verdict**: **`improvement`**

---

## 4. Post-hoc sensitivity check (not pre-registered)

To test sensitivity against potential vocabulary leakage, we evaluate the effect of excluding the five questions whose wording was not revised in the review pass (v001, v006, v010, v013, v019), which still share vocabulary with their pages, and recomputing metrics on the other 15 v2 answerable questions.

### Questions Excluded and Rationale
All five questions contain lexical overlap with their page headings or verbatim answer sentences:
1. **`v001`**: *"How can I declare single primitive values like integers or strings as part of the JSON request body?"*
   - Target page: `docs/fastapi/tutorial/body-multiple-params.md`
   - Overlap: Title *"Body - Multiple Parameters"*, headings *"Singular values in body"*, *"Embed a single body parameter"*, and answer sentence contain `body`, `values`, `single`.
2. **`v006`**: *"How do I specify the schema of the returned data using standard Python type annotations on my endpoint function?"*
   - Target page: `docs/fastapi/tutorial/response-model.md`
   - Overlap: Headings *"Response Model - Return Type"*, *"Type Annotations and Tooling"*, *"FastAPI Data Filtering"*, and answer sentence contain `type`, `annotations`, `data`, `function`, `returned`.
3. **`v010`**: *"What is the format used by a JSON Web Token to serialize a JSON object into a transmission string?"*
   - Target page: `docs/fastapi/tutorial/security/oauth2-jwt.md`
   - Overlap: Title *"Bearer with JWT tokens"*, headings *"About JWT"*, *"Handle JWT tokens"*, and answer sentence contain `token`, `JWT`, `JSON`, `object`, `string`.
4. **`v013`**: *"How do I define startup logic that must run before the application starts receiving incoming requests?"*
   - Target page: `docs/fastapi/advanced/events.md`
   - Overlap: Headings *"`startup` event"*, *"`startup` and `shutdown` together"*, and answer sentence contain `startup`, `logic`, `define`, `application`.
5. **`v019`**: *"Why is lru_cache recommended when reading application configurations from environment files?"*
   - Target page: `docs/fastapi/advanced/settings.md`
   - Overlap: Title *"Settings and Environment Variables"*, headings *"Creating the `Settings` only once with `lru_cache`"*, *"Reading a `.env` file"*, and answer sentence contain `lru_cache`, `reading`, `environment`.

### Recomputed Metrics on the other 15 v2 answerable questions (N=15)

Recomputing metrics from the saved baseline JSONs on the other 15 v2 answerable questions:

| Retriever | Hit@1 | Hit@5 | MRR |
|---|---|---|---|
| Vector-only | 0.4667 (7/15) | 0.8667 (13/15) | 0.6467 |
| Hybrid-BM25 | **0.7333 (11/15)** | **0.9333 (14/15)** | **0.8167** |
| **Delta** | **+0.2667 (+4 hits)** | **+0.0667 (+1 hit)** | **+0.1700** |

On the other 15 v2 answerable questions, the direction is unchanged: MRR delta is +0.1700, Hit@1 is +4 hits, and Hit@5 is +1 hit.

---

## 5. Limitations

1. **Development Set Overfitting Risk**: The v1 evaluation set (`eval/questions.jsonl`, 31 questions) was AI-drafted and used during iterative development to diagnose full-text retrieval flaws and select BM25 parameters.
2. **Held-Out Sample Granularity**: The held-out set (`eval/questions_v2.jsonl`) contains 20 answerable questions. Due to the sample size, each question represents exactly 5.0 percentage points on Hit@1 and Hit@5, meaning small shifts produce discrete jumps.
3. **Sensitivity Findings**: On the 15 remaining questions the direction is unchanged (MRR +0.170, Hit@5 +1 question); this is consistent with the gain not depending on the five unrevised questions, but 15 questions cannot establish it.
4. **Score-Based Refusal Gating Cannot Be Fixed by Thresholding**: Vector similarity scores between relevant documentation chunks and out-of-domain / unanswerable questions overlap significantly:
   - **v1**: Lowest answerable top score was **0.669** (`q027`), whereas the highest unanswerable top score was **0.759** (`q039`).
   - **v2**: Lowest answerable top score was **0.682** (`v015`), whereas the highest unanswerable top score was **0.755** (`v030`).
   No static cosine similarity threshold between 0.60 and 0.80 can separate answerable queries from near-miss unanswerable queries without creating severe false refusals. A reranker or semantic refusal classifier is necessary.
