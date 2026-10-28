import re
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


class AnalysisCreate(BaseModel):
    repo_url: str = Field(max_length=300)
    focus: Literal["quality", "architecture", "tests"] = "quality"

    @field_validator("repo_url")
    @classmethod
    def validate_repo(cls, value):
        parsed = urlparse(value.strip())
        parts = parsed.path.strip("/").removesuffix(".git").split("/")
        if (
            parsed.scheme != "https"
            or parsed.netloc != "github.com"
            or parsed.query
            or parsed.fragment
            or len(parts) != 2
            or not all(re.fullmatch(r"[A-Za-z0-9_.-]+", p) and p not in {".", ".."} for p in parts)
        ):
            raise ValueError("Use https://github.com/usuario/repositorio, sem parâmetros.")
        return "https://github.com/" + "/".join(parts)


class FindingDraft(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    severity: Literal["high", "medium", "low"]
    category: Literal["quality", "architecture", "tests", "security"]
    path: str = Field(max_length=500)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    evidence: str = Field(min_length=1, max_length=6000)
    description: str = Field(min_length=1, max_length=3000)
    recommendation: str = Field(min_length=1, max_length=3000)


class ReportDraft(BaseModel):
    summary: str = Field(min_length=1, max_length=5000)
    findings: list[FindingDraft] = Field(max_length=20)


class ResolveUpdate(BaseModel):
    resolved: bool
