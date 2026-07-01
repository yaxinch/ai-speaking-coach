TOPIC_KEYWORDS = {
    "technology": ("technology", "internet", "phone", "computer", " ai ", "online"),
    "environment": ("environment", "pollution", "climate", "recycling", "nature"),
    "work": ("work", "job", "career", "company"),
    "study": ("study", "school", "university", "teacher", "subject"),
    "hometown": ("hometown", "city", "neighborhood", "neighbourhood"),
    "travel": ("travel", "trip", "holiday", "tourism"),
    "family": ("family", "parents", "children"),
    "friends": ("friend", "friendship"),
    "health": ("health", "exercise", "sport"),
    "culture": ("culture", "tradition", "festival"),
}


def classify_topic(question: dict | str) -> str | None:
    if isinstance(question, dict):
        text = " ".join(
            str(value or "")
            for value in (question.get("question"), question.get("cue_card_title"), question.get("cue_card_bullets"))
        )
    else:
        text = question
    haystack = f" {text.lower()} "
    scores = {topic: sum(keyword in haystack for keyword in keywords) for topic, keywords in TOPIC_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else None


class TopicClassifier:
    """Extension point for future rule or LLM-backed classifiers."""

    def classify(self, question: dict) -> str | None:
        return classify_topic(question)
