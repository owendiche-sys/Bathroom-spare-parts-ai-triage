# Application explanation

## Business problem

Customer enquiries can mix product-identification requests, compatibility questions, faults, deliveries and returns in one unstructured message. Important evidence—brand, markings, dimensions, a photograph or an order number—is often absent. Staff therefore repeat the same triage and search work before they can give a useful answer.

## How the prototype works

The Streamlit interface accepts a fictional message and an optional sample image. A deterministic extraction pipeline, or an optional OpenAI-assisted path, maps the message to a Pydantic schema. Category-specific rules score how complete the evidence is and select the most useful next question.

For part-related cases with enough evidence, a TF-IDF retriever searches only the included fictional catalogue. The app returns at most three records, calculates a bounded confidence score and lists the evidence that contributed to each result. It then drafts a response for staff to edit. Approval, rejection or escalation is an explicit action recorded in SQLite.

## Technologies used

- Python and Streamlit for the prototype interface
- Pydantic for structured validation
- Pandas and scikit-learn TF-IDF for catalogue retrieval
- SQLite for the local audit trail
- Optional OpenAI structured extraction, grounded back to text in the source enquiry
- Pytest for automated behavioural and safety checks

## Safeguards and limitations

The retriever cannot produce a product outside the CSV. Low-completeness and low-confidence cases are escalated. Candidate wording avoids confirmation, customer contact is never automatic, and image content is not processed. Common phone and email patterns are removed from stored text, but the prototype still requires fictional data and is not a production privacy control.

There is no live stock, price, customer, order, email or supplier integration. Confidence is a ranking aid, not a statistical guarantee of compatibility. Returns, warranty and complex installation advice remain human decisions.

## Improvements with authorised internal access

The prototype could use live product and availability data, customer and order lookup, email intake, ticket creation, supplier records and catalogue images. Staff-approved matches could become labelled feedback for retrieval evaluation. Aggregate reporting could show enquiry volume, response time, escalation rate and recurring faults, subject to access controls, retention rules and monitoring.

