import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.llm.base import LLMProvider
from app.llm.json_parser import parse_json_object
from app.prompts.mock_test_prompt import build_mock_session_composer_prompt
from app.question_bank.embedding_service import EmbeddingService, EmbeddingUnavailable
from app.question_bank.models import SpeakingQuestion
from app.question_bank.service import QuestionBankService
from app.question_bank.vector_search import ScoredQuestion, VectorSearchService
from app.schemas.mock_test import (
    MockSessionMetadata,
    MockSessionParts,
    SessionCueCard,
    SessionPart1,
    SessionPart1Topic,
    SessionPart2,
    SessionPart3,
    SessionQuestion,
    StartMockTestResponse,
)


class MockSessionComposerService:
    def __init__(
        self,
        db: Session,
        llm: LLMProvider,
        *,
        embedding_service: EmbeddingService | None = None,
        question_bank: QuestionBankService | None = None,
    ) -> None:
        self.db = db
        self.llm = llm
        self.embedding = embedding_service or EmbeddingService()
        self.bank = question_bank or QuestionBankService(db)

    async def start(self, practice_goal: str | None) -> StartMockTestResponse:
        goal = (practice_goal or "").strip()
        if not goal:
            return self._default_session(practice_goal=None)
        try:
            query_vector = await asyncio.to_thread(self.embedding.embed_query, goal)
            search = VectorSearchService(self.db, model=self.embedding.model, dimensions=self.embedding.dimensions)
            expanded_part1 = search.search(query_vector, part="part1", top_k=100)
            initial_part1 = expanded_part1[:20]
            initial_groups = self._group_scored_by_topic(initial_part1)
            part1_candidates = (
                initial_part1
                if sum(len(rows) >= 3 for rows in initial_groups.values()) >= 2
                else expanded_part1
            )
            candidates = {
                "part1": part1_candidates,
                "part2": search.search(query_vector, part="part2", top_k=10),
                "part3": search.search(query_vector, part="part3", top_k=20),
            }
            if any(not candidates[part] for part in ("part1", "part2", "part3")):
                raise EmbeddingUnavailable("The persisted embedding index is incomplete. Run generate_embeddings first.")
            candidates = self._ensure_candidate_capacity(candidates)
            selected = await self._select_with_llm(goal, candidates)
            return self._build_response(
                selected,
                practice_goal=goal,
                mode="goal_based",
                retrieval_used=True,
                candidate_count=sum(len(items) for items in candidates.values()),
                composer_used=True,
                fallback_used=False,
                fallback_reason=None,
            )
        except EmbeddingUnavailable as exc:
            return self._default_session(practice_goal=goal, fallback_reason=str(exc))
        except Exception as exc:
            # Invalid/failed LLM output uses retrieval candidates; other unexpected errors
            # degrade to a usable default session instead of breaking the recording flow.
            if "candidates" in locals():
                try:
                    selected = self._rule_select(candidates)
                    return self._build_response(
                        selected,
                        practice_goal=goal,
                        mode="goal_based",
                        retrieval_used=True,
                        candidate_count=sum(len(items) for items in candidates.values()),
                        composer_used=True,
                        fallback_used=True,
                        fallback_reason=f"LLM composer fallback ({type(exc).__name__}).",
                    )
                except Exception:
                    pass
            return self._default_session(practice_goal=goal, fallback_reason=f"Retrieval fallback ({type(exc).__name__}).")

    def _default_session(self, practice_goal: str | None, fallback_reason: str | None = None) -> StartMockTestResponse:
        topics = self.bank.eligible_part1_topics(3)
        chosen_topics = self.bank.random_questions(topics, 2)
        part1 = [self.bank.random_questions(self.bank.questions(part="part1", topic=topic), 3) for topic in chosen_topics]
        part2 = self.bank.random_part2()
        related = self.bank.questions(part="part3", topic=part2.topic) if part2.topic else []
        chosen_part3 = self.bank.random_questions(related, 4) if len(related) >= 4 else list(related)
        if len(chosen_part3) < 4:
            existing = {row.id for row in chosen_part3}
            pool = [row for row in self.bank.questions(part="part3") if row.id not in existing]
            chosen_part3.extend(self.bank.random_questions(pool, 4 - len(chosen_part3)))
        return self._build_response(
            {"part1": part1, "part2": part2, "part3": chosen_part3},
            practice_goal=practice_goal,
            mode="goal_based" if practice_goal else "default",
            retrieval_used=False,
            candidate_count=0,
            composer_used=False,
            fallback_used=fallback_reason is not None,
            fallback_reason=fallback_reason,
        )

    def _ensure_candidate_capacity(self, candidates: dict[str, list[ScoredQuestion]]) -> dict[str, list[ScoredQuestion]]:
        result = {part: list(items) for part, items in candidates.items()}
        part1_groups = self._group_scored_by_topic(result["part1"])
        eligible = [topic for topic, rows in part1_groups.items() if len(rows) >= 3]
        if len(eligible) < 2:
            seen = {item.question.id for item in result["part1"]}
            full_groups: dict[str, list[SpeakingQuestion]] = defaultdict(list)
            for row in self.bank.questions(part="part1"):
                full_groups[self.bank.topic(row)].append(row)
            preferred_topics = list(part1_groups)
            preferred_topics.extend(topic for topic in sorted(full_groups) if topic not in part1_groups)
            for topic in preferred_topics:
                existing_count = len(part1_groups.get(topic, []))
                if len(full_groups.get(topic, [])) < 3:
                    continue
                for row in full_groups[topic]:
                    if row.id not in seen and existing_count < 3:
                        result["part1"].append(ScoredQuestion(row, -1.0))
                        seen.add(row.id)
                        existing_count += 1
                part1_groups = self._group_scored_by_topic(result["part1"])
                eligible = [name for name, rows in part1_groups.items() if len(rows) >= 3]
                if len(eligible) >= 2:
                    break
        if not any(self.bank.cue_card_bullets(item.question) for item in result["part2"]):
            seen = {item.question.id for item in result["part2"]}
            replacement = next(
                (
                    row
                    for row in self.bank.questions(part="part2")
                    if row.id not in seen and self.bank.cue_card_bullets(row)
                ),
                None,
            )
            if replacement is not None:
                result["part2"].append(ScoredQuestion(replacement, -1.0))
        if len(result["part3"]) < 4:
            seen = {item.question.id for item in result["part3"]}
            for row in self.bank.questions(part="part3"):
                if row.id not in seen:
                    result["part3"].append(ScoredQuestion(row, -1.0))
                    seen.add(row.id)
                    if len(result["part3"]) >= 4:
                        break
        return result

    async def _select_with_llm(self, goal: str, candidates: dict[str, list[ScoredQuestion]]) -> dict:
        payloads = {
            part: [
                {
                    "id": item.question.id,
                    "topic": self.bank.topic(item.question),
                    "difficulty": self.bank.difficulty(item.question),
                    "text": item.question.question,
                    **(
                        {"bulletPoints": self.bank.cue_card_bullets(item.question)}
                        if part == "part2"
                        else {}
                    ),
                }
                for item in items
            ]
            for part, items in candidates.items()
        }
        raw = await self.llm.chat(
            build_mock_session_composer_prompt(goal, payloads["part1"], payloads["part2"], payloads["part3"]),
            temperature=0.1,
        )
        value = parse_json_object(raw)
        by_part = {part: {item.question.id: item.question for item in items} for part, items in candidates.items()}
        topics = value.get("part1", {}).get("topics", [])
        if not isinstance(topics, list) or len(topics) != 2:
            raise ValueError("Composer must choose two Part 1 topics.")
        selected_part1: list[list[SpeakingQuestion]] = []
        used: set[str] = set()
        for group in topics:
            ids = group.get("questionIds", []) if isinstance(group, dict) else []
            if len(ids) != 3 or len(set(ids)) != 3:
                raise ValueError("Each Part 1 topic must contain three unique IDs.")
            rows = [by_part["part1"].get(item_id) for item_id in ids]
            if any(row is None for row in rows):
                raise ValueError("Part 1 selection contains an unknown ID.")
            resolved = [row for row in rows if row is not None]
            if len({self.bank.topic(row) for row in resolved}) != 1 or used.intersection(ids):
                raise ValueError("Part 1 IDs do not form two unique topic groups.")
            used.update(ids)
            selected_part1.append(resolved)
        cue_id = value.get("part2", {}).get("cueCardId")
        part2 = by_part["part2"].get(cue_id)
        if part2 is None or not self.bank.cue_card_bullets(part2):
            raise ValueError("Composer selected an invalid cue card ID.")
        part3_ids = value.get("part3", {}).get("questionIds", [])
        if len(part3_ids) != 4 or len(set(part3_ids)) != 4:
            raise ValueError("Composer must choose four unique Part 3 IDs.")
        part3 = [by_part["part3"].get(item_id) for item_id in part3_ids]
        if any(row is None for row in part3):
            raise ValueError("Part 3 selection contains an unknown ID.")
        return {"part1": selected_part1, "part2": part2, "part3": [row for row in part3 if row is not None]}

    def _rule_select(self, candidates: dict[str, list[ScoredQuestion]]) -> dict:
        groups = self._group_scored_by_topic(candidates["part1"])
        eligible = [(topic, rows) for topic, rows in groups.items() if len(rows) >= 3]
        if len(eligible) < 2:
            raise ValueError("Not enough Part 1 candidate topics.")
        part1 = [[item.question for item in rows[:3]] for _, rows in eligible[:2]]
        valid_part2 = [item.question for item in candidates["part2"] if self.bank.cue_card_bullets(item.question)]
        if not valid_part2:
            raise ValueError("No valid cue card candidate is available.")
        part2 = valid_part2[0]
        ranked_part3 = [item.question for item in candidates["part3"]]
        related = [row for row in ranked_part3 if row.topic and row.topic == part2.topic]
        rest = [row for row in ranked_part3 if row.id not in {item.id for item in related}]
        part3 = (related + rest)[:4]
        if len(part3) < 4:
            raise ValueError("Not enough Part 3 candidates.")
        return {"part1": part1, "part2": part2, "part3": part3}

    def _group_scored_by_topic(self, rows: list[ScoredQuestion]) -> dict[str, list[ScoredQuestion]]:
        groups: dict[str, list[ScoredQuestion]] = defaultdict(list)
        for item in rows:
            groups[self.bank.topic(item.question)].append(item)
        return dict(groups)

    def _session_question(self, row: SpeakingQuestion) -> SessionQuestion:
        return SessionQuestion(
            id=row.id,
            text=row.question,
            topic=self.bank.topic(row),
            source=row.source_name,
            difficulty=self.bank.difficulty(row),
        )

    def _build_response(
        self,
        selected: dict,
        *,
        practice_goal: str | None,
        mode: str,
        retrieval_used: bool,
        candidate_count: int,
        composer_used: bool,
        fallback_used: bool,
        fallback_reason: str | None,
    ) -> StartMockTestResponse:
        part2: SpeakingQuestion = selected["part2"]
        parts = MockSessionParts(
            part1=SessionPart1(
                topics=[
                    SessionPart1Topic(topic=self.bank.topic(rows[0]), questions=[self._session_question(row) for row in rows])
                    for rows in selected["part1"]
                ]
            ),
            part2=SessionPart2(
                cueCard=SessionCueCard(
                    id=part2.id,
                    topic=self.bank.topic(part2),
                    prompt=part2.cue_card_title or part2.question,
                    bulletPoints=self.bank.cue_card_bullets(part2),
                    source=part2.source_name,
                    difficulty=self.bank.difficulty(part2),
                )
            ),
            part3=SessionPart3(questions=[self._session_question(row) for row in selected["part3"]]),
        )
        return StartMockTestResponse(
            sessionId=str(uuid4()),
            practiceGoal=practice_goal,
            mode=mode,
            parts=parts,
            metadata=MockSessionMetadata(
                retrievalUsed=retrieval_used,
                candidateCount=candidate_count,
                composerUsed=composer_used,
                fallbackUsed=fallback_used,
                fallbackReason=fallback_reason,
                createdAt=datetime.now(timezone.utc),
            ),
        )
