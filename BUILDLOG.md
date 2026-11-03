# Build log: where AI helped, where it was wrong

Honest record of AI assistance on this capstone. Edit anything here that is not true to your experience.

## Where AI helped
- Explained concepts one at a time before each step (Pydantic validation of model output, embeddings, cosine similarity, retries).
- Wrote and walked through the pipeline code in small pieces: schema, migrations, vision job, embeddings, guard, eval script.
- Spotted design issues from real output: free-tier limits, overconfident model scores, a too-easy eval set.

## Where AI was wrong, and what changed
- A VS Code agent and an earlier AI-generated bundle produced code in the wrong folder and out of step with what I understood. I discarded all of it and rebuilt from my last good commit.
- Retry logic, first version: the Gemini SDK has its own hidden retries that multiplied with mine, and an unbounded sleep on a 429 hung the job for 20+ minutes. A network timeout also crashed the run. Fixed: SDK retries off, waits capped at 90 s and printed, timeouts retried and logged.
- A weak unit test used `or`, so it could not fail. Rewritten.
- The guard's first subject rule compared only the last word, so "goat farming" did not match "goat". The eval exposed it; fixed by comparing word sets.
- The first similarity threshold (0.77) was a guess and cost recall; the sweep showed 0.70-0.76 was better. Now 0.74.
- A false security alarm about the `𝜋thon` file in the venv: it is a harmless CPython 3.14 feature.

## Decisions I made
- Free tier forced a model switch (gemini-3.5-flash daily cap), so images and articles were labelled by two models. Recorded per call in ai_calls.model.
- Image ground truth comes from my own labels (filename prefix plus checking the unusual images by eye), not from the model, so the eval is not circular.
- I wrote the "expected" article labels before seeing results and did not change them afterwards, even for the debatable coyotes-and-wolves article.

## Later corrections
- I (the AI) guessed that the baseline's single miss in the eval was the husky article. The output showed it was
  the "Cubs emerge from winter dens" article (the baseline put a fox first). Guesses about results were replaced
  by real output every time.
- The 36 eval articles are short texts written with AI help for this eval, not real blog posts. The expected labels
  were written before results were seen.
- A pasted command block was cut off when a terminal closed, so two test files were missing; the state check
  caught it before the commit.
