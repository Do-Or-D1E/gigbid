"""Pydantic request/response models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ProposalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    cover_letter: str = Field(min_length=50, max_length=5000)
    screening_answers: list[str] = Field(default_factory=list, max_length=50)
    bid_amount: float = Field(gt=0)
    bid_type: Literal["fixed", "hourly"]


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=5000)


class ClockAdvance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hours: float = Field(ge=0, le=24 * 365)


class AdminConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_rate: float | None = Field(default=None, ge=0, le=1)
    rate_limit_per_min: int | None = Field(default=None, ge=0)
    policy_version: str | None = None


class LoadJobs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobs: list[dict[str, Any]] = Field(default_factory=list)
    clients: list[dict[str, Any]] = Field(default_factory=list)
