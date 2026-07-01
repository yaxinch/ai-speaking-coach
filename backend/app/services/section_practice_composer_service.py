import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.llm.base import LLMProvider
from app.llm.json_parser import parse_json_object
from app.prompts.section_practice_prompt import build_section_practice_selector_prompt
from app.question_bank.embedding_service import EmbeddingService, EmbeddingUnavailable
from app.question_bank.models import SpeakingQuestion
from app.question_bank.service import QuestionBankService
from app.question_bank.vector_search import ScoredQuestion, VectorSearchService
from app.schemas.agent import PartType
from app.schemas.practice import (
    SectionCueCard,
    SectionPracticeItem,
    SectionPracticeMetadata,
    StartSectionPracticeResponse,
)


class SectionPracticeUnavailable(RuntimeError):
    pass


class SectionPracticeComposerService:
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

    async def start(self, part: PartType, practice_goal: str | None) -> StartSectionPracticeResponse:
        goal = (practice_goal or "").strip()
        if not goal:
            return self._default(part, practice_goal=None)

        try:
            query_vector = await asyncio.to_thread(self.embedding.embed_query, goal)
            top_k = 10 if part == "part2" else 20
            candidates = VectorSearchService(
                self.db,
                model=self.embedding.model,
                dimensions=self.embedding.dimensions,
            ).search(query_vector, part=part, top_k=top_k)
            candidates = self._valid_candidates(part, candidates)
            if not candidates:
                raise EmbeddingUnavailable(f"No indexed {part} questions are available.")
        except EmbeddingUnavailable as exc:
            return self._default(part, practice_goal=goal, fallback_reason=str(exc))
        except Exception as exc:
            return self._default(
                part,
                practice_goal=goal,
                fallback_reason=f"Retrieval fallback ({type(exc).__name__}).",
            )

        try:
            selected = await self._select_with_llm(part, goal, candidates)
            fallback_used = False
            fallback_reason = None
        except Exception as exc:
            selected = candidates[0].question
            fallback_used = True
            fallback_reason = f"LLM selector fallback ({type(exc).__name__})."

        return self._response(
            selected,
            part=part,
            practice_goal=goal,
            mode="goal_based",
            retrieval_used=True,
            candidate_count=len(candidates),
            selector_used=True,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
        )

    def _default(
        self,
        part: PartType,
        *,
        practice_goal: str | None,
        fallback_reason: str | None = None,
    ) -> StartSectionPracticeResponse:
        rows = self.bank.questions(part=part)
        if part == "part2":
            rows = [row for row in rows if self.bank.cue_card_bullets(row)]
        if not rows:
            raise SectionPracticeUnavailable(f"No approved {part} practice questions are available.")
        selected = self.bank.random_questions(rows, 1)[0]
        return self._response(
            selected,
            part=part,
            practice_goal=practice_goal,
            mode="goal_based" if practice_goal else "default",
            retrieval_used=False,
            candidate_count=0,
            selector_used=False,
            fallback_used=fallback_reason is not None,
            fallback_reason=fallback_reason,
        )

    def _valid_candidates(self, part: PartType, rows: list[ScoredQuestion]) -> list[ScoredQuestion]:
        return [
            item
            for item in rows
            if item.question.part == part and (part != "part2" or bool(self.bank.cue_card_bullets(item.question)))
        ]

    async def _select_with_llm(
        self,
        part: PartType,
        goal: str,
        candidates: list[ScoredQuestion],
    ) -> SpeakingQuestion:
        payload = []
        for item in candidates:
            row = item.question
            candidate = {
                "id": row.id,
                "part": row.part,
                "topic": self.bank.topic(row),
                "difficulty": self.bank.difficulty(row),
                "text": row.question,
            }
            if part == "part2":
                candidate["bulletPoints"] = self.bank.cue_card_bullets(row)
            payload.append(candidate)
        raw = await self.llm.chat(build_section_practice_selector_prompt(part, goal, payload), temperature=0.1)
        value = parse_json_object(raw)
        selected_id = value.get("selectedId")
        by_id = {item.question.id: item.question for item in candidates}
        selected = by_id.get(selected_id)
        if selected is None or selected.part != part:
            raise ValueError("LLM selected an unknown or cross-part question ID.")
        if part == "part2" and not self.bank.cue_card_bullets(selected):
            raise ValueError("LLM selected an incomplete cue card.")
        return selected

    def _response(
        self,
        row: SpeakingQuestion,
        *,
        part: PartType,
        practice_goal: str | None,
        mode: str,
        retrieval_used: bool,
        candidate_count: int,
        selector_used: bool,
        fallback_used: bool,
        fallback_reason: str | None,
    ) -> StartSectionPracticeResponse:
        topic = self.bank.topic(row)
        difficulty = self.bank.difficulty(row)
        cue_card = None
        text = row.question
        item_type = f"{part}_question"
        if part == "part2":
            text = row.cue_card_title or row.question
            item_type = "part2_cue_card"
            cue_card = SectionCueCard(
                id=row.id,
                topic=topic,
                prompt=text,
                bulletPoints=self.bank.cue_card_bullets(row),
                source=row.source_name,
                difficulty=difficulty,
            )
        return StartSectionPracticeResponse(
            selectionId=str(uuid4()),
            mode=mode,
            practiceGoal=practice_goal,
            part=part,
            item=SectionPracticeItem(
                type=item_type,
                id=row.id,
                topic=topic,
                text=text,
                source=row.source_name,
                difficulty=difficulty,
                cueCard=cue_card,
            ),
            metadata=SectionPracticeMetadata(
                retrievalUsed=retrieval_used,
                candidateCount=candidate_count,
                selectorUsed=selector_used,
                fallbackUsed=fallback_used,
                fallbackReason=fallback_reason,
                createdAt=datetime.now(timezone.utc),
            ),
        )
