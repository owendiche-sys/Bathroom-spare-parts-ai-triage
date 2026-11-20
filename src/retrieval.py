from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .models import EnquiryAnalysis, EnquiryCategory, HumanReviewStatus, ProductCategory, ProductSuggestion


MATCHABLE_ENQUIRIES = {
    EnquiryCategory.SPARE_PART_IDENTIFICATION,
    EnquiryCategory.PRODUCT_COMPATIBILITY,
    EnquiryCategory.PRODUCT_FAULT,
    EnquiryCategory.GENERAL_TECHNICAL,
}

CATEGORY_FAMILIES: dict[ProductCategory, set[str]] = {
    ProductCategory.TAPS: {"Taps", "Cartridges"},
    ProductCategory.SHOWER_VALVES: {"Shower valves", "Cartridges"},
    ProductCategory.TOILETS_AND_CISTERNS: {"Toilets and cisterns", "Flush mechanisms"},
    ProductCategory.CARTRIDGES: {"Cartridges"},
    ProductCategory.SHOWER_ENCLOSURES: {"Shower enclosures", "Seals", "Hinges and rollers"},
    ProductCategory.SEALS: {"Seals", "Shower enclosures"},
    ProductCategory.HINGES_AND_ROLLERS: {"Hinges and rollers", "Shower enclosures"},
    ProductCategory.FLUSH_MECHANISMS: {"Flush mechanisms", "Toilets and cisterns"},
    ProductCategory.OTHER: set(),
}


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9-]+", value.lower()) if len(token) > 2}


def _measurement_tokens(value: str) -> set[str]:
    matches = re.findall(
        r"\d+(?:\.\d+)?\s*(?:mm|cm|inches?|inch|in|splines?)?",
        value.lower(),
    )
    return {re.sub(r"\s+", "", item).rstrip("s") for item in matches if item.strip()}


class CatalogueRetriever:
    def __init__(self, catalogue_path: str | Path):
        self.catalogue_path = Path(catalogue_path)
        self.catalogue = pd.read_csv(self.catalogue_path).fillna("")
        required = {
            "sku", "product_name", "brand", "category", "compatible_models",
            "measurements", "markings", "common_symptoms", "product_url", "stock_status",
        }
        missing = required - set(self.catalogue.columns)
        if missing:
            raise ValueError(f"Catalogue is missing columns: {sorted(missing)}")
        self.catalogue["search_text"] = self.catalogue.apply(
            lambda row: " ".join(str(row[column]) for column in required if column not in {"product_url", "stock_status"}),
            axis=1,
        )
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True)
        self.matrix = self.vectorizer.fit_transform(self.catalogue["search_text"])

    @property
    def brands(self) -> list[str]:
        return sorted(self.catalogue["brand"].dropna().astype(str).unique().tolist())

    def search(self, analysis: EnquiryAnalysis, original_message: str, limit: int = 3) -> list[ProductSuggestion]:
        if analysis.enquiry_category not in MATCHABLE_ENQUIRIES:
            return []
        if analysis.information_completeness_score < 60 or analysis.product_category == ProductCategory.OTHER:
            return []

        query = " ".join(
            filter(
                None,
                [
                    original_message,
                    analysis.product_category.value,
                    analysis.brand,
                    analysis.product_or_model_name,
                    analysis.part_code,
                    " ".join(analysis.markings),
                    " ".join(analysis.measurements),
                    analysis.symptoms_or_reported_problem,
                ],
            )
        )
        similarities = cosine_similarity(self.vectorizer.transform([query]), self.matrix)[0]
        allowed_categories = CATEGORY_FAMILIES[analysis.product_category]
        candidates: list[ProductSuggestion] = []

        for index in similarities.argsort()[::-1]:
            row = self.catalogue.iloc[index]
            if allowed_categories and row["category"] not in allowed_categories:
                continue

            evidence: list[str] = []
            confidence = 0.12 + (float(similarities[index]) * 0.58)

            if row["category"] == analysis.product_category.value:
                confidence += 0.10
                evidence.append(f"Category aligns: {row['category']}")
            elif row["category"] in allowed_categories:
                confidence += 0.04
                evidence.append(f"Related catalogue category: {row['category']}")

            if analysis.brand and row["brand"].lower() == analysis.brand.lower():
                confidence += 0.15
                evidence.append(f"Brand matches: {row['brand']}")

            identifiers = " ".join(
                [analysis.part_code or "", " ".join(analysis.markings), analysis.product_or_model_name or ""]
            ).lower()
            catalogue_identifiers = f"{row['sku']} {row['markings']} {row['compatible_models']}".lower()
            identifier_overlap = _tokens(identifiers) & _tokens(catalogue_identifiers)
            if identifier_overlap:
                confidence += 0.14
                evidence.append(f"Identifier evidence: {', '.join(sorted(identifier_overlap))}")

            measurement_overlap = _measurement_tokens(" ".join(analysis.measurements)) & _measurement_tokens(
                str(row["measurements"])
            )
            if measurement_overlap:
                confidence += 0.10
                evidence.append(f"Measurement evidence: {', '.join(sorted(measurement_overlap))}")

            symptom_overlap = _tokens(analysis.symptoms_or_reported_problem or "") & _tokens(str(row["common_symptoms"]))
            if symptom_overlap:
                confidence += min(0.08, 0.02 * len(symptom_overlap))
                evidence.append(f"Symptom evidence: {', '.join(sorted(symptom_overlap)[:4])}")

            confidence = min(0.96, round(confidence, 3))
            if confidence < 0.38:
                continue
            if not evidence:
                evidence.append("Text similarity to catalogue description")

            candidates.append(
                ProductSuggestion(
                    sku=str(row["sku"]),
                    product_name=str(row["product_name"]),
                    brand=str(row["brand"]),
                    category=str(row["category"]),
                    confidence_score=confidence,
                    evidence=evidence,
                    product_url=str(row["product_url"]),
                    stock_status=str(row["stock_status"]),
                )
            )
            if len(candidates) >= min(limit, 3):
                break

        return candidates


def attach_suggestions(analysis: EnquiryAnalysis, suggestions: list[ProductSuggestion]) -> EnquiryAnalysis:
    operational = analysis.enquiry_category not in MATCHABLE_ENQUIRIES
    if suggestions:
        confidence = suggestions[0].confidence_score
        status = (
            HumanReviewStatus.REVIEW_PENDING
            if confidence >= 0.62
            else HumanReviewStatus.HUMAN_REVIEW_REQUIRED
        )
    elif operational:
        confidence = analysis.information_completeness_score / 100
        status = (
            HumanReviewStatus.REVIEW_PENDING
            if analysis.information_completeness_score >= 60
            else HumanReviewStatus.HUMAN_REVIEW_REQUIRED
        )
    else:
        confidence = min(0.49, analysis.information_completeness_score / 100)
        status = HumanReviewStatus.HUMAN_REVIEW_REQUIRED

    return analysis.model_copy(
        update={
            "suggested_products": suggestions[:3],
            "confidence_score": confidence,
            "human_review_status": status,
        }
    )

