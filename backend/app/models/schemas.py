from typing import Any

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(default="Smart Notification Summary")
    description: str = Field(default="")
    product_idea: str = Field(default="")


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    product_idea: str | None = None


class RunCreate(BaseModel):
    user_input: str


class AdjustmentCreate(BaseModel):
    message: str
    selected_version: str | None = None
    selected_tab: str | None = None


class Project(BaseModel):
    id: str
    name: str
    description: str
    product_idea: str
    current_version: str
    created_at: str
    updated_at: str


class Artefact(BaseModel):
    id: str
    project_id: str
    kind: str
    version: str
    path: str
    content_type: str
    created_at: str


class RunRecord(BaseModel):
    id: str
    project_id: str
    version: str
    user_input: str
    status: str
    message: str
    created_at: str


class ProjectDetail(BaseModel):
    project: Project
    artefacts: list[Artefact]
    runs: list[RunRecord]
    latest: dict[str, Any]


class RunResponse(BaseModel):
    run: RunRecord
    project: Project
    artefacts: list[Artefact]
    state: dict[str, Any]
