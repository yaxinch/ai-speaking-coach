ABSTRACT_MARKERS = (
    "society",
    "government",
    "future",
    "advantage",
    "disadvantage",
    "compare",
    "influence",
    "change",
)
REASON_MARKERS = ("why", "reason", "explain", "how")


def classify_difficulty(question: dict) -> str:
    part = question.get("part")
    text = str(question.get("question", "")).lower()
    if part == "part3" or any(marker in text for marker in ABSTRACT_MARKERS):
        return "hard"
    if part == "part2" or any(marker in text for marker in REASON_MARKERS):
        return "medium"
    return "easy"


class DifficultyClassifier:
    """Extension point for future rule or LLM-backed classifiers."""

    def classify(self, question: dict) -> str:
        return classify_difficulty(question)
