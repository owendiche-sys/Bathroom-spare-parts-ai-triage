from pathlib import Path

from src.extraction import extract_enquiry
from src.models import HumanReviewStatus
from src.retrieval import CatalogueRetriever, attach_suggestions


CATALOGUE = Path(__file__).parents[1] / "data" / "sample_catalogue.csv"


def test_retrieval_returns_only_catalogue_skus_and_at_most_three():
    retriever = CatalogueRetriever(CATALOGUE)
    message = (
        "Northbridge Tempra 200 shower valve cartridge marked NB-T200. "
        "It is 86 mm long, 32 mm wide and has 20 splines. Temperature stuck hot. Photos attached."
    )
    analysis = extract_enquiry(message, False, retriever.brands, enquiry_id="ENQ-TEST1001")
    suggestions = retriever.search(analysis, message)
    catalogue_skus = set(retriever.catalogue["sku"])

    assert 1 <= len(suggestions) <= 3
    assert suggestions[0].sku == "FSP-CAR-003"
    assert all(suggestion.sku in catalogue_skus for suggestion in suggestions)
    assert all(suggestion.evidence for suggestion in suggestions)
    assert any("Measurement evidence" in item for item in suggestions[0].evidence)


def test_low_completeness_returns_no_suggestions_and_requires_review():
    retriever = CatalogueRetriever(CATALOGUE)
    message = "The bathroom thing is broken and I need a part."
    analysis = extract_enquiry(message, False, retriever.brands, enquiry_id="ENQ-TEST1002")
    result = attach_suggestions(analysis, retriever.search(analysis, message))

    assert result.suggested_products == []
    assert result.human_review_status == HumanReviewStatus.HUMAN_REVIEW_REQUIRED


def test_operational_enquiry_never_triggers_product_search():
    retriever = CatalogueRetriever(CATALOGUE)
    message = "Please return my unopened seal from order BSP-10482 because it is the wrong size."
    analysis = extract_enquiry(message, False, retriever.brands, enquiry_id="ENQ-TEST1003")
    assert retriever.search(analysis, message) == []

