# Two-to-three-minute demonstration script

## 0:00–0:25 — Frame the problem

“Bathroom spare-parts enquiries often arrive as unstructured messages with missing photographs, measurements or markings. Staff must work out what the customer needs, ask the best follow-up question and search for a possible part. This prototype makes that review faster while keeping the decision with the member of staff.”

Point out the mode strip: deterministic demo mode, 40 fictional catalogue records and mandatory staff approval.

## 0:25–1:15 — Show a strong identification case

Load **Shower valve — strong evidence** and select **Analyse enquiry**.

“The app classifies the enquiry, validates a structured record and scores completeness. Here it has the brand, marking, cartridge measurements, symptom and photograph. The catalogue search is restricted to the supplied CSV, so it cannot invent a SKU.”

Open **Catalogue matches**.

“The leading suggestion is a possible match, not a confirmed one. The confidence is accompanied by evidence: category, brand, identifier, measurements and symptoms.”

Open **Validated JSON** briefly to show the Pydantic-backed structure.

## 1:15–1:55 — Show human approval and audit

Open **Draft and decision**.

“The customer response is a draft. A staff member can edit it, choose a catalogue SKU, add a note and approve, reject or escalate. Nothing is sent automatically.”

Choose the leading SKU, save an approval decision, then open **Audit log**.

“The explicit decision is now recorded in SQLite. Common email and phone patterns are redacted before storage.”

## 1:55–2:30 — Show the safety behaviour

Return to **Triage workspace**, load **Vague enquiry — escalation required**, and analyse it.

“This message does not contain enough evidence. The app returns no product candidates, labels the case Human review required, and asks for photographs, brand, markings and measurements instead of guessing.”

## 2:30–2:50 — Close

“This is intentionally a small prototype: structured extraction, missing-information detection, grounded catalogue retrieval, transparent confidence and a human-review audit trail. With authorised internal access, the next step would be live stock and order lookup, inbox integration and learning from approved matches.”

