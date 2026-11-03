# AI Image Understanding and Content Matching Engine

FlyRank internship capstone. The system looks at an image library, tags every image with schema-validated
metadata, and matches images to articles by meaning, not keywords. A mismatch guard refuses wrong pairings and
explains why. Good suggestions when confident, safe rejection when uncertain.

## What it does

1. A vision model (Gemini Flash, free tier) labels each image: subject, category, attributes, caption, confidence.
   Every answer is validated with Pydantic. Invalid answers are retried or recorded as failures, never trusted.
   Low-confidence images are flagged for human review.
2. Image captions and article text are embedded into the same vector space and compared with cosine similarity.
3. The mismatch guard decides whether the best candidate is actually good enough, and says why when it is not.
4. Vision and embedding calls run as background batch jobs with retries, pacing and per-call cost logging.
5. A review API lets a human approve or reject suggestions and inspect why each image was selected or refused.

## Architecture

    Images --(batch job)--> Gemini vision --> ImageAnalysis (Pydantic) --> image_metadata
                                                    '--> embed(subject + caption) --> image_embeddings
    Posts  --(batch job)--> Gemini --> ArticleAnalysis (Pydantic) --> article_metadata
                      '--> embed(title + body) --> article_embeddings

    GET /posts/{id}/images
      '--> cosine ranking (image_embeddings x article embedding)
            '--> mismatch guard
                  |-- suggested image, ranked, with reasons
                  '-- "No confident match" with reasons
    POST /posts/{id}/suggestions --> saved --> POST /suggestions/{id}/review (approve / reject)

    Every AI call --> ai_calls (tokens, estimated cost, status, attempt) --> GET /costs
    Budget guard: AI calls stop once logged spend reaches MAX_BUDGET_USD.

Layers: HTTP in `app/main.py`, rules in `app/guard.py` and `app/matching.py`, data access in `app/repo.py`,
AI calls in `app/vision.py`, `app/article_analysis.py` and `app/embeddings.py`, schemas in `app/schemas/`.

## The mismatch guard

Rules run in order and the first failure rejects the pair with a plain-English reason:

1. Article analysis confidence is at least 0.6.
2. The image was not flagged for review (its own confidence is at least 0.6).
3. Categories match (a wolf photo is refused for a fox article even when it looks similar).
4. For category "other", the subjects share a meaningful word (giraffe is refused for a kangaroo article).
5. Similarity is at least the threshold (0.74, calibrated on the eval set).

If no candidate in the top 5 passes, the answer is "no confident match" plus the reasons.

## Results (python -m scripts.run_eval)

Human ground truth: article labels written by hand before results were seen, image labels reviewed by eye.
36 articles (24 have a correct image, 12 have none), 55 images.

- Top-1 precision (right outcome on all articles): 97.2% (24 right images + 11 right refusals)
- Precision of returned matches: 96.0%, recall 100%, correct refusals 11 of 12
- Baseline without the guard (top-1 by similarity only): 23 of 24 correct, 0 of 12 refused

The full output is in `eval_results.txt` and the evidence is in `EVIDENCE.md`.

## Run it

You need Docker, Python 3.11+ and a free Gemini API key from Google AI Studio (no card).

    cp .env.example .env            # then put your Gemini key and a long random REVIEW_API_KEY in it
    docker compose up -d            # Postgres; the tables are created from db/migrations on first start
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    # place about 50 animal photos in data/images (see data/SOURCES.md), JPEG/PNG/WEBP
    python -m scripts.seed_images
    python -m scripts.run_vision_batch      # about 12 minutes on the free tier (5 requests per minute)
    python -m scripts.embed_images
    python -m scripts.seed_articles
    python -m scripts.analyze_articles
    python -m scripts.embed_articles
    python -m scripts.run_eval
    python -m pytest -q
    uvicorn app.main:app --port 8000

If a model is overloaded or out of daily quota, set `VISION_MODEL=gemini-3.1-flash-lite` for the run.
Failed images are retried by running the same command again.

## API

- `GET /health`, `GET /posts`
- `GET /posts/{id}/images` ranked candidates with the guard's verdict, or "no confident match" with reasons
- `GET /posts/{id}/check/{image_id}` force one image onto a post and see the guard's verdict
- `POST /posts/{id}/suggestions` save the verdicts (needs `X-API-Key`)
- `GET /posts/{id}/suggestions`, `GET /suggestions/{id}` inspect why an image was selected or refused
- `POST /suggestions/{id}/review` approve or reject (needs `X-API-Key`); approving a pair the guard rejected is refused
- `GET /costs` every AI call attributed with an estimated cost

## Design decisions

- Captions are embedded, not pixels: the vision model turns an image into text once, and text embeddings then
  compare it with articles. This keeps one embedding model and makes every decision explainable.
- Embeddings are stored as Postgres float arrays and compared in Python. At about 50 images this is simpler than
  pgvector; pgvector would be the next step for a large library.
- Category is checked before similarity, because similarity alone cannot separate a wolf from a fox.
- Costs are logged per attempt, including failures, so retries are visible. Prices are estimates at list price.

## Limitations

- The eval set is small (36 articles, 55 images) and the articles are short synthetic texts written for the eval,
  not real blog posts. The precision number shows the method works, not that it would hold at scale.
- One known false accept: a mixed article about coyotes and wolves matched a coyote photo. The model gave it
  confidence 0.90 although the prompt asks for a low score when several animals appear.
- The similarity threshold refused nothing on this set (category and subject rules did all the refusing), so it is
  untested as a safety net. The subject rule for "other" (shared word) is crude.
- The free tier limits drove the design: 5 requests per minute per model, daily caps, frequent 503 overloads.
  Images and articles were labelled by two models (gemini-3.5-flash and gemini-3.1-flash-lite); the model is
  recorded on every call in `ai_calls`. The lite model reports confidence 1.0 for almost everything, so the
  confidence flag rarely fires (one image flagged).
- Authorization is a single shared API key, with no per-user accounts.

## Tests

    python -m pytest -q     # 38 tests: schema validation, guard, matching, budget guard, API behaviour, eval precision
