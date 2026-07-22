"""
Core recommendation logic: loads the MovieLens-style dataset, builds a
TF-IDF genre similarity matrix, and exposes simple lookup/recommend functions.

No pandas dependency -- the dataset is parsed with plain Python, and
scikit-learn's TfidfVectorizer works directly on a list of strings.
"""
import os
import re
import csv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

DATA_PATH = os.path.join(os.path.dirname(__file__), "movies.dat")

# Small built-in stopword list so we don't depend on NLTK's downloaded corpora
# (those downloads are a common source of flaky deploys).
_STOPWORDS = {
    "a", "an", "the", "i", "me", "my", "you", "your", "he", "she", "it", "we",
    "they", "is", "am", "are", "was", "were", "be", "been", "being", "do",
    "does", "did", "have", "has", "had", "and", "or", "but", "if", "so",
    "of", "in", "on", "at", "to", "for", "with", "about", "like", "love",
    "loved", "liked", "enjoy", "enjoyed", "movie", "film", "watch", "watched",
    "recommend", "please", "can", "could", "would", "want", "show", "tell",
    "what", "who", "which", "when", "where", "why", "how", "some", "any",
    "other", "similar", "something",
}


def _tokenize(text: str):
    return re.findall(r"[a-z0-9']+", text.lower())


class MovieRecommender:
    def __init__(self, data_path: str = DATA_PATH):
        self.titles = []   # list[str], index-aligned with self.genres
        self.genres = []   # list[str] of pipe-joined genre strings

        with open(data_path, "r", encoding="latin-1") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line:
                    continue
                parts = line.split("::")
                if len(parts) < 3:
                    continue
                _movie_id, title, genre_str = parts[0], parts[1], parts[2]
                if genre_str == "(no genres listed)":
                    genre_str = ""
                self.titles.append(title)
                self.genres.append(genre_str)

        tfidf = TfidfVectorizer(stop_words="english")
        tfidf_matrix = tfidf.fit_transform(self.genres)
        self.cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)

        # Map lowercase title -> row index for fast, case-insensitive lookup
        self._title_to_index = {t.lower(): i for i, t in enumerate(self.titles)}

    def search_titles(self, query: str, limit: int = 8):
        """Return up to `limit` titles that contain the query substring."""
        query = (query or "").strip().lower()
        if not query:
            return []
        results = []
        for title in self.titles:
            if query in title.lower():
                results.append(title)
                if len(results) >= limit:
                    break
        return results

    def resolve_title(self, text: str):
        """Best-effort match of free text to a known movie title.

        Tries, in order: an exact title match, a whole-string substring
        match, then progressively shorter word-windows (so "I loved Toy
        Story a lot" still finds "Toy Story (1995)" even though the
        sentence as a whole isn't a substring of any title).
        """
        raw = (text or "").strip().lower()
        if not raw:
            return None

        if raw in self._title_to_index:
            return self.titles[self._title_to_index[raw]]

        whole_match = self.search_titles(raw, limit=1)
        if whole_match:
            return whole_match[0]

        tokens = [t for t in _tokenize(raw) if t not in _STOPWORDS]
        if not tokens:
            return None

        # Try longest-to-shortest contiguous windows of the meaningful
        # tokens so multi-word titles are preferred over single-word ones.
        for window in range(len(tokens), 0, -1):
            starts = range(0, len(tokens) - window + 1)
            # Prefer longer, more specific phrases first within this window size
            ordered_starts = sorted(
                starts, key=lambda s: -len(tokens[s:s + window][-1])
            )
            for start in ordered_starts:
                phrase = " ".join(tokens[start:start + window])
                match = self.search_titles(phrase, limit=1)
                if match:
                    return match[0]
        return None

    def recommend(self, title: str, top_n: int = 5):
        """Return up to `top_n` titles most similar (by genre) to `title`."""
        idx = self._title_to_index.get((title or "").strip().lower())
        if idx is None:
            return []
        sim_scores = list(enumerate(self.cosine_sim[idx]))
        sim_scores.sort(key=lambda x: x[1], reverse=True)
        sim_scores = [s for s in sim_scores if s[0] != idx][:top_n]
        return [self.titles[i] for i, _ in sim_scores]
