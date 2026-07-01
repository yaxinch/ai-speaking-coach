import logging
import re

from app.question_bank.crawler.parser_base import BaseQuestionParser, StaticQuestionParser


logger = logging.getLogger(__name__)
PART_RE = re.compile(r"\bpart\s*([123])\b", re.IGNORECASE)
EXCLUDED = (
    "sample answer",
    "model answer",
    "suggested answer",
    "vocabulary",
    "tips",
    "course",
    "newsletter",
    "sign up",
    "signup",
    "log in",
    "login",
    "advertisement",
    "comments",
    "author",
    "about the author",
)
GENERIC_HEADINGS = {"questions", "sample questions", "practice questions", "speaking questions", "sample task"}


def _question_sentences(text: str) -> list[str]:
    questions = []
    for candidate in re.findall(r"[^?]{3,500}\?", text):
        candidate = re.sub(r"^\s*(?:\d+[.)]|[-•▪])\s*", "", candidate).strip()
        lowered = candidate.lower()
        if any(marker in lowered for marker in EXCLUDED):
            continue
        if lowered.startswith(("here are", "the following", "practice your", "read more")):
            continue
        questions.append(candidate)
    return questions


def _topic_from_heading(text: str) -> str | None:
    cleaned = re.sub(r"\b(?:ielts|speaking|topic|questions?)\b", " ", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" :-–—")
    if not cleaned or text.lower().strip() in GENERIC_HEADINGS or len(cleaned) > 80:
        return None
    return cleaned.lower()


class GenericQuestionListParser(BaseQuestionParser):
    """Conservative parser for question lists grouped under explicit Part headings."""

    def parse(self, html: str, source_config: dict) -> list[dict]:
        blocks = self.extract_blocks(html)
        current_part: str | None = None
        topic: str | None = None
        excluded_section = False
        records: list[dict] = []
        seen: set[tuple[str, str]] = set()
        index = 0
        while index < len(blocks):
            tag, text = blocks[index]
            lowered = text.lower().strip()
            part_match = PART_RE.search(text) if tag.startswith("h") else None
            if part_match:
                current_part = f"part{part_match.group(1)}"
                topic = None
                excluded_section = False
                index += 1
                continue
            if tag.startswith("h"):
                if any(marker in lowered for marker in EXCLUDED):
                    excluded_section = True
                    index += 1
                    continue
                if current_part:
                    possible_topic = _topic_from_heading(text)
                    if possible_topic:
                        topic = possible_topic
                        excluded_section = False
                index += 1
                continue
            if current_part is None or excluded_section or tag not in {"p", "li", "td"}:
                index += 1
                continue
            if any(marker in lowered for marker in EXCLUDED):
                index += 1
                continue
            if current_part == "part2" and lowered.startswith("describe "):
                bullets: list[str] = []
                cursor = index + 1
                while cursor < len(blocks) and blocks[cursor][0] == "li":
                    bullet = blocks[cursor][1].strip(" -•▪")
                    if bullet and not any(marker in bullet.lower() for marker in EXCLUDED):
                        bullets.append(bullet)
                    cursor += 1
                record = StaticQuestionParser._record(source_config, current_part, text, text, bullets or None)
                record["topic"] = topic
                records.append(record)
                index = cursor
                continue
            if (
                tag == "p"
                and "?" not in text
                and len(text) <= 80
                and index + 1 < len(blocks)
                and blocks[index + 1][0] == "li"
            ):
                possible_topic = _topic_from_heading(text)
                if possible_topic:
                    topic = possible_topic
                index += 1
                continue
            for question in _question_sentences(text):
                key = (current_part, question.lower())
                if key in seen:
                    continue
                seen.add(key)
                record = StaticQuestionParser._record(source_config, current_part, question)
                record["topic"] = topic
                records.append(record)
            index += 1
        if not records:
            logger.warning("No conservative question-list regions found: %s", source_config["source_url"])
        return records
