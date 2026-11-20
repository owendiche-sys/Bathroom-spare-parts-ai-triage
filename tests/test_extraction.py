from src.extraction import extract_enquiry
from src.models import EnquiryCategory, HumanReviewStatus, ProductCategory


BRANDS = ["AquaVale", "Northbridge", "FlushCraft"]


def test_extracts_complete_shower_cartridge_enquiry():
    message = (
        "Northbridge Tempra 200 shower valve. The cartridge is marked NB-T200, "
        "86 mm long and 32 mm wide with 20 splines. It is stuck hot. Photos attached."
    )
    result = extract_enquiry(message, False, BRANDS, enquiry_id="ENQ-TEST0001")

    assert result.enquiry_category == EnquiryCategory.PRODUCT_FAULT
    assert result.product_category == ProductCategory.CARTRIDGES
    assert result.brand == "Northbridge"
    assert "NB-T200" in result.markings
    assert {"86 mm", "32 mm", "20 splines"}.issubset(set(result.measurements))
    assert result.photograph_attached is True
    assert result.information_completeness_score >= 85
    assert result.human_review_status == HumanReviewStatus.REVIEW_PENDING


def test_vague_enquiry_is_escalated_without_guessing():
    result = extract_enquiry(
        "The thing in my bathroom is broken. Can you tell me what I need?",
        False,
        BRANDS,
        enquiry_id="ENQ-TEST0002",
    )

    assert result.product_category == ProductCategory.OTHER
    assert result.brand is None
    assert result.information_completeness_score < 60
    assert result.human_review_status == HumanReviewStatus.HUMAN_REVIEW_REQUIRED


def test_return_enquiry_extracts_order_number():
    result = extract_enquiry(
        "I need to return an unopened seal from order BSP-10482 because it is the wrong size.",
        False,
        BRANDS,
        enquiry_id="ENQ-TEST0003",
    )

    assert result.enquiry_category == EnquiryCategory.RETURN_REQUEST
    assert result.order_number == "BSP-10482"
    assert result.information_completeness_score >= 60


def test_absence_phrase_does_not_become_part_code():
    result = extract_enquiry(
        "My FlushCraft flush valve has no visible product code. It keeps running.",
        False,
        BRANDS,
        enquiry_id="ENQ-TEST0004",
    )
    assert result.part_code is None

