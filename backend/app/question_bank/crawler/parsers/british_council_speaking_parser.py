import logging
import re

from app.question_bank.crawler.parser_base import BaseQuestionParser, StaticQuestionParser


logger = logging.getLogger(__name__)


def _questions_in(text: str) -> list[str]:
    """Split a table cell conservatively, retaining only explicit questions."""
    return [match.strip() for match in re.findall(r"[^?]{3,}\?", text) if len(match.strip()) <= 500]


class BritishCouncilSpeakingParser(BaseQuestionParser):
    """Parse only the question/task-card regions of reviewed Take IELTS pages."""

    def parse(self, html: str, source_config: dict) -> list[dict]:
        blocks = self.extract_blocks(html)
        source_url = source_config["source_url"]
        part_match = re.search(r"/part-([123])/?$", source_url)
        if not part_match:
            logger.warning("British Council URL is an index or unsupported page; no questions parsed: %s", source_url)
            return []
        part = f"part{part_match.group(1)}"
        if part == "part1":
            return self._parse_question_region(blocks, source_config, part, "part 1 questions", "listening to the audio")
        if part == "part2":
            return self._parse_part2(blocks, source_config)
        return self._parse_question_region(blocks, source_config, part, "how to practise", "listening to the audio")

    def _parse_question_region(
        self,
        blocks: list[tuple[str, str]],
        source_config: dict,
        part: str,
        start_marker: str,
        end_marker: str,
    ) -> list[dict]:
        active = False
        records: list[dict] = []
        seen: set[str] = set()
        for tag, text in blocks:
            lowered = text.lower()
            if tag.startswith("h") and start_marker in lowered:
                active = True
                continue
            if active and tag.startswith("h") and end_marker in lowered:
                break
            if not active or tag not in {"p", "li", "td"}:
                continue
            for question in _questions_in(text):
                normalized = question.lower()
                if normalized in seen:
                    continue
                seen.add(normalized)
                records.append(StaticQuestionParser._record(source_config, part, question))
        if not records:
            logger.warning("No stable British Council question region found: %s", source_config["source_url"])
        return records

    def _parse_part2(self, blocks: list[tuple[str, str]], source_config: dict) -> list[dict]:
        active = False
        task: dict | None = None
        follow_ups: list[dict] = []
        bullets: list[str] = []
        for tag, text in blocks:
            lowered = text.lower()
            if tag.startswith("h") and "candidate task card" in lowered:
                active = True
                continue
            if active and tag.startswith("h") and "listening to the audio" in lowered:
                break
            if not active:
                continue
            if task is None and lowered.startswith("describe "):
                task = StaticQuestionParser._record(source_config, "part2", text, text, None)
                continue
            if tag.startswith("h") and "rounding off questions" in lowered:
                if task is not None:
                    task["cue_card_bullets"] = bullets or None
                    task["raw_text"] = "\n".join([task["question"], *bullets])
                bullets = []
                continue
            if tag == "li":
                questions = _questions_in(text)
                if questions:
                    follow_ups.extend(
                        StaticQuestionParser._record(source_config, "part2", question) for question in questions
                    )
                elif task is not None:
                    bullets.append(text)
        if task is not None and task.get("cue_card_bullets") is None:
            task["cue_card_bullets"] = bullets or None
            task["raw_text"] = "\n".join([task["question"], *bullets])
        records = ([task] if task else []) + follow_ups
        if not records:
            logger.warning("No stable British Council task-card region found: %s", source_config["source_url"])
        return records
