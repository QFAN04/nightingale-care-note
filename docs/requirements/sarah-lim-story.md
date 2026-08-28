# Sarah Lim Synthetic Patient Story

This is Nightingale's canonical demo-story specification. Every name, identifier, medical detail, and event is synthetic. Tests, UI behaviour, the demo video, and documentation must share the fixture in `backend/app/seed/sarah_lim.py` rather than inventing conflicting versions.

## People and permissions

- **Patient:** Sarah Lim, born 18 May 1984, patient number `PAT-001`.
- **Staff:** Amanda Wong, who can write staff notes, comment, and document follow-up outcomes.
- **Clinician:** Dr Priya Nair, who performs clinical confirmation, Highlight review, and permitted revision operations.
- **Admin:** Daniel Tan, who has a read-only clinic view in the first version.

## Longitudinal timeline

### 15 April 2026 - Clinician note

Dr Priya Nair confirms Sarah's Penicillin allergy, with urticaria as the previous reaction, and records Atorvastatin 20 mg once daily. Both items are clinician-authoritative context. The allergy is persistent critical safety context and does not disappear through time decay.

### 12 July 2026 - Staff follow-up

Amanda Wong completes a routine telephone follow-up. Sarah explicitly reports no chest pain or chest pressure and no new medication concern. This record provides the time comparison for the later new or worsening symptom.

### 23 August 2026 - Patient-AI session

Sarah reports new chest pressure lasting three days and says it was stronger the previous night. The AI may extract only facts supported by the transcript, preserve an exact quote, and keep both the fact and Highlight in `suggested` status. It cannot confirm a diagnosis or determine final priority.

### 24 August 2026 - Staff follow-up

Amanda confirms that the chest pressure remains present, writes a staff note, uses an `@clinician` comment to request review, and creates an open high-priority task for a clinician to assess and document next steps.

### 25 August 2026 - Doctor consultation

The synthetic raw transcript deliberately contains the name Sarah Lim, Singapore phone number `91234567`, and synthetic ID `S1234567A`. Before any LLM request, these values must become `[PATIENT_NAME]`, `[PHONE]`, and `[ID]`.

Sarah says she believes she is taking Atorvastatin 10 mg, while the clinician-authoritative April note records 20 mg. The system creates a `medication_dose` conflict. It must not overwrite either source or allow the AI to claim that either dose is a new clinical instruction.

## Expected Care Glance context

- **Critical:** Penicillin allergy, clinician-confirmed, retained as persistent safety context.
- **Recent change:** Worsening chest pressure, AI-suggested, awaiting clinician review.
- **Open action:** Assess persistent chest pressure and document next steps.
- **Conflict:** Patient-reported Atorvastatin 10 mg versus the clinician record of 20 mg.

Every Highlight must resolve through `Highlight -> ClinicalFact -> Entry -> ConsultSession` to exact evidence, except that manual records resolve directly to their Entry. Confirming a clinical fact and deciding whether its Highlight belongs in Care Glance are separate review actions.
