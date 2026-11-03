# Evidence

Proof that each piece works, with real terminal output.

## Definition-of-done checklist (brief section 6) and where each box is proven

- Vision output schema-validated, invalid never trusted: Phase 1 schema sections; Phase 2 (7 rejected outputs logged); tests/test_schema.py
- Low-confidence classifications flagged: Phase 3 gate, probe 1 (blurry_03 flagged at 0.55)
- Batch background job with retries: Phase 2 vision batch job; progress tracking: GET /images/status (Phase 4)
- Costs tracked per call: Phase 4 review API, probe 6 (GET /costs); budget guard demo
- Embeddings stored, posts return ranked images: Phase 3 naive matching; GET /posts/{id}/images
- Equivalent concepts match ("red fox" and "Vulpes vulpes"): section "Semantic matching of equivalent concepts"
- Guard rejects the wolf, with a reason: Phase 3 gate probe 3; probe 2; tests/test_matching.py, test_guard.py
- No confident match with reasons: Phase 4 probe 4
- DB models and indexes: db/migrations 001-006; clean-machine proof below
- Validated endpoints and review workflow: Phase 4 review API (401, 404, 409, 422 transcripts)
- Automated tests: Phase 4 budget guard, probe 2 and automated tests (38 passing)
- Labeled eval set with top-1 precision: Phase 4 evaluation (97.2%), eval_results.txt, same number in README
- README with diagram and the submission pack: README.md, capstone.yaml, EVIDENCE.md, BUILDLOG.md, .env.example, LICENSE

## Phase 1: ImageAnalysis schema (`app/schemas/image_analysis.py`)

Every Gemini response must pass through this model before it is trusted. Each rule below was tested by sending data that breaks exactly that rule and confirming Pydantic rejects it with a `ValidationError`.

### confidence above 1 is rejected

Rule: `confidence: float = Field(ge=0, le=1)`

```
1 validation error for ImageAnalysis
confidence
  Input should be less than or equal to 1 [type=less_than_equal, input_value=1.4, input_type=float]
    For further information visit https://errors.pydantic.dev/2.13/v/less_than_equal
```

### category outside the enum is rejected

Rule: `category: Category`, where `Category(str, Enum)` allows only fox, wolf, dog, bear, deer.

```
1 validation error for ImageAnalysis
category
  Input should be 'fox', 'wolf', 'dog', 'bear' or 'deer' [type=enum, input_value='cat', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/enum
```

Note: `Category.CAT` raises `AttributeError` in Python before Pydantic runs. The test must pass the raw string `"cat"`, which is what Gemini's JSON would contain.

### attributes: list length is enforced

Rule: `attributes: list[...] = Field(min_length=1, max_length=10)`

Too many items (excerpt of the output):

```
attributes
  List should have at most 10 items after validation, not 12 [type=too_long, input_value=['', 'wild', 'forest', 'd...independent', 'curious'], input_type=list]
    For further information visit https://errors.pydantic.dev/2.13/v/too_long
```

Empty list:

```
attributes
  List should have at least 1 item after validation, not 0 [type=too_short, input_value=[], input_type=list]
    For further information visit https://errors.pydantic.dev/2.13/v/too_short
```

### attributes: blank items are rejected

Rule: each item is `Annotated[str, Field(min_length=1, max_length=40)]`. The `.0` in the path shows which item failed.

```
attributes.0
  String should have at least 1 character [type=string_too_short, input_value='', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/string_too_short
```

### subject: too short is rejected

Rule: `StringConstraints(min_length=3, max_length=30, to_lower=True, strip_whitespace=True)`

```
subject
  String should have at least 3 characters [type=string_too_short, input_value='dg', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/string_too_short
```

### subject is lowercased

Input was `subject="Dog"`. Output:

```
subject='dog' category=<Category.DOG: 'dog'> attributes=['domestic', 'playful', 'cute', 'furry', 'small', 'agile', 'nocturnal', 'independent', 'curious'] caption='Hanging on the fence' confidence=1.0
```

The caption keeps its capital H on purpose: it feeds the embedding, so it is not lowercased.

### caption: empty and oversized are rejected

Rule: `StringConstraints(min_length=..., max_length=500, strip_whitespace=True)`

Empty caption (run when the minimum was 3; being raised to 10):

```
caption
  String should have at least 3 characters [type=string_too_short, input_value='', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/string_too_short
```

Oversized caption:

```
1 validation error for ImageAnalysis
caption
  String should have at most 500 characters [type=string_too_long, input_value='Hang onHang onHang onHan...onHang onHang onHang on', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/string_too_long
```

## Findings worth remembering

- `to_lower` is not a valid argument for `Field()`. Pydantic warned that extra keyword arguments are deprecated and ignored it. The correct tool is `StringConstraints`.
- `min_length` counts characters for a string and items for a list. The list and the strings inside it need separate rules.
- A test should break exactly one rule at a time, otherwise the error does not show which rule fired.



## Phase 1: database and image seeding

### Seed script registers every image once and is safe to re-run

    $ python -m scripts.seed_images
    54 new image(s) added, 54 file(s) found, 0 already registered
    $ python -m scripts.seed_images
    0 new image(s) added, 54 file(s) found, 54 already registered

### All images start as pending

     status  | count
    ---------+-------
     pending |    54

## Phase 2: vision batch job (app/vision.py, scripts/run_vision_batch.py)

Ran Gemini over the image set with retries, pacing and per-attempt cost logging.

    images:  53 done, 2 failed (dog_04 network timeout, fox_01 repeated 503; retryable later)
    ai_calls: 53 ok, 53 api_error (503/504/429/timeouts, all logged), 7 validation_error
    estimated cost at list price: about $0.11 (actual $0, free tier)
    categories: bear 5, deer 5, dog 15, fox 9, other 10, wolf 9

Findings:
- Free tier limits hit in practice: 5 requests/minute/model, a daily cap per model (switched model after the daily cap), and frequent 503 overload errors.
- Bugs found by running it: SDK-internal retries multiplied with ours and caused silent hangs; an unbounded sleep on a 429 hung the job for 20+ minutes; an httpx.ReadTimeout crashed the whole run. Each was fixed and the job is safe to re-run.
- The lite model reports confidence 1.00 on almost everything, so needs_review never fired. The mismatch guard must not depend on confidence alone.
- wolf_4.jpg was labelled coyote (other): a candidate test case for the guard and the eval set.

## Phase 3: naive matching (scripts/try_matching.py)

Cosine similarity between image caption embeddings and article embeddings, no guard yet.

    image-to-image check: fox_02's top 5 neighbours are all foxes (0.91-0.93);
    nearest wrong answer is wolf_5 at 0.883.
    category averages: same category 0.82-0.90, different 0.77-0.80 (narrow gap)
    articles with a matching image: top-1 correct for 11 of 11 (easy set, not the final eval)
    articles with no matching image: top score 0.752 (eagles) and 0.705 (carbon markets)
    lowest correct top-1 score: 0.789 (golden retriever article)

Findings:
- Similarity separates species but only by a narrow margin, so a threshold must be calibrated on labelled data, not guessed.
- Ranks beyond top-1 are noisy (deer article rank 3 is a wolf at 0.783).
- Category other covers many animals, so the guard needs a subject check for it.
- Current articles name the animal, so they are too easy: the real eval set needs ambiguous and mixed articles.

## Phase 3: article analysis (app/article_analysis.py)

Gemini classifies each article into subject, category and confidence, validated by ArticleAnalysis.

    13 of 13 articles analyzed, 13 of 13 categories match the hand labels
    the two no-image articles came back as category other: bald eagle, carbon markets
    estimated cost: about $0.022 at list price (actual $0)

## Phase 3: mismatch guard (app/guard.py, app/matching.py, scripts/run_matching.py)

Rules run in order and the first failure rejects with a reason: article confidence, image confidence,
category, subject (for category other), similarity threshold (0.77, provisional).

    unit tests: 7 passed (tests/test_guard.py)
    13 articles: wrong-category candidates rejected with reasons, for example
      deer article, rank 3: category mismatch: article is about deer ('red deer'), image shows wolf ('gray wolf')
    eagle article: all top candidates rejected -> NO CONFIDENT MATCH
    carbon markets article: top candidate rejected by the subject rule ('carbon markets' vs 'goat') -> NO CONFIDENT MATCH
    preview: 13 of 13 as expected (graded with the model's own labels, so NOT the real eval)

Open issue: the golden retriever article's best match scores 0.789 against a 0.77 threshold,
so the threshold must be calibrated on the larger eval set.

## Phase 3 gate: acceptance probes 1 and 3

Probe 3, force the wolf onto the fox post (scripts/check_pair.py):

    $ python -m scripts.check_pair "How red foxes survive" wolf_01.jpg
    Article:   How red foxes survive winter in the Highlands  [fox: red fox]
    Candidate: wolf_01.jpg  [wolf: gray wolf]  similarity 0.764
    Verdict:   REJECTED [category]
    Reason:    category mismatch: article is about fox ('red fox'), image shows wolf ('gray wolf')

The wolf's similarity (0.764) is above the 0.74 threshold, so similarity alone would have accepted it.
Only the category rule rejects it.

Probe 1, low-confidence images are flagged, not guessed:

     filename    | category | confidence | needs_review
    -------------+----------+------------+--------------
     blurry_03.jpg | other  |       0.55 | t
     blurry_01.jpg | other  |       0.75 | f
     blurry_5.jpg  | other  |       0.85 | f

    flagged images: 1

## Phase 4: evaluation against human labels (scripts/run_eval.py, full output in eval_results.txt)

Ground truth: article labels written by hand before results were seen (data/articles.json, field expected),
image labels from my own review (data/image_truth.json). The model's labels never grade themselves.

First eval, 27 easy articles, after fixing the subject rule and lowering the threshold to 0.74:

    precision 100% (21 of 21), recall 100%, refusals 6 of 6; baseline without guard 21 of 21 correct, 0 of 6 refused

That set was too easy, so nine harder articles were added (mixed animals, figurative titles,
a husky article that mentions wolves, articles that never name the animal).

Second eval, 36 articles (24 have a correct image, 12 have none), threshold 0.74, top_k 5:

    HEADLINE top-1 precision (right outcome on all 36 articles): 97.2%  (24 right images + 11 right refusals)
    matches returned 25, correct 24, precision 96.0%
    recall 100.0% (24 of 24 articles with a correct image)
    correct refusals 11 of 12
    baseline without the guard: 23 of 24 correct, 0 of 12 refused

Threshold sweep (precision / recall / correct refusals):

    0.70  96.0%  100.0%  11/12
    0.74  96.0%  100.0%  11/12
    0.76  96.0%  100.0%  11/12
    0.77  95.7%   91.7%  11/12
    0.78  95.2%   83.3%  11/12
    0.79  94.7%   75.0%  11/12
    0.80  93.8%   62.5%  11/12
    0.82 100.0%   41.7%  12/12

Findings:
- The guard's measured benefit on matchable articles: the baseline put a fox first for "Cubs emerge from winter dens"
  (the article never says bear); the guard's category check skipped it and returned a bear image.
- Of 11 correct refusals: 8 by the category rule, 1 by the subject rule, 1 by article confidence
  ("Wolves and foxes", 0.50), 1 by image confidence (hiking boots matched a flagged blurry image first).
  None came from the similarity threshold, so the threshold is untested as a safety net.
- "From wolf to Chihuahua" was refused only because the top 5 candidates were all wolf images; it depends on top_k.
- My first threshold guess (0.77) lost correct matches (the weakest scored 0.762). 0.74 sits just under it.
  0.82 would refuse the false accept but discards 58% of correct matches.
- One false accept, a known limitation: "Coyotes versus wolves" matched wolf_4.jpg (a coyote). The model gave that
  mixed article confidence 0.90 though the prompt asks for below 0.6 when several animals appear.
  The expected label was not changed after seeing the result.

## Updates to earlier sections
- The Category enum later gained "other" (the Phase 1 enum error text above predates that).
- 55 images were in the library when the vision job ran (the Phase 1 seeding snapshot above shows 54, taken earlier); 53 labelled: dog_04 and fox_01 failed on repeated Gemini 503 overload and were excluded from the eval at this point.
- Later update (2026-11-03): both images were retried successfully, embedded, and labelled by hand (dog_04 is a dog, fox_01 is a fox). The eval now covers all 55 images and the headline is unchanged at 97.2%. Sections above this line are snapshots from earlier runs; the current status is in 'Progress tracking' and eval_results.txt.

## Phase 4: review API (app/main.py, app/repo.py, db/migrations/006_reviews_and_indexes.sql)

Layers: HTTP (main.py) -> logic (guard.py, matching.py) -> data (repo.py). Writes need an X-API-Key header.

    $ curl -X POST localhost:8000/posts/1/suggestions            (no key)
    HTTP 401
    $ curl -X POST -H "X-API-Key: ..." localhost:8000/posts/1/suggestions
     id 1 rank 1 fox_10.jpg accepted
     id 2 rank 2 fox_6.jpg accepted
     id 3 rank 3 fox_02.jpg accepted
     id 4 rank 4 fox_8.jpg accepted
     id 5 rank 5 fox_4.jpg accepted
    approve rank 1 -> fox_10.jpg approved - clear fox photo
    reject rank 2  -> fox_6.jpg rejected - fox is partly hidden
    same approval again -> HTTP 200 (idempotent: one review row per suggestion)
    after re-running matching, both reviews are still there:
      1 fox_10.jpg guard: accepted review: approved
      2 fox_6.jpg guard: accepted review: rejected
      3 fox_02.jpg guard: accepted review: None

Guard cannot be silently overridden: approving a pair the guard rejected is refused.

    $ curl -X POST ... -d '{"decision":"approved"}' localhost:8000/suggestions/<eagle suggestion>/review
    {"detail":"cannot approve: the guard rejected this pair [category] category mismatch: article is about other ('bald eagle'), image shows fox ('red fox')"}
    HTTP 409

Input validation: GET /posts/abc/images -> 422, GET /posts/9999/images -> 404, review decision "maybe" -> 422.

Probe 4, a post with nothing suitable (eagles):

    no_confident_match - No confident match found. Every top candidate was rejected (category, subject).

Probe 6, the cost log (GET /costs), every AI call attributed:

    article_analysis api_error calls 20 est $ 0.0
    article_analysis ok calls 36 est $ 0.0423
    article_embedding ok calls 36 est $ 0.0003
    image_embedding ok calls 53 est $ 0.0002
    vision api_error calls 53 est $ 0.0
    vision ok calls 53 est $ 0.0955
    vision validation_error calls 7 est $ 0.0098
    TOTAL calls 258 est $ 0.148155   (estimated at list price; actual spend is $0 on the free tier)

## Phase 4: budget guard, probe 2 and automated tests

Budget guard (cost requirement): before every AI call the code adds up the logged cost in ai_calls and refuses to
continue once it reaches MAX_BUDGET_USD (default 1.0). Demo with a tiny cap; the check runs before the API call,
so no call was made:

    $ MAX_BUDGET_USD=0.01 python -m scripts.run_vision_batch --limit 1
    Model: gemini-3.5-flash
    STOPPED by the budget guard: estimated spend $0.1482 has reached the budget $0.01

Probe 2, the fox post against other animals (python -m scripts.check_pair):

    best fox photos for the post:  fox_10.jpg 0.850, fox_6.jpg 0.840, fox_02.jpg 0.839 (accepted)
    wolf_01.jpg  similarity 0.764  REJECTED [category]
    bear_01.jpg  similarity 0.736  REJECTED [category]
    dog_01.jpg   similarity 0.713  REJECTED [category]

The wolf scores above the 0.74 similarity threshold, so only the category rule keeps it out.

Automated tests (tests/test_schema.py, test_guard.py, test_matching.py, test_budget.py, test_api.py). They cover
schema validation of model output, mismatch rejection, ranking and refusal with synthetic vectors, the budget guard,
API behaviour (422, 404, 401, 409) and the eval headline precision staying at or above 90%:

    $ python -m pytest -q
    37 passed, 1 warning in 1.08s

## Clean-machine database proof

A brand-new throwaway Postgres container with only db/migrations mounted built the full schema on first start
(no manual steps; only harmless NOTICEs from ADD COLUMN IF NOT EXISTS):

    ai_calls, article_embeddings, article_metadata, articles, image_embeddings,
    image_metadata, images, reviews, suggestions   (9 tables)

## Semantic matching of equivalent concepts

The article "Vulpes vulpes: the secretive canid of hedgerows" never says "fox" in its title or text, yet:

    verdict: match - Suggested fox_8.jpg
    #1 fox_8.jpg 0.832 accepted
    #2 fox_03.jpg 0.828 accepted
    #3 fox_02.jpg 0.817 accepted

## Progress tracking (GET /images/status)

After retrying the two images that had failed on 503 overloads, all 55 are done:

    {
        "total": 55,
        "counts": {
            "done": 55
        },
        "failed": []
    }

## Final test run

    $ python -m pytest -q
    38 passed, 1 warning in 1.11s

## Cost log after the retry (2026-11-03)

Output of `python -m scripts.run_vision_batch` after retrying dog_04 and fox_01, and of `python -m scripts.embed_images`:

    article_analysis api_error         calls= 20 in=      0 out=     0 est=$0.0000
    article_analysis ok                calls= 36 in=   7820 out=  9727 est=$0.0423
    article_embedding ok               calls= 36 in=   1981 out=     0 est=$0.0003
    vision   api_error                 calls= 54 in=      0 out=     0 est=$0.0000
    vision   ok                        calls= 55 in=  72112 out= 12860 est=$0.1023
    vision   validation_error          calls=  7 in=   9107 out=   798 est=$0.0098
    image_embedding ok (after retry)   calls= 55 est_tokens=1281 est=$0.000189

All 55 images now have a successful vision call. Estimated at list price; actual spend is $0 on the free tier.
The earlier cost table (probe 6) is a snapshot from before the retry.
