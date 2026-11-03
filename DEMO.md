# Demo script (about 6 minutes)

Before you start (check the post ids with the last command; the fox post is 1 and the eagle post is 12):

    docker compose up -d
    source .venv/bin/activate
    uvicorn app.main:app --port 8000 > /tmp/api.log 2>&1 &
    export KEY=$(grep '^REVIEW_API_KEY=' .env | cut -d= -f2)
    curl -s localhost:8000/posts | python -c "import sys,json; [print(p['id'], p['title']) for p in json.load(sys.stdin)]"

## 1. A folder of photos, processed (1 min)

Show the stored tags and captions, then the progress endpoint:

    docker exec -i image-relevance-db psql -U relevance -d image_relevance -c "SELECT i.filename, m.category, m.confidence, left(m.caption, 55) AS caption FROM image_metadata m JOIN images i ON i.id = m.image_id ORDER BY i.id LIMIT 8;"
    curl -s localhost:8000/images/status | python -m json.tool

Say: every answer is schema-validated; blurry_03.jpg was flagged at confidence 0.55 instead of being trusted.
Optional live run if the free quota allows: `python -m scripts.run_vision_batch --limit 2`.

## 2. The red-fox article surfaces the fox photo (1 min)

    curl -s localhost:8000/posts/1/images | python -c "import sys,json; d=json.load(sys.stdin); print(d['message']); [print(c['rank'], c['filename'], c['similarity'], c['decision']['rule']) for c in d['candidates']]"

## 3. Force the wolf: the guard refuses it (1 min)

    python -m scripts.check_pair "How red foxes survive" wolf_01.jpg

Say: the wolf scores 0.764, above the 0.74 similarity threshold. Similarity alone would accept it.
The category rule is what refuses it, and it says why.

## 4. A post where nothing fits (1 min)

    curl -s localhost:8000/posts/12/images | python -c "import sys,json; d=json.load(sys.stdin); print(d['verdict']); print(d['message']); [print(c['filename'], '-', c['decision']['reason']) for c in d['candidates'][:3]]"

## 5. Approve one, reject another: the review trail (1 min)

    curl -s -X POST -H "X-API-Key: $KEY" localhost:8000/posts/1/suggestions > /dev/null
    IDS=$(curl -s localhost:8000/posts/1/suggestions | python -c "import sys,json; print(' '.join(str(s['id']) for s in json.load(sys.stdin)))"); set -- $IDS
    curl -s -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" -d '{"decision":"approved","note":"clear fox photo"}' localhost:8000/suggestions/$1/review > /dev/null
    curl -s -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" -d '{"decision":"rejected","note":"fox is partly hidden"}' localhost:8000/suggestions/$2/review > /dev/null
    curl -s localhost:8000/posts/1/suggestions | python -c "import sys,json; [print(s['rank'], s['filename'], 'guard:', s['guard_decision'], 'review:', s['review_decision'], '-', s['review_note']) for s in json.load(sys.stdin)]"

## 6. Close with the number (1 min)

    python -m scripts.run_eval | head -12

Say: "Top-1 precision: 97.2%, measured on 36 articles against labels I wrote before seeing the results.
Without the guard, plain similarity gets 23 of 24 right and refuses none of the 12 articles that have no image."

Final line: good suggestions when confident, safe rejection when uncertain. That is production AI.
