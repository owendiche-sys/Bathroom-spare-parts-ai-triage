from __future__ import annotations

from .models import EnquiryAnalysis, EnquiryCategory, HumanReviewStatus


def generate_draft_response(analysis: EnquiryAnalysis) -> str:
    lines = ["Dear Customer,", "", "Thank you for contacting Bathroom Spare Parts."]

    if analysis.enquiry_category == EnquiryCategory.RETURN_REQUEST:
        if analysis.order_number:
            lines.append(
                f"We have noted your return request for order {analysis.order_number}. A member of the team will review the item and the current returns policy before confirming the next step."
            )
        else:
            lines.append("We can help with your return request, but we need your order number before we can review it.")
    elif analysis.enquiry_category in {EnquiryCategory.ORDER_ENQUIRY, EnquiryCategory.DELIVERY_ENQUIRY}:
        if analysis.order_number:
            lines.append(
                f"We have noted your enquiry about order {analysis.order_number}. A member of the team will check the order details before replying."
            )
        else:
            lines.append("We can look into this for you once we have your order number.")
    elif analysis.suggested_products:
        lead = analysis.suggested_products[0]
        lines.append(
            f"Based on the details supplied, {lead.product_name} ({lead.sku}) is a possible match from our sample catalogue. This is not yet confirmed and must be checked by a member of the team before ordering."
        )
    else:
        lines.append(
            "We do not yet have enough reliable evidence to suggest a part. A member of the team will review the enquiry once the details below are available."
        )

    if analysis.missing_information:
        lines.extend(["", analysis.recommended_next_question])

    if analysis.human_review_status == HumanReviewStatus.HUMAN_REVIEW_REQUIRED:
        lines.extend(["", "We will not confirm a product until these details have been reviewed."])

    lines.extend(["", "Kind regards,", "Bathroom Spare Parts team"])
    return "\n".join(lines)

