from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobType(str, Enum):
    INGESTION = "ingestion"
    QUIZ_GENERATION = "quiz_generation"
    ANSWER_EVALUATION = "answer_evaluation"
