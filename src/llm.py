from __future__ import annotations

import os

from openai import OpenAI
from pydantic import BaseModel, Field

from .extraction import extract_enquiry, finalise_analysis
from .models import EnquiryCategory, ProductCategory
from .privacy import redact_pii


class LLMExtraction(BaseModel):
    enquiry_category: EnquiryCategory
    product_category: ProductCategory
    brand: str | None = None
    product_or_model_name: str | None = None
    part_code: str | None = None
    markings: list[str] = Field(default_factory=list)
    symptoms_or_reported_problem: str | None = None
    measurements: list[str] = Field(default_factory=list)
    order_number: str | None = None


def _grounded(value: str | None, source: str) -> str | None:
    if not value:
        return None
    return value if value.lower() in source.lower() else None


def extract_with_openai(
    message: str,
    photograph_attached: bool,
    known_brands: list[str],
    model: str | None = None,
):
    """Optional extraction path; all free-text values are grounded back to the source."""
    base = extract_enquiry(message, photograph_attached, known_brands)
    client = OpenAI()
    safe_message = redact_pii(message)
    completion = client.beta.chat.completions.parse(
        model=model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract only facts explicitly present in this fictional bathroom spare-parts enquiry. "
                    "Do not infer or invent a brand, model, code, marking, measurement, or order number."
                ),
            },
            {"role": "user", "content": safe_message},
        ],
        response_format=LLMExtraction,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise ValueError("The model did not return a validated extraction.")

    updates = {
        "enquiry_category": parsed.enquiry_category,
        "product_category": parsed.product_category,
        "brand": _grounded(parsed.brand, safe_message),
        "product_or_model_name": _grounded(parsed.product_or_model_name, safe_message),
        "part_code": _grounded(parsed.part_code, safe_message),
        "markings": [item for item in parsed.markings if item.lower() in safe_message.lower()],
        "symptoms_or_reported_problem": parsed.symptoms_or_reported_problem or base.symptoms_or_reported_problem,
        "measurements": [item for item in parsed.measurements if item.lower() in safe_message.lower()],
        "order_number": _grounded(parsed.order_number, safe_message),
    }
    return finalise_analysis(base.model_copy(update=updates))
