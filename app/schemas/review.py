from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel


class ReviewDecision(BaseModel):
    decision: Literal["accepted", "rejected"]


class SubmissionReviewPublic(BaseModel):
    id: int
    item_id: int
    row_index: int
    item_text: Optional[str] = None
    labeler_id: int
    labeler_email: Optional[str] = None
    label_value: dict
    source: str
    status: str
    is_gold: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class ConsensusItem(BaseModel):
    item_id: int
    row_index: int
    item_text: Optional[str] = None
    majority_label: Optional[Any] = None
    votes: dict
    agreement: float
    submission_count: int
    is_gold: bool = False


class ConsensusReport(BaseModel):
    task_id: int
    items: list[ConsensusItem]
    overall_agreement: float
    labeled_count: int
    total_items: int


class GoldSet(BaseModel):
    gold_label: Optional[dict] = None


class LeaderboardEntry(BaseModel):
    labeler_id: int
    labeler_email: Optional[str] = None
    submitted: int
    accepted: int
    rejected: int
    review_accuracy: Optional[float] = None
    gold_answered: int
    gold_correct: int
    gold_accuracy: Optional[float] = None


class TaskStats(BaseModel):
    task_id: int
    title: str
    status: str
    labeled: int
    total: int
    agreement: float
    gold_items: int = 0


class AnalyticsOverview(BaseModel):
    datasets: int
    tasks: int
    items: int
    labeled: int
    submissions: int
    overall_agreement: float
    gold_coverage: float = 0.0
    gold_accuracy: Optional[float] = None
    per_task: list[TaskStats]
    daily_submissions: list[dict]
    label_distribution: dict


class MyProgress(BaseModel):
    submitted: int
    accepted: int
    rejected: int
    review_accuracy: Optional[float] = None
    gold_answered: int
    gold_correct: int
    gold_accuracy: Optional[float] = None
    daily_submissions: list[dict]
    tasks_claimed: int
