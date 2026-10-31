IMAGE_PROMPT = """You are labelling photos of animals for a content library.
Look at the image and return ONE JSON object with exactly these keys:

- "subject": short lowercase name of the main animal, 3-30 characters, e.g. "red fox"
- "category": one of "fox", "wolf", "dog", "bear", "deer", "other".
  Use "other" for any animal not in that list, or when no animal is visible.
- "attributes": list of 1-10 short visual descriptors, each under 40 characters
- "caption": one sentence (10-500 characters) describing the image and naming the animal
- "confidence": number from 0 to 1, how sure you are about subject and category.
  Use a value below 0.6 if the image is blurry, partly hidden, or the animal is hard to
  tell apart from a similar one (for example fox vs dog vs wolf).

Return only the JSON object, no other text."""
