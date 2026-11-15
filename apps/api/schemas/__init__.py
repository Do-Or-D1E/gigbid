"""Request and response models of the GigBid API. The web client's TypeScript types are
generated from the OpenAPI schema these produce (apps/web/src/lib/api)."""
from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

Email = Annotated[str, Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=200)]


# ----------------------------------------------------------------------------- auth / onboarding
class RegisterIn(BaseModel):
    email: Email
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=80)


class LoginIn(BaseModel):
    email: Email
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    persona_id: str | None = None
    onboarded: bool = False


class TokenOut(BaseModel):
    token: str
    user: UserOut


class PersonaOut(BaseModel):
    id: str
    name: str
    headline: str
    skills: list[str]
    hourly_rate_usd: float
    min_project_usd: float
    weekly_connects_budget: int


class SavedSearchIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    query: str = Field(default="", max_length=200)
    category: str | None = None
    interval_minutes: int = Field(default=30, ge=10, le=1440)


class SavedSearchOut(SavedSearchIn):
    id: int
    last_run_at: str | None = None
    enabled: bool = True


class OnboardingIn(BaseModel):
    persona_id: str
    marketplace: Literal["gigsim", "upwork_live"] = "gigsim"
    hourly_rate_usd: float = Field(gt=0, le=1000)
    min_project_usd: float = Field(ge=0, le=100000)
    weekly_connects_budget: int = Field(ge=0, le=500)
    saved_search: SavedSearchIn | None = None


class ConnectedAccount(BaseModel):
    mode: str
    account_id: str
    connected_at: str | None = None


class SettingsOut(BaseModel):
    autonomy: Literal["suggest", "auto_skip_low_fit"] = "suggest"
    hourly_rate_usd: float | None = None
    min_project_usd: float | None = None
    weekly_connects_budget: int | None = None
    hidden_items: list[str] = Field(default_factory=list)
    saved_searches: list[SavedSearchOut] = Field(default_factory=list)
    connected_accounts: list[ConnectedAccount] = Field(default_factory=list)
    model_profile: str = "open"
    marketplace_mode: str = "gigsim"
    policy_version: int = 1
    rag_variant: str = ""


class SettingsIn(BaseModel):
    autonomy: Literal["suggest", "auto_skip_low_fit"] | None = None
    hourly_rate_usd: float | None = Field(default=None, gt=0, le=1000)
    min_project_usd: float | None = Field(default=None, ge=0)
    weekly_connects_budget: int | None = Field(default=None, ge=0, le=500)


class MemoryItem(BaseModel):
    key: str
    kind: Literal["style", "outcome"]
    text: str
    support: int | None = None
    detail: dict[str, Any] = Field(default_factory=dict)


class MemoryOut(BaseModel):
    style: list[MemoryItem]
    outcome: list[MemoryItem]
    pending_edits: list[list[str]] = Field(default_factory=list)
    promotion_rule: str


class PortfolioItemOut(BaseModel):
    item_id: str
    type: str
    title: str
    date: str | None = None
    hidden: bool = False


class UploadIn(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    text: str = Field(min_length=50, max_length=20000)
    kind: Literal["case_study", "repo", "review", "upload"] = "case_study"


# ----------------------------------------------------------------------------- jobs
class RiskFlagOut(BaseModel):
    kind: str
    evidence: str
    severity: str


class PriceOut(BaseModel):
    bid_type: str
    amount: float
    connects_cost: int | None = None
    connects_usd: float | None = None
    expected_value_usd: float | None = None
    worth_it: bool | None = None
    rationale: str = ""
    market_p25: float | None = None
    market_p50: float | None = None
    market_p75: float | None = None
    floor: float | None = None
    win_probability: float | None = None


class JobCard(BaseModel):
    job_id: str
    title: str
    category: str | None = None
    budget_type: str | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    posted_at: str | None = None
    status: str
    action: str | None = None
    fit_score: float | None = None
    risk_score: float | None = None
    risk_flags: list[RiskFlagOut] = Field(default_factory=list)
    price: PriceOut | None = None
    connects_cost: int | None = None
    injection_detected: bool = False
    thread_id: str | None = None
    updated_at: str | None = None


class EvidenceOut(BaseModel):
    item_id: str
    type: str
    title: str
    snippet: str
    source: str = ""
    date: str | None = None
    outcome: str | None = None


class MatrixRow(BaseModel):
    requirement: str
    strength: str
    reason: str = ""
    evidence: list[EvidenceOut]


class RunRef(BaseModel):
    run_id: str
    thread_id: str
    status: str = "queued"


class RunOut(BaseModel):
    run_id: str
    kind: str
    status: str
    thread_id: str
    job_id: str | None = None
    created_at: str | None = None
    finished_at: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    trace_url: str | None = None
    error: str | None = None


class JobDetailOut(BaseModel):
    card: JobCard
    job: dict[str, Any]
    job_spec: dict[str, Any] | None = None
    risk: dict[str, Any] | None = None
    fit: dict[str, Any] | None = None
    decision: dict[str, Any] | None = None
    matrix: list[MatrixRow] = Field(default_factory=list)
    claim_report: dict[str, Any] | None = None
    compliance: dict[str, Any] | None = None
    critiques: list[dict[str, Any]] = Field(default_factory=list)
    attention: str | None = None
    runs: list[RunOut] = Field(default_factory=list)
    approval_pending: bool = False


class SkipIn(BaseModel):
    reason: str = Field(default="not interested", max_length=300)


# ----------------------------------------------------------------------------- approvals
class ScreeningAnswerIO(BaseModel):
    question: str
    answer: str


class DecisionIn(BaseModel):
    action: Literal["approve", "edit", "reject"]
    edited_cover_letter: str | None = Field(default=None, max_length=5000)
    edited_answers: list[ScreeningAnswerIO] | None = None
    reason: str | None = Field(default=None, max_length=500)


class ApprovalOut(BaseModel):
    thread_id: str
    kind: str
    job_id: str | None = None
    status: str
    payload: dict[str, Any]
    decision: dict[str, Any] | None = None
    created_at: str | None = None
    run_id: str | None = None


class RegenerateIn(BaseModel):
    paragraph_index: int = Field(ge=0, le=20)
    instruction: str = Field(default="", max_length=300)


class RegenerateOut(BaseModel):
    text: str
    removed: list[str] = Field(default_factory=list)


# ----------------------------------------------------------------------------- pipeline / messages
class PipelineCard(BaseModel):
    proposal_id: str
    job_id: str | None = None
    title: str = ""
    stage: str
    amount: float | None = None
    connects: int | None = None
    updated_at: str | None = None
    thread_id: str | None = None


class PipelineOut(BaseModel):
    columns: dict[str, list[PipelineCard]]


class ThreadOut(BaseModel):
    thread_id: str
    job_id: str | None = None
    title: str = ""
    last_message: str = ""
    last_sender: str | None = None
    updated_at: str | None = None
    pending_reply: bool = False


class MessageOut(BaseModel):
    sender: str
    text: str
    at: str | None = None


class ThreadDetailOut(BaseModel):
    thread_id: str
    messages: list[MessageOut]
    approval: ApprovalOut | None = None
    runs: list[RunOut] = Field(default_factory=list)


# ----------------------------------------------------------------------------- runs / analytics / health
class RunEventOut(BaseModel):
    id: int
    ts: str
    kind: str
    node: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class SpanOut(BaseModel):
    kind: str
    name: str
    node: str | None = None
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    usd: float = 0.0
    list_usd: float = 0.0
    latency_s: float = 0.0
    error: str | None = None


class RunDetailOut(RunOut):
    events: list[RunEventOut] = Field(default_factory=list)
    spans: list[SpanOut] = Field(default_factory=list)
    per_node: list[dict[str, Any]] = Field(default_factory=list)


class CheckpointOut(BaseModel):
    checkpoint_id: str
    next: list[str]
    created_at: str | None = None
    status: str | None = None


class ShareOut(BaseModel):
    url: str


class CategoryStat(BaseModel):
    category: str
    submitted: int
    replied: int
    hired: int
    reply_rate: float
    hire_rate: float


class AnalyticsOut(BaseModel):
    by_category: list[CategoryStat]
    connects_spent: int
    connects_per_reply: float | None = None
    jobs_analysed: int
    proposals: int
    latency: dict[str, float | None]
    cost: dict[str, float | None]
    rejection_reasons: list[dict[str, Any]]
    decisions: dict[str, int]


class HealthOut(BaseModel):
    ok: bool
    db: bool
    marketplace: Literal["up", "down", "unknown"]
    marketplace_detail: str = ""
    model_profile: str
    marketplace_mode: str
    policy_version: int
    rag_variant: str
    version: str = "0.1.0"
