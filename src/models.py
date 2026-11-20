from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EnquiryCategory(StrEnum):
    SPARE_PART_IDENTIFICATION = "Spare-part identification"
    PRODUCT_COMPATIBILITY = "Product compatibility"
    PRODUCT_FAULT = "Product fault"
    ORDER_ENQUIRY = "Order enquiry"
    DELIVERY_ENQUIRY = "Delivery enquiry"
    RETURN_REQUEST = "Return request"
    GENERAL_TECHNICAL = "General technical question"


class ProductCategory(StrEnum):
    TAPS = "Taps"
    SHOWER_VALVES = "Shower valves"
    TOILETS_AND_CISTERNS = "Toilets and cisterns"
    CARTRIDGES = "Cartridges"
    SHOWER_ENCLOSURES = "Shower enclosures"
    SEALS = "Seals"
    HINGES_AND_ROLLERS = "Hinges and rollers"
    FLUSH_MECHANISMS = "Flush mechanisms"
    OTHER = "Other"


class HumanReviewStatus(StrEnum):
    REVIEW_PENDING = "Review pending"
    HUMAN_REVIEW_REQUIRED = "Human review required"
    APPROVED = "Approved"
    EDITED_AND_APPROVED = "Edited and approved"
    REJECTED = "Rejected"
    ESCALATED = "Escalated"


class ProductSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sku: str
    product_name: str
    brand: str
    category: str
    confidence_score: float = Field(ge=0, le=1)
    evidence: list[str] = Field(default_factory=list)
    product_url: str
    stock_status: str


class EnquiryAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enquiry_id: str
    enquiry_category: EnquiryCategory
    product_category: ProductCategory
    brand: str | None = None
    product_or_model_name: str | None = None
    part_code: str | None = None
    markings: list[str] = Field(default_factory=list)
    symptoms_or_reported_problem: str | None = None
    measurements: list[str] = Field(default_factory=list)
    order_number: str | None = None
    photograph_attached: bool = False
    information_completeness_score: int = Field(ge=0, le=100)
    missing_information: list[str] = Field(default_factory=list)
    recommended_next_question: str
    suggested_products: list[ProductSuggestion] = Field(default_factory=list, max_length=3)
    confidence_score: float = Field(ge=0, le=1)
    human_review_status: HumanReviewStatus

    def as_json_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

