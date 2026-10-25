# Failure Analysis

Cases where the system failed, with the likely cause. The last two columns are
filled in as each phase is evaluated, so this file doubles as the before/after
record.

Baseline: vector-only retrieval. Hit@1 0.677, Hit@5 0.935, MRR 0.768
(31 answerable questions, 9 unanswerable).

## Retrieval failures (baseline-vector-only)

| Case | What happened | Likely cause | After hybrid | After reranker |
|---|---|---|---|---|
| q003 "default 200 ok number when a new item gets saved" | Correct page chunk scored 0.57 and ranked 5th; top 4 were PUT/update chunks | The word "saved" pulled it toward update pages; the docs say "status code" | miss | |
| q004 "restrict a path parameter to predefined choices" | Enum chunk scored 0.696 and fell just outside the top 5; top 5 were numeric-validation and query-param chunks | Embedding fixated on "path parameter"; "predefined" is a lexical clue | rank 1 | |
| q007 "mark a post route as obsolete, crossed out in swagger" | Correct chunk scored 0.657; top 5 were Swagger UI configuration pages | Vocabulary gap: "obsolete / crossed out" vs "deprecated" | miss | |
| q011 "catch image uploads from a web form" | Top 4 were error-handling chunks | "catch" matched exception-handling content | miss | |
| q015 "serve css and javascript at /static" | A docs self-hosting assets page ranked 1 to 3 (top score 0.80); the real page ranked 4th | A competing page mentions the same terms and mounts the same directory | miss | |

## Hybrid search v1 (negative result)

### Metrics

| Retriever | Hit@1 | Hit@5 | MRR |
|---|---|---|---|
| Vector baseline | 0.677 | 0.935 | 0.768 |
| Fulltext only | 0.226 | 0.581 | 0.361 |
| Hybrid RRF (k=60, pool=50) | 0.581 | 0.774 | 0.672 |

### Question transitions

- **6 questions fell out of the top 5:**
  - q003: "Where can I change the default 200 ok number when a new item gets saved?" (Rank 5 -> Miss)
  - q010: "How do I make a parameter accept numbers that must be greater than zero and less than 100?" (Rank 1 -> Miss)
  - q011: "How can I catch image uploads from a web form in my handler function?" (Rank 5 -> Miss)
  - q013: "I want to share my database session across handlers and close it when done. How is that written?" (Rank 3 -> Miss)
  - q015: "How do I serve a folder of css and javascript files at the /static address?" (Rank 4 -> Miss)
  - q030: "How do I paginate large database query results in endpoints?" (Rank 1 -> Miss)

- **4 questions improved:**
  - q004: "How do I restrict a path parameter so users can only pass predefined choices?" (Miss -> Rank 1)
  - q012: "How do I throw a 404 message when a record is not found in the database?" (Rank 3 -> Rank 2)
  - q017: "Why does the browser block my React frontend when making calls to my API on a different port?" (Rank 2 -> Rank 1)
  - q036: "Why is it better to install package requirements in a separate step before putting all my python files into the container?" (Rank 2 -> Rank 1)

### Hypothesis

Postgres `ts_rank_cd` has no IDF weighting and the OR query rewards chunks repeating common words, so the full-text ranking is noisy and RRF gives it equal weight.

## Score gate

Five unanswerable questions scored 0.68 to 0.76 (q026, q027, q031, q039, q040),
inside the answerable range of 0.67 to 0.88. No similarity threshold separates
them without false refusals, so MIN_SCORE=0.60 only catches the 4 easiest
(clearly out-of-scope) questions.

## Generation failures (local Llama 3.1 8B, early runs)

| Case | What happened | Likely cause |
|---|---|---|
| Background tasks question | Answer cited the wrong chunk and invented code (some_background_task); after the prompt fix it invented app.state.background_tasks | Weak small model; invented inline code is not caught by the code-block grounding check |
| OAuth2 question | Refused at retrieval score 0.79 although the docs answer it | Retrieved chunks were overview and "See it in action" text with no implementation code |
| Optional query parameters | Answer cited chunks [2] and [4] and skipped [1], the page that answers the question | Citation choice is unreliable on an 8B model |
