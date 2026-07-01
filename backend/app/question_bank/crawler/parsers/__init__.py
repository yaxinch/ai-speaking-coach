from app.question_bank.crawler.parsers.british_council_parser import BritishCouncilParser
from app.question_bank.crawler.parsers.british_council_speaking_parser import BritishCouncilSpeakingParser
from app.question_bank.crawler.parsers.examword_parser import ExamwordParser
from app.question_bank.crawler.parsers.generic_static_parser import GenericStaticParser
from app.question_bank.crawler.parsers.generic_question_list_parser import GenericQuestionListParser
from app.question_bank.crawler.parsers.generic_topic_question_list_parser import GenericTopicQuestionListParser
from app.question_bank.crawler.parsers.idp_speaking_parser import IdpSpeakingParser
from app.question_bank.crawler.parsers.ielts_liz_parser import IeltsLizParser
from app.question_bank.crawler.parsers.ielts_org_sample_parser import IeltsOrgSampleParser


PARSER_REGISTRY = {
    "british_council": BritishCouncilParser,
    "british_council_speaking": BritishCouncilSpeakingParser,
    "examword": ExamwordParser,
    "ielts_liz": IeltsLizParser,
    "ielts_org_sample": IeltsOrgSampleParser,
    "idp_speaking": IdpSpeakingParser,
    "generic_static": GenericStaticParser,
    "generic_question_list": GenericQuestionListParser,
    "generic_topic_question_list": GenericTopicQuestionListParser,
}


def create_parser(name: str):
    try:
        return PARSER_REGISTRY[name]()
    except KeyError as exc:
        raise ValueError(f"Unknown parser: {name}") from exc
