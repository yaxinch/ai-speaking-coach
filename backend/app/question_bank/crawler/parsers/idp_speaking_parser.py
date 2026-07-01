import logging
import re

from app.question_bank.crawler.parser_base import BaseQuestionParser, StaticQuestionParser


logger = logging.getLogger(__name__)


class IdpSpeakingParser(BaseQuestionParser):
    """Extract only explicit questions inside the IDP article's Part sections."""

    def parse(self, html: str, source_config: dict) -> list[dict]:
        current_part: str | None = None
        seen: set[str] = set()
        records: list[dict] = []
        for tag, text in self.extract_blocks(html):
            heading = re.match(r"Part\s*([123])\s*:", text, re.IGNORECASE) if tag.startswith("h") else None
            if heading:
                current_part = f"part{heading.group(1)}"
                continue
            if current_part is None or tag != "p":
                continue
            candidates: list[str] = []
            if current_part == "part2" and text.lower().startswith("describe "):
                candidates.append(text)
            if "question might be" in text.lower():
                candidates.extend(re.findall(r"[“\"]([^”\"]+\?)[”\"]", text))
            for question in candidates:
                normalized = question.strip().lower()
                if normalized in seen:
                    continue
                seen.add(normalized)
                records.append(StaticQuestionParser._record(source_config, current_part, question.strip()))
        if not records:
            logger.warning(
                "No inline IDP speaking questions found; linked Prompt resources require manual review: %s",
                source_config["source_url"],
            )
        return records
