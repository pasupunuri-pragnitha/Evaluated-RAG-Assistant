# Failure Analysis

Cases where the system failed, with the likely cause. The last two columns are
filled in as each phase is evaluated, so this file doubles as the before/after
record.

Baseline: vector-only retrieval. Hit@1 0.677, Hit@5 0.935, MRR 0.768
(31 answerable questions, 9 unanswerable).

## Retrieval failures (baseline-vector-only)

| Case | What happened | Likely cause | After hybrid | After reranker |
|---|---|---|---|---|
| q003 "default 200 ok number when a new item gets saved" | Correct page chunk scored 0.57 and ranked 5th; top 4 were PUT/update chunks | The word "saved" pulled it toward update pages; the docs say "status code" | | |
| q004 "restrict a path parameter to predefined choices" | Enum chunk scored 0.696 and fell just outside the top 5; top 5 were numeric-validation and query-param chunks | Embedding fixated on "path parameter"; "predefined" is a lexical clue | | |
| q007 "mark a post route as obsolete, crossed out in swagger" | Correct chunk scored 0.657; top 5 were Swagger UI configuration pages | Vocabulary gap: "obsolete / crossed out" vs "deprecated" | | |
| q011 "catch image uploads from a web form" | Top 4 were error-handling chunks | "catch" matched exception-handling content | | |
| q015 "serve css and javascript at /static" | A docs self-hosting assets page ranked 1 to 3 (top score 0.80); the real page ranked 4th | A competing page mentions the same terms and mounts the same directory | | |

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
