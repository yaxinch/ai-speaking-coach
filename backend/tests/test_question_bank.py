import csv
import json
import tempfile
import unittest
from pathlib import Path

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.question_bank.crawler.cleaner import clean_question, clean_text
from app.question_bank.crawler.deduper import dedupe_questions, generate_content_hash, normalize_question_text
from app.question_bank.crawler.difficulty_classifier import classify_difficulty
from app.question_bank.crawler.fetcher import CompliantFetcher, FetchSkipped
from app.question_bank.crawler.parsers import create_parser
from app.question_bank.crawler.topic_classifier import classify_topic
from app.question_bank.models import SpeakingQuestion
from app.question_bank.repository import QuestionRepository
from app.question_bank.scripts.import_questions import load_import_records
from app.question_bank.service import build_embedding_text, prepare_questions


def raw_question(**overrides) -> dict:
    data = {
        "part": "part1",
        "question": "Do you use the internet every day?",
        "cue_card_title": None,
        "cue_card_bullets": None,
        "topic": None,
        "sub_topic": None,
        "difficulty": None,
        "source_name": "Example Education Site",
        "source_url": "https://example.com/questions",
        "source_type": "education_site",
        "confidence": "medium_high",
        "season": None,
        "raw_text": "Do you use the internet every day?",
    }
    data.update(overrides)
    return data


class CleanerAndClassifierTests(unittest.TestCase):
    def test_cleans_entities_whitespace_and_punctuation(self):
        self.assertEqual(clean_text("  What&nbsp;is your hometown’s name?\n"), "What is your hometown's name?")

    def test_rejects_answer_content_and_structures_part2_bullets(self):
        self.assertIsNone(clean_question(raw_question(question="Sample answer: I use it daily.")))
        cleaned = clean_question(
            raw_question(
                part="Part 2",
                question="Describe a useful website",
                cue_card_bullets='["what it is", "how you use it"]',
            )
        )
        self.assertEqual(cleaned["part"], "part2")
        self.assertEqual(cleaned["cue_card_bullets"], ["what it is", "how you use it"])

    def test_dedupes_by_normalized_hash_and_prefers_confidence(self):
        self.assertEqual(normalize_question_text("  Do you work, or STUDY? "), "do you work or study")
        low = raw_question(question="Do you work or study?", confidence="low")
        high = raw_question(question="Do you work, or study?", confidence="high", source_name="Official")
        result = dedupe_questions([low, high])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source_name"], "Official")
        self.assertEqual(result[0]["content_hash"], generate_content_hash(high["question"]))

    def test_rule_classifiers_and_embedding_text(self):
        technology = raw_question(question="How has technology changed society?", part="part3")
        self.assertEqual(classify_topic(technology), "technology")
        self.assertEqual(classify_difficulty(technology), "hard")
        self.assertEqual(classify_difficulty(raw_question()), "easy")
        prepared = prepare_questions([technology])[0]
        self.assertIn("Topic: technology", build_embedding_text(prepared))


class ParserTests(unittest.TestCase):
    HTML = """
    <html><body>
      <h2>Speaking Part 1</h2><p>Do you work or study?</p>
      <h2>Part 2</h2><p>Describe a useful website</p>
      <ul><li>what it is</li><li>how you use it</li></ul>
      <h2>Sample Answer</h2><p>I use a news website.</p>
      <h2>Part 3</h2><p>How has the internet changed communication?</p>
    </body></html>
    """

    def test_all_static_parsers_return_uniform_questions(self):
        config = {
            "name": "Test",
            "source_url": "https://example.com/page",
            "source_type": "education_site",
            "confidence": "medium_high",
        }
        for parser_name in ("generic_static", "british_council", "ielts_liz"):
            with self.subTest(parser=parser_name):
                records = create_parser(parser_name).parse(self.HTML, config)
                self.assertEqual([record["part"] for record in records], ["part1", "part2", "part3"])
                self.assertEqual(records[1]["cue_card_bullets"], ["what it is", "how you use it"])
                self.assertTrue(all(record["source_url"] == config["source_url"] for record in records))

    def test_british_council_parser_limits_part1_to_question_region(self):
        html = """
        <h1>IELTS practice Speaking test - part 1</h1>
        <h2>How to practise IELTS Speaking part 1</h2>
        <p>How long is IELTS Speaking part 1?</p>
        <h2>Speaking practice test - part 1 questions</h2>
        <table><tr><td>What kind of place is it?</td></tr><tr><td>How long have you lived there?</td></tr></table>
        <h2>Listening to the audio</h2><p>Do you think this candidate performed well?</p>
        <h2>Transcript of the audio file</h2><p>Examiner What kind of place is it?</p>
        """
        config = {
            "name": "British Council",
            "source_url": "https://takeielts.britishcouncil.org/example/part-1",
            "source_type": "official_sample",
            "confidence": "high",
        }
        records = create_parser("british_council_speaking").parse(html, config)
        self.assertEqual([record["question"] for record in records], ["What kind of place is it?", "How long have you lived there?"])
        self.assertTrue(all(record["status"] == "pending_review" for record in records))

    def test_british_council_parser_structures_part2_task_card(self):
        html = """
        <h1>IELTS practice Speaking test - part 2</h1>
        <h2>Speaking test part 2: candidate task card</h2>
        <p>Describe something you own which is important to you.</p>
        <ul><li>where you got it from</li><li>why it is important</li></ul>
        <h2>Rounding off questions</h2><ul><li>Would it be easy to replace?</li></ul>
        <h2>Listening to the audio</h2><p>Do not collect this?</p>
        """
        config = {
            "name": "British Council",
            "source_url": "https://takeielts.britishcouncil.org/example/part-2",
            "source_type": "official_sample",
            "confidence": "high",
        }
        records = create_parser("british_council_speaking").parse(html, config)
        self.assertEqual(records[0]["cue_card_bullets"], ["where you got it from", "why it is important"])
        self.assertEqual(records[1]["question"], "Would it be easy to replace?")

    def test_idp_parser_ignores_navigation_and_keeps_explicit_part_example(self):
        html = """
        <nav><p>Need help?</p><p>Who accepts IELTS?</p></nav>
        <h2>Part 1: Introduction and questions</h2><p>Why or why not?</p>
        <h2>Part 3: Two-way discussion</h2>
        <p>The first question might be, “Do you think it is important to maintain beautiful places in cities?”</p>
        <h2>Sample task</h2><p>Prompt</p><p>Transcript</p>
        """
        config = {
            "name": "IDP IELTS",
            "source_url": "https://ielts.idp.com/prepare/example",
            "source_type": "official_sample",
            "confidence": "high",
        }
        records = create_parser("idp_speaking").parse(html, config)
        self.assertEqual(
            [record["question"] for record in records],
            ["Do you think it is important to maintain beautiful places in cities?"],
        )
        self.assertEqual(records[0]["part"], "part3")

    def test_generic_question_list_tracks_paragraph_topics_and_cue_cards(self):
        html = """
        <h2>Part 1 IELTS Speaking Questions</h2>
        <p>Accommodation</p><ul><li>Do you live in a house or a flat?</li></ul>
        <h2>Part 2 IELTS Speaking Questions</h2>
        <p>Important possessions</p>
        <p>Describe something important to you</p><ul><li>where you got it</li><li>why it matters</li></ul>
        <h2>Sample Answer</h2><p>Do not collect this answer?</p>
        """
        config = {
            "name": "Question Site",
            "source_url": "https://example.com/questions",
            "source_type": "education_site",
            "source_format": "webpage",
            "confidence": "medium",
        }
        records = create_parser("generic_question_list").parse(html, config)
        self.assertEqual(records[0]["topic"], "accommodation")
        self.assertEqual(records[1]["cue_card_bullets"], ["where you got it", "why it matters"])
        self.assertTrue(all(record["source_format"] == "webpage" for record in records))

    def test_examword_parser_stops_before_answer_metadata_and_structures_parts(self):
        html = """
        <div id="side2CoreFilerRef1"><div><span>2026-06-25</span>: <span>Part 1</span></div>
          <div style="font-size:110%;"><ol><li>Where are you living now?</li></ol>
            <div style="color:lightgray;font-size:80%;"><a>Sample Answers</a><li>Do not collect?</li></div>
          </div>
        </div>
        <div id="side2CoreFilerRef2"><div><span>Part 2</span></div>
          <div style="font-size:110%;">Describe a useful website.<br><br>You should say:
            <ul><li>what it is</li><li>why it is useful</li></ul>
            <div style="color:lightgray;font-size:80%;">Vocab and Sample Answers</div>
          </div>
        </div>
        <div id="side2CoreFilerRef3"><div><span>Part 3</span></div>
          <div style="font-size:110%;"><ol><li>How has the internet changed communication?</li></ol></div>
        </div>
        """
        config = {
            "name": "Examword IELTS Speaking Questions",
            "source_url": "https://www.examword.com/ielts-practice/speaking-exam-question",
            "source_type": "recent_recalled",
            "source_format": "webpage",
            "confidence": "medium",
        }
        records = create_parser("examword").parse(html, config)
        self.assertEqual([record["part"] for record in records], ["part1", "part2", "part3"])
        self.assertEqual(records[1]["cue_card_bullets"], ["what it is", "why it is useful"])
        self.assertNotIn("Do not collect?", [record["question"] for record in records])
        self.assertTrue(all(record["status"] == "pending_review" for record in records))


class FetcherTests(unittest.TestCase):
    def test_dry_run_makes_no_network_requests(self):
        calls = []

        def handler(request):
            calls.append(request.url)
            return httpx.Response(500)

        with tempfile.TemporaryDirectory() as directory, httpx.Client(transport=httpx.MockTransport(handler)) as client:
            fetcher = CompliantFetcher(directory, client=client, sleep_fn=lambda _: None)
            self.assertIsNone(fetcher.fetch("https://example.com/page", dry_run=True))
        self.assertEqual(calls, [])

    def test_obeys_robots_and_uses_html_cache(self):
        calls = []

        def handler(request):
            calls.append(str(request.url))
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text="User-agent: *\nDisallow: /private\nAllow: /")
            return httpx.Response(
                200,
                text="<h2>Part 1</h2><p>Do you work?</p>",
                headers={"content-type": "text/html; charset=utf-8"},
            )

        with tempfile.TemporaryDirectory() as directory, httpx.Client(transport=httpx.MockTransport(handler)) as client:
            fetcher = CompliantFetcher(directory, client=client, sleep_fn=lambda _: None)
            first = fetcher.fetch("https://example.com/page")
            second = fetcher.fetch("https://example.com/page")
            self.assertFalse(first.from_cache)
            self.assertTrue(second.from_cache)
            with self.assertRaises(FetchSkipped):
                fetcher.fetch("https://example.com/private/item")
        self.assertEqual(sum(url.endswith("/page") for url in calls), 1)

    def test_retries_only_to_configured_limit(self):
        calls = []

        def handler(request):
            calls.append(str(request.url))
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text="User-agent: *\nAllow: /")
            return httpx.Response(503, text="busy")

        with tempfile.TemporaryDirectory() as directory, httpx.Client(transport=httpx.MockTransport(handler)) as client:
            fetcher = CompliantFetcher(directory, client=client, max_retries=2, sleep_fn=lambda _: None)
            with self.assertRaises(httpx.HTTPStatusError):
                fetcher.fetch("https://example.com/page")
        self.assertEqual(sum(url.endswith("/page") for url in calls), 3)

    def test_retries_transient_transport_error(self):
        page_attempts = 0

        def handler(request):
            nonlocal page_attempts
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text="User-agent: *\nAllow: /")
            page_attempts += 1
            if page_attempts == 1:
                raise httpx.ConnectError("temporary", request=request)
            return httpx.Response(200, text="<p>ok</p>", headers={"content-type": "text/html"})

        with tempfile.TemporaryDirectory() as directory, httpx.Client(transport=httpx.MockTransport(handler)) as client:
            fetcher = CompliantFetcher(directory, client=client, max_retries=1, sleep_fn=lambda _: None)
            self.assertEqual(fetcher.fetch("https://example.com/page").html, "<p>ok</p>")
        self.assertEqual(page_attempts, 2)

    def test_caches_robots_validation_failure_per_origin(self):
        calls = []

        def handler(request):
            calls.append(str(request.url))
            raise httpx.ReadTimeout("timeout", request=request)

        with tempfile.TemporaryDirectory() as directory, httpx.Client(transport=httpx.MockTransport(handler)) as client:
            fetcher = CompliantFetcher(directory, client=client, max_retries=0, sleep_fn=lambda _: None)
            for path in ("one", "two"):
                with self.assertRaisesRegex(FetchSkipped, "ReadTimeout"):
                    fetcher.fetch(f"https://example.com/{path}")
        self.assertEqual(calls, ["https://example.com/robots.txt"])


class RepositoryAndImportTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine, tables=[SpeakingQuestion.__table__])
        self.session = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_inserts_dedupes_updates_and_filters(self):
        question = prepare_questions([raw_question()])[0]
        repository = QuestionRepository(self.session)
        created, duplicates = repository.bulk_insert([question, question])
        self.assertEqual((len(created), duplicates), (1, 1))
        self.assertEqual(len(repository.pending_review()), 1)
        repository.update_status(created[0].id, "approved")
        self.assertEqual(len(repository.query(status="approved", topic="technology", part="part1")), 1)

    def test_csv_import_selects_only_approved_and_json_defaults_pending(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "review.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["question", "status"])
                writer.writeheader()
                writer.writerows(
                    [
                        {"question": "Approved?", "status": "approved"},
                        {"question": "Pending?", "status": "pending_review"},
                    ]
                )
            self.assertEqual([row["question"] for row in load_import_records(csv_path)], ["Approved?"])
            json_path = Path(directory) / "seed.json"
            json_path.write_text(json.dumps([raw_question()]), encoding="utf-8")
            self.assertEqual(load_import_records(json_path)[0]["status"], "pending_review")


if __name__ == "__main__":
    unittest.main()
