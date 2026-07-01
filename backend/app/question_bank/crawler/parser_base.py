import re
from abc import ABC, abstractmethod
from html.parser import HTMLParser


BLOCK_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "th", "td"}
PART_PATTERN = re.compile(r"\bpart\s*([123])\b", re.IGNORECASE)
EXCLUDED_SECTION_MARKERS = ("sample answer", "model answer", "suggested answer", "vocabulary", "transcript")


class _BlockExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.frames: list[tuple[str, list[str]]] = []
        self.blocks: list[tuple[str, str]] = []
        self.ignored_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript", "nav", "footer"}:
            self.ignored_depth += 1
        if not self.ignored_depth and tag in BLOCK_TAGS:
            self.frames.append((tag, []))

    def handle_data(self, data: str) -> None:
        if self.ignored_depth:
            return
        for _, chunks in self.frames:
            chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "nav", "footer"} and self.ignored_depth:
            self.ignored_depth -= 1
            return
        for index in range(len(self.frames) - 1, -1, -1):
            frame_tag, chunks = self.frames[index]
            if frame_tag == tag:
                text = " ".join("".join(chunks).split())
                if text:
                    self.blocks.append((tag, text))
                self.frames.pop(index)
                return


class BaseQuestionParser(ABC):
    @abstractmethod
    def parse(self, html: str, source_config: dict) -> list[dict]:
        """Extract question-shaped records without cleaning or persistence."""

    @staticmethod
    def extract_blocks(html: str) -> list[tuple[str, str]]:
        extractor = _BlockExtractor()
        extractor.feed(html)
        return extractor.blocks


class StaticQuestionParser(BaseQuestionParser):
    """Conservative parser for server-rendered pages with headings and lists."""

    def parse(self, html: str, source_config: dict) -> list[dict]:
        blocks = self.extract_blocks(html)
        records: list[dict] = []
        current_part: str | None = None
        excluded_section = False
        index = 0
        while index < len(blocks):
            tag, text = blocks[index]
            part_match = PART_PATTERN.search(text) if tag.startswith("h") else None
            if part_match:
                current_part = f"part{part_match.group(1)}"
                excluded_section = False
                index += 1
                continue
            if tag.startswith("h") and any(marker in text.lower() for marker in EXCLUDED_SECTION_MARKERS):
                excluded_section = True
                index += 1
                continue
            if excluded_section or current_part is None:
                index += 1
                continue
            lowered = text.lower().strip()
            if current_part == "part2" and lowered.startswith("describe "):
                bullets: list[str] = []
                cursor = index + 1
                while cursor < len(blocks) and blocks[cursor][0] == "li":
                    bullets.append(blocks[cursor][1])
                    cursor += 1
                records.append(self._record(source_config, current_part, text, text, bullets or None))
                index = cursor
                continue
            if text.endswith("?") and not any(marker in lowered for marker in EXCLUDED_SECTION_MARKERS):
                records.append(self._record(source_config, current_part, text))
            index += 1
        return records

    @staticmethod
    def _record(
        source_config: dict,
        part: str,
        question: str,
        cue_card_title: str | None = None,
        cue_card_bullets: list[str] | None = None,
    ) -> dict:
        return {
            "part": part,
            "question": question,
            "cue_card_title": cue_card_title,
            "cue_card_bullets": cue_card_bullets,
            "topic": None,
            "sub_topic": None,
            "difficulty": None,
            "source_name": source_config["name"],
            "source_url": source_config["source_url"],
            "source_type": source_config["source_type"],
            "source_format": source_config.get("source_format", "webpage"),
            "confidence": source_config["confidence"],
            "season": source_config.get("season"),
            "raw_text": "\n".join([question, *(cue_card_bullets or [])]),
            "status": "pending_review",
        }
