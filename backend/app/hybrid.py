"""Hybrid content, collaborative and popularity recommender with safe catalogue fallback."""

import json
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


PRODUCTS = json.loads(
    Path(__file__).with_name("catalog.json").read_text(encoding="utf-8")
)


class Hybrid:
    """Return up to five relevant products, including rediscovery when needed."""

    MODEL_VERSION = "hybrid-v4"

    def __init__(self):
        self.index = {product["id"]: i for i, product in enumerate(PRODUCTS)}
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.matrix = self.vectorizer.fit_transform(
            [product.get("tags", "") for product in PRODUCTS]
        )
        self.feature_names = self.vectorizer.get_feature_names_out()

    def recommend(self, history, signals, limit=5, mode="hybrid", refresh_seed=0):
        total = len(PRODUCTS)
        if total == 0:
            return []

        # Product requirement: show exactly five whenever five exist.
        limit = min(5, total)
        history = history or []
        signals = signals or []

        event_weights = {"view": 1.0, "click": 2.5, "purchase": 5.0}
        preference = np.zeros(total, dtype=float)
        viewed, clicked, purchased = set(), set(), set()

        # History is newest-first in storage. Give recent and high-intent
        # interactions more influence, while retaining older interests.
        for position, event in enumerate(history):
            product_id = event.get("product_id")
            event_type = event.get("event_type")
            if product_id not in self.index or event_type not in event_weights:
                continue

            idx = self.index[product_id]
            dwell = max(0.0, float(event.get("dwell_seconds") or 0))
            weight = event_weights[event_type] * (1 + min(dwell, 120) / 240)
            weight *= 0.98 ** position
            preference[idx] += weight

            if event_type == "view":
                viewed.add(idx)
            elif event_type == "click":
                clicked.add(idx)
            elif event_type == "purchase":
                purchased.add(idx)

        preference = np.minimum(preference, 30.0)
        interacted = viewed | clicked | purchased

        # Build user-item matrix from asynchronously processed signals.
        users = sorted({s.get("user_id") for s in signals if s.get("user_id")})
        user_index = {user: i for i, user in enumerate(users)}
        item_users = np.zeros((len(users), total), dtype=float)

        for signal in signals:
            product_id = signal.get("product_id")
            user_id = signal.get("user_id")
            if product_id not in self.index or user_id not in user_index:
                continue
            item_users[user_index[user_id], self.index[product_id]] = min(
                float(signal.get("weight") or 0), 30.0
            )

        popularity = (
            (item_users > 0).sum(axis=0).astype(float)
            if len(users) else np.zeros(total, dtype=float)
        )
        if popularity.max() > 0:
            popularity /= popularity.max()

        # Content profile is built from the event history, so it can update
        # immediately without waiting for the background Kafka consumer.
        content = np.zeros(total, dtype=float)
        profile = None
        if preference.sum() > 0:
            profile = np.asarray(preference @ self.matrix).reshape(1, -1)
            content = cosine_similarity(profile, self.matrix).flatten()
            if content.max() > 0:
                content /= content.max()

        collaborative = np.zeros(total, dtype=float)
        if len(users) >= 2 and preference.sum() > 0:
            item_similarity = cosine_similarity(item_users.T)
            np.fill_diagonal(item_similarity, 0)
            collaborative = (preference @ item_similarity) / preference.sum()
            if collaborative.max() > 0:
                collaborative /= collaborative.max()

        if mode == "popularity":
            weights = {"content": 0.0, "collaborative": 0.0, "popularity": 1.0}
        else:
            available = {
                "content": content.max() > 0,
                "collaborative": collaborative.max() > 0,
                "popularity": popularity.max() > 0,
            }
            base = {"content": 0.65, "collaborative": 0.25, "popularity": 0.10}
            denominator = sum(base[k] for k in base if available[k])
            weights = {
                k: (base[k] / denominator if available[k] and denominator else 0.0)
                for k in base
            }

        # Score every catalogue item. Unseen products get a small discovery
        # bonus, but seen/purchased items remain eligible when the catalogue
        # is small or the user's history covers most products.
        rng = np.random.default_rng(max(0, int(refresh_seed)))
        exploration = rng.uniform(0.0, 0.015, total) if refresh_seed else np.zeros(total)
        results = []

        for idx, product in enumerate(PRODUCTS):
            components = {
                "content": float(content[idx]),
                "collaborative": float(collaborative[idx]),
                "popularity": float(popularity[idx]),
            }
            contributions = {k: components[k] * weights[k] for k in components}
            score = sum(contributions.values())

            rank_score = score
            if preference.sum() > 0 or popularity.max() > 0:
                if idx not in interacted:
                    rank_score += 0.035
                elif idx in viewed:
                    rank_score -= 0.008
                elif idx in clicked:
                    rank_score -= 0.015
                elif idx in purchased:
                    rank_score -= 0.025

            rank_score += float(exploration[idx])

            shared_terms = []
            if profile is not None:
                overlap = profile.flatten() * self.matrix[idx].toarray().flatten()
                top = np.argsort(-overlap)[:4]
                shared_terms = [
                    str(self.feature_names[j]) for j in top if overlap[j] > 0
                ]

            reasons = []
            if shared_terms:
                reasons.append("Related to your interests: " + ", ".join(shared_terms))
            if contributions["collaborative"] > 0:
                reasons.append("Users with similar interests interacted with this product")
            if contributions["popularity"] > 0:
                reasons.append("Popular among users")
            if idx not in interacted:
                reasons.append("New discovery from the catalogue")
            elif idx in purchased:
                reasons.append("Rediscovered using your purchase preferences")
            elif idx in clicked:
                reasons.append("Related to a product you clicked")
            elif idx in viewed:
                reasons.append("Related to a product you viewed")
            if not reasons:
                reasons.append("Recommended for discovery")

            results.append({
                **product,
                "score": float(score),
                "_rank_score": float(rank_score),
                "explanation": {
                    "components": components,
                    "weights": weights,
                    "contributions": contributions,
                    "reasons": reasons,
                    "shared_terms": shared_terms,
                },
                "model_version": self.MODEL_VERSION,
            })

        # Stable ranking for a given profile; manual refresh rotates the
        # top-five slate so the button visibly offers another ordering.
        def priority(item):
            idx = self.index[item["id"]]
            if idx not in interacted:
                return 0
            if idx in (viewed | clicked):
                return 1
            return 2

        results.sort(
            key=lambda item: (priority(item), -item["_rank_score"], item["id"])
        )
        top = results[:limit]
        if refresh_seed and len(top) > 1:
            shift = (int(refresh_seed) - 1) % len(top)
            top = top[shift:] + top[:shift]

        for item in top:
            item.pop("_rank_score", None)
        return top
