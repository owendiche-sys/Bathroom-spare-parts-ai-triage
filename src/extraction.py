from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from .models import (
    EnquiryAnalysis,
    EnquiryCategory,
    HumanReviewStatus,
    ProductCategory,
)


MEASUREMENT_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s?(?:mm|cm|inches?|inch|in)\b|\b\d+\s*[- ]?spline(?:s)?\b",
    re.IGNORECASE,
)

ORDER_PATTERN = re.compile(
    r"\border\s*(?:number|no\.?|#)?\s*[:#-]?\s*([A-Z]{1,5}-?\d{3,10})\b",
    re.IGNORECASE,
)

PART_CODE_PATTERN = re.compile(
    r"\b(?:part|product|sku)\s*(?:code|number|no\.?)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9-]{3,24})\b",
    re.IGNORECASE,
)

MARKING_PATTERN = re.compile(
    r"\b(?:marked|marking(?:s)?(?: read| say)?|stamped)\s*[:#-]?\s*([A-Z0-9][A-Z0-9-]{2,24})\b",
    re.IGNORECASE,
)

MODEL_PATTERN = re.compile(
    r"\b(?:model|range)\s*(?:name|number|no\.?)?\s*[:#-]?\s*([A-Za-z0-9][A-Za-z0-9 -]{1,28}?)(?=[,.;\n]|\s+(?:with|and|but|is|has)\b|$)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CompletenessResult:
    score: int
    missing: list[str]
    next_question: str


def _normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" ,.;:-")


def classify_enquiry(message: str) -> EnquiryCategory:
    text = message.lower()
    if any(term in text for term in ("return", "refund", "send it back", "send back", "rma")):
        return EnquiryCategory.RETURN_REQUEST
    if any(term in text for term in ("delivery", "delivered", "courier", "tracking", "where is my parcel", "arrive")):
        return EnquiryCategory.DELIVERY_ENQUIRY
    if any(term in text for term in ("order status", "cancel my order", "change my order", "invoice", "ordered")):
        return EnquiryCategory.ORDER_ENQUIRY
    if any(term in text for term in ("compatible", "compatibility", "will this fit", "fit my", "replacement for")):
        return EnquiryCategory.PRODUCT_COMPATIBILITY
    if any(term in text for term in ("fault", "faulty", "leak", "drip", "stuck", "jammed", "broken", "no hot", "no cold")):
        return EnquiryCategory.PRODUCT_FAULT
    if any(term in text for term in ("how do i", "how to", "install", "installation", "adjust", "technical question")):
        return EnquiryCategory.GENERAL_TECHNICAL
    return EnquiryCategory.SPARE_PART_IDENTIFICATION


def classify_product(message: str) -> ProductCategory:
    text = message.lower()
    rules: list[tuple[ProductCategory, tuple[str, ...]]] = [
        (ProductCategory.HINGES_AND_ROLLERS, ("hinge", "roller", "wheel", "pivot")),
        (ProductCategory.SEALS, ("seal", "sweep", "water guard")),
        (ProductCategory.FLUSH_MECHANISMS, ("flush valve", "flush mechanism", "flush button", "dual flush", "syphon")),
        (ProductCategory.CARTRIDGES, ("cartridge", "ceramic valve", "thermostatic element")),
        (ProductCategory.SHOWER_VALVES, ("shower valve", "thermostatic shower", "concealed valve", "mixer valve")),
        (ProductCategory.SHOWER_ENCLOSURES, ("shower enclosure", "shower door", "bath screen", "cubicle")),
        (ProductCategory.TOILETS_AND_CISTERNS, ("toilet", "cistern", "toilet seat", "fill valve")),
        (ProductCategory.TAPS, ("tap", "faucet", "basin mixer", "bath mixer")),
    ]
    for category, terms in rules:
        if any(term in text for term in terms):
            return category
    return ProductCategory.OTHER


def extract_brand(message: str, known_brands: list[str]) -> str | None:
    for brand in sorted(known_brands, key=len, reverse=True):
        if re.search(rf"\b{re.escape(brand)}\b", message, re.IGNORECASE):
            return brand
    match = re.search(r"\bbrand\s*(?:is|:|-)?\s*([A-Z][A-Za-z0-9& -]{1,24})", message)
    if not match:
        return None
    return _normalise(match.group(1).split(",")[0])


def _extract_symptom(message: str) -> str | None:
    symptom_terms = (
        "drip", "leak", "stuck", "jam", "broken", "fault", "hot", "cold",
        "pressure", "noisy", "loose", "cracked", "won't", "doesn't", "wrong size",
        "unopened", "damaged", "missing", "identify", "replacement",
    )
    sentences = re.split(r"(?<=[.!?])\s+|\n+", message)
    matches = [sentence.strip() for sentence in sentences if any(term in sentence.lower() for term in symptom_terms)]
    if not matches:
        return _normalise(message)[:240] if len(message.split()) >= 5 else None
    return _normalise(" ".join(matches))[:320]


def _identifier_present(analysis: EnquiryAnalysis) -> bool:
    return bool(analysis.part_code or analysis.markings or analysis.product_or_model_name)


def calculate_completeness(analysis: EnquiryAnalysis) -> CompletenessResult:
    category = analysis.enquiry_category
    product_known = analysis.product_category != ProductCategory.OTHER
    has_issue = bool(analysis.symptoms_or_reported_problem)

    if category in {EnquiryCategory.ORDER_ENQUIRY, EnquiryCategory.DELIVERY_ENQUIRY}:
        checks = [
            (analysis.order_number, 60, "Order number"),
            (has_issue, 40, "What help is needed"),
        ]
    elif category == EnquiryCategory.RETURN_REQUEST:
        checks = [
            (analysis.order_number, 60, "Order number"),
            (has_issue, 25, "Reason for return"),
            (analysis.photograph_attached, 15, "Photograph of the item and packaging label, if relevant"),
        ]
    elif category == EnquiryCategory.PRODUCT_FAULT:
        checks = [
            (product_known, 15, "Product category"),
            (analysis.brand, 15, "Brand"),
            (_identifier_present(analysis), 15, "Model, part code or markings"),
            (has_issue, 30, "Fault symptoms"),
            (analysis.photograph_attached, 15, "Photograph"),
            (analysis.measurements, 10, "Key measurements"),
        ]
    elif category == EnquiryCategory.GENERAL_TECHNICAL:
        checks = [
            (product_known, 20, "Product category"),
            (analysis.brand, 15, "Brand"),
            (_identifier_present(analysis), 15, "Model, part code or markings"),
            (has_issue, 30, "Technical question or symptom"),
            (analysis.photograph_attached, 10, "Photograph"),
            (analysis.measurements, 10, "Relevant measurements"),
        ]
    else:
        checks = [
            (product_known, 20, "Product category"),
            (analysis.brand, 15, "Brand"),
            (analysis.photograph_attached, 20, "Photograph"),
            (analysis.measurements, 20, "Key measurements"),
            (_identifier_present(analysis), 15, "Model, part code or markings"),
            (has_issue, 10, "What the part does or the reported problem"),
        ]

    score = sum(weight for present, weight, _ in checks if bool(present))
    missing = [label for present, _, label in checks if not bool(present)]
    next_question = recommended_question(analysis, missing)
    return CompletenessResult(score=score, missing=missing, next_question=next_question)


def recommended_question(analysis: EnquiryAnalysis, missing: list[str]) -> str:
    if not missing:
        return "No essential information is missing. Please confirm the proposed response and any product match before sending."
    if "Order number" in missing:
        return "Please provide your order number so we can review the order and advise on the correct next step."
    category = analysis.product_category
    if category == ProductCategory.CARTRIDGES:
        return "Please provide the cartridge length, body diameter and spline count, together with a clear photograph showing any markings."
    if category == ProductCategory.TAPS:
        return "Please send a photograph of the complete tap and the removed valve or cartridge, including its key measurements and any markings."
    if category == ProductCategory.SHOWER_VALVES:
        return "Please send photographs of the valve with the handles and cover plate removed, plus any markings and the cartridge dimensions."
    if category in {ProductCategory.TOILETS_AND_CISTERNS, ProductCategory.FLUSH_MECHANISMS}:
        return "Please send photographs of the cistern internals, flush button and removed part, together with the outlet diameter and overall height."
    if category in {ProductCategory.SHOWER_ENCLOSURES, ProductCategory.HINGES_AND_ROLLERS, ProductCategory.SEALS}:
        return "Please send a photograph of the whole enclosure and close-ups of the part, including any markings and key dimensions."
    if analysis.enquiry_category == EnquiryCategory.PRODUCT_FAULT:
        return "Please provide the brand, model or part code, photographs of the product, and a clear description of when the fault occurs."
    return "Please send clear photographs of the complete fitting and the part you need, together with the brand, markings and key measurements."


def finalise_analysis(analysis: EnquiryAnalysis) -> EnquiryAnalysis:
    completeness = calculate_completeness(analysis)
    confidence = completeness.score / 100
    status = (
        HumanReviewStatus.REVIEW_PENDING
        if completeness.score >= 60
        else HumanReviewStatus.HUMAN_REVIEW_REQUIRED
    )
    return analysis.model_copy(
        update={
            "information_completeness_score": completeness.score,
            "missing_information": completeness.missing,
            "recommended_next_question": completeness.next_question,
            "confidence_score": confidence,
            "human_review_status": status,
        }
    )


def extract_enquiry(
    message: str,
    photograph_attached: bool,
    known_brands: list[str],
    enquiry_id: str | None = None,
) -> EnquiryAnalysis:
    measurements = list(dict.fromkeys(_normalise(item) for item in MEASUREMENT_PATTERN.findall(message)))
    markings = list(dict.fromkeys(match.upper() for match in MARKING_PATTERN.findall(message)))
    order_match = ORDER_PATTERN.search(message)
    part_match = PART_CODE_PATTERN.search(message)
    model_match = MODEL_PATTERN.search(message)
    part_code = part_match.group(1).upper() if part_match else None
    if part_code in {"CODE", "NUMBER", "UNKNOWN", "NONE", "VISIBLE", "READABLE"}:
        part_code = None

    analysis = EnquiryAnalysis(
        enquiry_id=enquiry_id or f"ENQ-{uuid.uuid4().hex[:8].upper()}",
        enquiry_category=classify_enquiry(message),
        product_category=classify_product(message),
        brand=extract_brand(message, known_brands),
        product_or_model_name=_normalise(model_match.group(1)) if model_match else None,
        part_code=part_code,
        markings=markings,
        symptoms_or_reported_problem=_extract_symptom(message),
        measurements=measurements,
        order_number=order_match.group(1).upper() if order_match else None,
        photograph_attached=photograph_attached or any(
            phrase in message.lower() for phrase in ("photo attached", "photos attached", "attached a photo", "attached photos")
        ),
        information_completeness_score=0,
        missing_information=[],
        recommended_next_question="",
        suggested_products=[],
        confidence_score=0,
        human_review_status=HumanReviewStatus.HUMAN_REVIEW_REQUIRED,
    )
    return finalise_analysis(analysis)

