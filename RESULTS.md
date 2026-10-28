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
| Hybrid-BM25 (pool=50, rrf_k=60) | 0.7097 (22/31) | 0.9032 (28/31) | 0.9355 (29/31) | 0.8091 |
| **Hybrid-BM25 + Rerank** (`bge-reranker-base`) | **0.7742 (24/31)** | **0.9355 (29/31)** | **0.9355 (29/31)** | **0.8441** |

### Hybrid-BM25 vs Hybrid-BM25-Rerank (v1, N=31)

| Retriever | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---|---|---|---|
| Hybrid-BM25 | 0.7097 (22/31) | 0.9032 (28/31) | 0.9355 (29/31) | 0.8091 |
| Hybrid-BM25 + Rerank | **0.7742 (24/31)** | **0.9355 (29/31)** | **0.9355 (29/31)** | **0.8441** |
| Delta | +0.0645 (+2) | +0.0323 (+1) | 0.0000 (0) | +0.0350 |

- Improved (4 questions): `q003` (rank 4 -> 3), `q013` (rank 2 -> 1), `q018` (rank 2 -> 1), `q020` (rank 2 -> 1).
- Regressed (1 question): `q008` (rank 1 -> 2).

---

## 2. Held-Out Evaluation Set (v2) Results

Evaluated on `eval/questions_v2.jsonl` (20 answerable questions, 11 unanswerable questions, N=20). Candidate parameters were frozen in `eval/PREREGISTRATION.md` and `eval/PREREGISTRATION_RERANK.md` prior to running evaluations.

| Retriever | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---|---|---|---|
| Vector-only (`bge-small-en-v1.5`) | 0.5000 (10/20) | 0.7500 (15/20) | 0.8500 (17/20) | 0.6450 |
| BM25-only (diagnostic) | 0.5000 (10/20) | 0.7500 (15/20) | 0.8000 (16/20) | 0.6183 |
| Hybrid-BM25 (pool=50, rrf_k=60) | 0.6500 (13/20) | 0.8000 (16/20) | 0.9000 (18/20) | 0.7392 |
| **Hybrid-BM25 + Rerank** (`bge-reranker-base`) | **0.7500 (15/20)** | **0.9000 (18/20)** | **0.9000 (18/20)** | **0.8083** |

### Hybrid-BM25 vs Hybrid-BM25-Rerank (v2, N=20)

| Retriever | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---|---|---|---|
| Hybrid-BM25 | 0.6500 (13/20) | 0.8000 (16/20) | 0.9000 (18/20) | 0.7392 |
| Hybrid-BM25 + Rerank | **0.7500 (15/20)** | **0.9000 (18/20)** | **0.9000 (18/20)** | **0.8083** |
| Delta | +0.1000 (+2) | +0.1000 (+2) | 0.0000 (0) | +0.0691 |

- Improved (3 questions): `v006` (rank 5 -> 1), `v007` (rank 4 -> 1), `v010` (rank 3 -> 1).
- Regressed (2 questions): `v009` (rank 2 -> 3), `v018` (rank 1 -> 3).
*(Note: Per pre-registration instructions, per-type metrics are not reported for v2 due to small bucket sizes).*

---

## 3. Pre-Registration Verdicts

### Phase 2: Hybrid-BM25 Verdict
Under the decision rule specified in `eval/PREREGISTRATION.md`:
> *"hybrid-bm25 is reported as an improvement only if its MRR on v2 is higher than vector-only AND its Hit@5 is not lower. Otherwise the result is reported as no improvement."*

- **MRR**: Hybrid-BM25 MRR (**0.7392**) > Vector-Only MRR (**0.6450**) — higher by +0.0942.
- **Hit@5**: Hybrid-BM25 Hit@5 (**0.9000**, 18/20) $\ge$ Vector-Only Hit@5 (**0.8500**, 17/20) — not lower (+0.0500, +1 hit).

**Verdict**: **`improvement`**

### Phase 3: Cross-Encoder Reranker Verdict
Under the decision rule specified in `eval/PREREGISTRATION_RERANK.md` and `eval/PREREGISTRATION_RERANK_ADDENDUM.md`:
> *"hybrid-bm25-rerank is reported as an improvement only if its MRR on v2 is higher than hybrid-bm25 AND its Hit@5 is not lower. Otherwise the result is reported as no improvement."*

- **MRR**: Hybrid-BM25-Rerank MRR (**0.8083**) > Hybrid-BM25 MRR (**0.7392**) — higher by +0.0691.
- **Hit@5**: Hybrid-BM25-Rerank Hit@5 (**0.9000**, 18/20) $\ge$ Hybrid-BM25 Hit@5 (**0.9000**, 18/20) — not lower (0.0000, 0 hits).

**Verdict**: **`improvement`**

---

## 4. Post-hoc sensitivity check (not pre-registered)

To test sensitivity against potential vocabulary leakage, we evaluate the effect of excluding the five questions whose wording was not revised in the review pass (`v001`, `v006`, `v010`, `v013`, `v019`), which still share vocabulary with their pages, and evaluate on (a) the remaining 15 v2 answerable questions and (b) the 5 unrevised questions.

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

### Recomputed Metrics for Vector vs Hybrid-BM25 on the other 15 questions (N=15)

| Retriever | Hit@1 | Hit@5 | MRR |
|---|---|---|---|
| Vector-only | 0.4667 (7/15) | 0.8667 (13/15) | 0.6467 |
| Hybrid-BM25 | **0.7333 (11/15)** | **0.9333 (14/15)** | **0.8167** |
| **Delta** | **+0.2667 (+4 hits)** | **+0.0667 (+1 hit)** | **+0.1700** |

### Post-hoc Sensitivity for Hybrid-BM25 vs Reranker

| Subset | Metric | Hybrid-BM25 | Hybrid-BM25-Rerank | Delta |
|---|---|---|---|---|
| **The other 15 questions** | Hit@1 | 0.7333 (11/15) | 0.7333 (11/15) | 0.0000 (0) |
| | Hit@5 | 0.9333 (14/15) | 0.9333 (14/15) | 0.0000 (0) |
| | MRR | 0.8167 | 0.8111 | -0.0056 |
| **The 5 unrevised questions** | Hit@1 | 0.4000 (2/5) | 0.8000 (4/5) | +0.4000 (+2) |
| | Hit@5 | 0.8000 (4/5) | 0.8000 (4/5) | 0.0000 (0) |
| | MRR | 0.5067 | 0.8000 | +0.2933 |

On the 15 remaining questions, reranking produces no change in Hit@1 or Hit@5, with an MRR delta of -0.0056 (`v007` improved 4 -> 1; `v009` regressed 2 -> 3, `v018` regressed 1 -> 3). The overall +0.0691 MRR gain on v2 is driven by two of the five unrevised questions (`v006` rank 5 -> 1, `v010` rank 3 -> 1).

---

## 5. Latency

Cross-encoder reranking (`BAAI/bge-reranker-base`, `max_length=512`, `device="cpu"` scoring 20 candidate pairs per question):
- **v1**: mean 7.4 s/query (7,435 ms), max 10.0 s/query (9,958 ms)
- **v2**: mean 7.8 s/query (7,775 ms), max 9.9 s/query (9,861 ms)
- Inference on CPU adds approximately 7.4 to 7.8 seconds of latency per query compared to non-reranked retrieval (<50 ms).

---

## 6. Refusal Gate Analysis

Comparison of the cosine gate (`MIN_SCORE = 0.60` on `top_vector_score`) vs the rerank gate (`MIN_SCORE = 0.502152` on `top_rerank_score`, computed strictly from the single lowest v1 answerable top rerank score, `q011`):

| Dataset | Metric | Cosine Gate (0.60) | Rerank Gate (0.502152) |
|---|---|---|---|
| **v1** (N=31 ans, 9 unans) | Unanswerable Refusal Rate | 0.4444 (4/9) | **0.5556 (5/9)** |
| | Answerable False-Refusal Rate | 0.0000 (0/31) | 0.0000 (0/31) |
| | Unanswerable Passing Gate | `q026`, `q027`, `q031`, `q039`, `q040` (5 passed) | `q026`, `q031`, `q034`, `q039` (4 passed) |
| **v2** (N=20 ans, 11 unans) | Unanswerable Refusal Rate | 0.3636 (4/11) | **0.5455 (6/11)** |
| | Answerable False-Refusal Rate | 0.0000 (0/20) | 0.0000 (0/20) |
| | Unanswerable Passing Gate | `v021`, `v022`, `v023`, `v024`, `v029`, `v030`, `v031` (7 passed) | `v023`, `v024`, `v029`, `v030`, `v031` (5 passed) |

---

## 7. Limitations

1. **Development Set Overfitting Risk**: The v1 evaluation set (`eval/questions.jsonl`, 31 questions) was AI-drafted and used during iterative development to diagnose full-text retrieval flaws and select BM25 parameters.
2. **Held-Out Sample Granularity**: The held-out set (`eval/questions_v2.jsonl`) contains 20 answerable questions. Due to the sample size, each question represents exactly 5.0 percentage points on Hit@1 and Hit@5, meaning small shifts produce discrete jumps.
3. **Sensitivity Findings**: On the 15 remaining questions the direction for hybrid-bm25 vs vector is unchanged (MRR +0.170, Hit@5 +1 question); this is consistent with the gain not depending on the five unrevised questions, but 15 questions cannot establish it. For the reranker, net gains on v2 are concentrated on the unrevised questions.
4. **Score-Based Refusal Gating Cannot Be Fixed by Thresholding Alone**: Vector similarity scores between relevant documentation chunks and out-of-domain / unanswerable questions overlap significantly:
   - **v1**: Lowest answerable top score was **0.669** (`q027`), whereas the highest unanswerable top score was **0.759** (`q039`).
   - **v2**: Lowest answerable top score was **0.682** (`v015`), whereas the highest unanswerable top score was **0.755** (`v030`).
5. **Reranker Candidate Ceiling**: The reranker re-scores only the top 20 candidates returned by hybrid-bm25; it cannot recover recall for items absent from this pool. As a result, Hit@5 was unchanged on both v1 (0.9355) and v2 (0.9000). For example, `q007` had no expected-page chunk anywhere among the 20 candidates, and `q015` had its best expected chunk reranked to rank 6 (score 0.6167), just missing the top 5.
6. **Rerank Gate Calibration**: The rerank refusal threshold (0.502152) is set by the single lowest v1 answerable score (`q011`). While it achieved zero false refusals on both v1 (0/31) and v2 (0/20) and improved unanswerable refusal from ~36-44% to ~55%, setting a gate threshold based on the minimum of a small sample carries variance and calibration risks on larger distributions.

---

## Answer quality (end-to-end, local Llama 3.1 8B)

Pipeline: default /ask configuration (hybrid-BM25, k=5, cosine gate 0.60 on
top_vector_score, no reranker, local llama31-rag, temperature 0). One run per
set; a 5-question rerun gave identical answers and refusal outcomes. Raw
results: eval/baselines/answers-v1.json, answers-v2.json.

| | v1 (development) | v2 (held-out) |
|---|---|---|
| Answerable questions | 31 | 20 |
| Expected page in top 5 | 29 | 18 |
| Refused although expected page was retrieved | 3 (2 after manual review) | 1 |
| Answered, expected page cited | 23 of 26 | 13 of 17 |
| Unanswerable questions refused | 9 of 9 | 11 of 11 |
| Mean / max latency | 18.5 s / 63.7 s | 13.3 s / 35.4 s |

Unanswerable refusals here count both the cosine gate and the model's own refusal; the gate alone refused about 36-44% (see gate analysis above).

Refusals: of the 4 refusals reviewed by hand, 3 were real false refusals (q011,
q024, v016: the answer was in the retrieved chunks) and 1 was defensible (q002:
the OAuth2PasswordBearer setup was not in the chunks). Reviews are in
eval/reviews/false-refusals.md.

Answer correctness (manual review of samples; first 15 answered questions by id
in each set, plus the 2 flagged v1 answers; not random):

| Sample | Correct | Partly | Incorrect | n |
|---|---|---|---|---|
| v1 | 7 | 4 | 4 | 15 |
| v1 flagged (answers with a warning) | 0 | 2 | 0 | 2 |
| v2 | 7 | 5 | 3 | 15 |

Method note: these verdicts are first-pass drafts written by Claude and checked
by the author against each cited chunk. This departs from the pre-registered
protocol (author-only scoring). No LLM judged any answer without author review.

Findings:
- "Cites an expected page" overstates correctness: q003, q010, q018 (v1) and
  v013, v014 (v2) cite an expected page but are incorrect or only partly right
  (a misread example, ge/le instead of gt/lt, advice reversed, deprecated
  on_event method instead of lifespan).
- The model sometimes answers a different question than the one asked (v1:
  q003, q010; v2: v001, v006, v017) and sometimes invents code not in the
  context (q012, q015, v017).
- The "code block not found in cited sources" warning caught real deviations in
  both flagged answers (q021, q038).
- Some answers cite nothing (q013, q015, v003, v017); those could not be checked
  against retrieved text.
- Some retrieved top-5 sets contain duplicate text (q039: 2 identical chunks,
  q040: 4 identical chunks; both unanswerable questions).

Limitations: 15-answer samples (one answer is 6.7 percentage points) and not
random; unanswerable refusals come from the cosine gate and the model's own
refusal habit, which also produced the false refusals; the 4 reviewed false
refusals are the only ones examined, 3 of them real.
