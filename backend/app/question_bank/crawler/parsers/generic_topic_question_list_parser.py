from app.question_bank.crawler.parsers.generic_question_list_parser import GenericQuestionListParser


class GenericTopicQuestionListParser(GenericQuestionListParser):
    """Question-list parser that also retains headings as candidate topics."""
