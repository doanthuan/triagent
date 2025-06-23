from enum import Enum

from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    CORRECT = "Correct"
    INCORRECT = "Incorrect"
    CANNOT_VERIFY = "Cannot verify"
    PARTIALLY_CORRECT = "Partially correct"


class ConfidenceLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class FactVerifierResponse(BaseModel):
    claim: str = Field(description="The claim identified from the paragraph")
    explanation: str = Field(description="The explanation of the fact")
    evidence: str = Field(
        description="Supporting evidence or reference (e.g., PMID, URL, or description of source)",
    )
    evidence_url: str = Field(description="The URL of the evidence")
    verified: VerificationStatus = Field(
        description="The verification status of the claim",
    )
    confidence_level: ConfidenceLevel = Field(
        description="The confidence level of the verification",
    )
