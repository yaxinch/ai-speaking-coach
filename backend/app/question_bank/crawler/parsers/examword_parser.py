import logging
import re
from html.parser import HTMLParser

from app.question_bank.crawler.parser_base import BaseQuestionParser, StaticQuestionParser


logger = logging.getLogger(__name__)


class _ExamwordGroupExtractor(HTMLParser):
    """Extract only public question text before each group's answer/VIP metadata."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.groups: list[dict] = []
        self.active = False
        self.depth = 0
        self.content_depth: int | None = None
        self.metadata = False
        self.part: str | None = None
        self.content_chunks: list[str] = []
        self.current_li: list[str] | None = None
        self.items: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        attributes = dict(attrs)
        if tag == "div" and not self.active and attributes.get("id", "").startswith("side2CoreFilerRef"):
            self.active = True
            self.depth = 1
            self.content_depth = None
            self.metadata = False
            self.part = None
            self.content_chunks = []
            self.current_li = None
            self.items = []
            return
        if not self.active:
            return
        if tag == "div":
            self.depth += 1
            style = attributes.get("style", "").replace(" ", "").lower()
            if self.content_depth is None and "font-size:110%" in style:
                self.content_depth = self.depth
            elif self.content_depth is not None and ("color:lightgray" in style or "color:lightgrey" in style):
                self.metadata = True
        elif tag == "li" and self.content_depth is not None and not self.metadata:
            self.current_li = []
        elif tag == "br" and self.content_depth is not None and not self.metadata and self.current_li is None:
            self.content_chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.active:
            return
        text = " ".join(data.split())
        if not text:
            return
        part_match = re.fullmatch(r"Part\s*([123])", text, re.IGNORECASE)
        if self.part is None and part_match:
            self.part = f"part{part_match.group(1)}"
        if self.content_depth is None or self.metadata:
            return
        if self.current_li is not None:
            self.current_li.append(text)
        else:
            self.content_chunks.append(text)

    def handle_endtag(self, tag: str) -> None:
        if not self.active:
            return
        if tag == "li" and self.current_li is not None:
            item = " ".join(self.current_li).strip()
            if item:
                self.items.append(item)
            self.current_li = None
            return
        if tag != "div":
            return
        if self.content_depth == self.depth:
            self.content_depth = None
        self.depth -= 1
        if self.depth == 0:
            self._finish_group()

    def _finish_group(self) -> None:
        if self.part:
            content = " ".join(" ".join(self.content_chunks).split())
            self.groups.append({"part": self.part, "content": content, "items": self.items[:]})
        self.active = False


class ExamwordParser(BaseQuestionParser):
    """Parser for Examword's public recent/recalled speaking question groups."""

    def parse(self, html: str, source_config: dict) -> list[dict]:
        extractor = _ExamwordGroupExtractor()
        extractor.feed(html)
        records: list[dict] = []
        for group in extractor.groups:
            part = group["part"]
            if part == "part2":
                title = group["content"].split("You should say:", 1)[0].strip()
                if not title.lower().startswith("describe "):
                    continue
                records.append(
                    StaticQuestionParser._record(source_config, part, title, title, group["items"] or None)
                )
                continue
            for question in group["items"]:
                if question.endswith("?") and len(question) <= 500:
                    records.append(StaticQuestionParser._record(source_config, part, question))
        if not records:
            logger.warning("No public Examword question groups found: %s", source_config["source_url"])
        return records
