import logging

from app.question_bank.crawler.parser_base import StaticQuestionParser


logger = logging.getLogger(__name__)


class IeltsOrgSampleParser(StaticQuestionParser):
    """Conservative HTML-only parser; IELTS.org PDFs require manual import for now."""

    def parse(self, html: str, source_config: dict) -> list[dict]:
        records = super().parse(html, source_config)
        if not records:
            logger.warning("No explicit Speaking question blocks found; manual review is required: %s", source_config["source_url"])
        return records
