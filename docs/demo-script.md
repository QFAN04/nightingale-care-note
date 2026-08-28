# Nightingale 72HR Build - Demo Script

This script uses only the synthetic Sarah Lim story. The target recording length is 6-8 minutes. The main demonstration is completed entirely through the Nightingale UI.

## Pre-demo reset and safety check

Use the dedicated Nightingale database only. The reset command refuses to run if it finds a patient, clinic, or user outside the fixed synthetic Sarah story.

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.seed.command --reset-demo
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

In a second PowerShell window:

```powershell
cd frontend
npm run dev
```

Before recording:

1. Confirm the reset reports `Synthetic Sarah Lim demo data: reset to canonical state.`
2. Open `http://localhost:3000` and select **Clinician view / Dr Priya Nair**.
3. Confirm Care Glance initially contains **Penicillin allergy**, **Worsening chest pressure**, one open clinician-review task, and the **Atorvastatin discrepancy**.
4. Confirm the local backend environment contains a working DeepSeek key without displaying the file or secret on screen.
5. Never show `.env`, API keys, database credentials, Supabase connection strings, or real patient information in the recording.

## 6-8 minute English presentation

### 1. Introduction and patient context

**Computer action:** Open Nightingale, keep **Clinician view / Dr Priya Nair**, and select **Sarah Lim**.

**Say:**

> Hello, this is Nightingale Care Note, a local-first longitudinal care-record prototype built for the Nightingale 72HR Build. This demonstration uses only the fixed synthetic patient Sarah Lim. The product is organised around three questions: what matters now, where the information came from, and who reviewed or changed it.

### 2. Explain Care Glance

**Computer action:** Point to **Critical**, **Recent changes**, **Open actions**, and **Conflicts**.

**Say:**

> At the top is Care Glance. It is not a free-form AI summary. It is a deterministic read model built from structured clinical state. It currently shows a persistent penicillin allergy, worsening chest pressure, an open clinician-review action, and an Atorvastatin discrepancy. The language model never decides the final clinical priority by itself.

### 3. Trace a Glance item to exact evidence

**Computer action:** Expand **Worsening chest pressure**, point to the source quote, and select **Jump to source**.

**Say:**

> Every Glance item remains traceable. This exact quote came from the August 23 AI-patient session. The provenance chain is Highlight to ClinicalFact to Entry to ConsultSession. Human-authored notes resolve directly to their Entry. This means a concise view never removes the underlying evidence.

### 4. Run a real AI Scribe consultation

**Computer action:** Select **New AI Scribe**. Confirm that the interaction type is read-only and displays **Doctor-patient consultation**. Copy and paste this exact synthetic transcript:

```text
Doctor: Please confirm your details.
Patient: I am Sarah Lim, phone 91234567, ID S1234567A.
Doctor: Have you noticed any new allergies?
Patient: I have a severe latex allergy and previously had anaphylaxis.
Doctor: When was the most recent reaction?
Patient: About two years ago after a medical procedure.
```

**Computer action:** Select **Generate** once and wait for the real DeepSeek response.

**Say while waiting:**

> The current identity determines the interaction type, so the client cannot claim a different clinical role. Before the provider is called, deterministic redaction replaces the known patient name, Singapore phone number, and ID-like value. The real API key remains only in the local backend environment.

### 5. Explain validation and the trust boundary

**Computer action:** Point to **PHI redacted**, the summary, extracted facts, and exact source quote.

**Say:**

> DeepSeek output is treated as untrusted structured input. It must pass the Pydantic schema, and every source quote must exist in the redacted transcript. Only a fully validated response is committed. The UI intentionally shows the redaction status rather than creating another browser copy of the complete redacted transcript.

### 6. Review the new Critical suggestion

**Computer action:** Close the dialog, wait for Timeline and Care Glance to reload, and locate **Latex allergy**. Select **Accept**.

**Say:**

> The extracted allergy appears as Suggested first. AI output cannot promote itself to clinician-confirmed truth. Accept means that I confirm this information should be prioritised in Care Glance; it does not mean the system independently made a diagnosis. Repeating the same persistent critical entity will not create another active Latex allergy card, although the source consultation remains preserved in the Timeline.

### 7. Explain the medication conflict

**Computer action:** Expand **Atorvastatin discrepancy**. Do not resolve it during the main recording.

**Say:**

> Sarah reported taking 10 milligrams, while the clinician-authoritative April record states 20 milligrams once daily. Nightingale preserves both sources and raises a conflict. It does not silently overwrite either statement, and the language model cannot issue a new medication instruction. I am leaving the conflict open so its unresolved state remains visible throughout the demonstration.

### 8. Create a manual Staff note

**Computer action:** Switch to **Staff view / Amanda Wong**, select **Add note**, and paste:

```text
Patient confirmed that chest pressure is improving today. Clinician review remains requested before closing follow-up.
```

**Computer action:** Select **Save note**.

**Say:**

> For a manual note, the client sends only non-empty content. The server derives the author, role, entry type, clinic scope, and manual provenance from the authenticated demo identity. The write also creates a complete Version 1 snapshot and a metadata-only audit event. Refreshing the Timeline does not remove the new note.

### 9. Show internal collaboration

**Computer action:** Open the August 24 **Follow-up escalated** Staff note and show Amanda Wong's `@clinician` comment. Optionally reply with:

```text
@clinician Reviewed during today's consultation.
```

**Say:**

> Staff and clinicians can collaborate around a timeline entry. These internal comments are role-scoped and are not returned to the Patient view.

### 10. Create a revision

**Computer action:** Switch back to **Clinician view / Dr Priya Nair**. Open **Version history** on the April 15 **Medication and allergy context** note. Append this sentence to the current content:

```text
Review again in four weeks.
```

**Computer action:** Select **Save revision**, then reopen Version history.

**Say:**

> A revision sends the expected version that the user started editing. If another update has already occurred, the server returns a 409 conflict and the UI reloads the latest version instead of silently overwriting it.

### 11. Compare and revert without deleting history

**Computer action:** Select **From v1**, **To v2**, and **Compare versions**. Then select **Revert to version 1** and confirm. Reopen Version history and show Version 3.

**Say:**

> Storage uses immutable full snapshots, while the comparison is calculated on demand. The added sentence is visible in the Diff. Revert does not delete Version 2; it appends Version 3 with the earlier content. The complete audit trail remains intact.

### 12. Demonstrate backend-enforced RBAC

**Computer action:** Return to the home view and switch to **Patient view / Sarah Lim**.

**Say:**

> The Patient role receives only its permitted patient scope and accepted content. Internal Staff notes, comments, suggested Highlights, open internal actions, and unresolved conflicts are filtered by the backend. This is not merely visual hiding. Cross-clinic access returns 404, and deny-by-default Supabase RLS provides a second protection layer behind the FastAPI policy.

### 13. Close with bounded self-learning

**Computer action:** Switch back to **Clinician view** and stop on Care Glance.

**Say:**

> Clinician Accept and Reject feedback can slightly adjust the future ranking of similar entities inside the same clinic. The learning bonus is clamped between zero and three. It cannot change a clinical risk label, transfer across clinics, or bypass clinician review. Nightingale uses AI to make longitudinal information easier to navigate without allowing AI to erase source, authority, or accountability. Thank you.

## Additional copy-ready rehearsal cases

Use these only for testing or a separate rehearsal. Run `--reset-demo` before the final recording so these trials do not pollute Care Glance.

### Recent change case - Nurse-patient Scribe

Switch to **Staff view / Amanda Wong**, open **New AI Scribe**, and paste:

```text
Nurse: How is the chest pressure compared with yesterday?
Patient: It has improved from seven out of ten to three out of ten.
Nurse: Do you still feel it while resting?
Patient: No, but it returns when I walk quickly.
Nurse: I will keep the clinician review request open for today.
Patient: Yes, please ask the doctor to review it.
```

Expected checks:

- The interaction type is locked to **Nurse-patient consultation**.
- The output preserves the improvement and exertional recurrence without inventing a diagnosis.
- A qualifying transient symptom is placed under **Recent changes**, not **Critical**.
- The clinician-review action remains open.

### Medication conflict case - AI-patient Scribe

Switch to **Patient view / Sarah Lim**, open **New AI Scribe**, and paste:

```text
AI Assistant: What dose of Atorvastatin are you currently taking?
Patient: I am taking 10 milligrams every night.
AI Assistant: Do you have a previous instruction showing another dose?
Patient: My clinic note may have said 20 milligrams, so I would like the clinic to verify it.
AI Assistant: Have you changed the dose on your own?
Patient: No. I am waiting for the clinic to confirm the correct dose.
```

Expected checks:

- The interaction type is locked to **AI-patient conversation**.
- The output records the patient-reported 10 mg dose without treating it as authoritative.
- The system preserves or detects the discrepancy against the clinician record.
- No new prescription or treatment instruction is generated.

### Duplicate Critical regression case

Run the Latex transcript from Step 4 twice in a rehearsal database.

Expected checks:

- Both consultation entries remain in the Timeline for provenance.
- Only one active **Latex allergy** card appears in Care Glance.
- The repeated fact does not crowd the existing **Penicillin allergy** out of the two-card Critical section.

### Additional Staff note cases

**Unsuccessful follow-up:**

```text
Attempted telephone follow-up at 14:30. Patient was not reached. A second contact attempt is planned for tomorrow morning.
```

**Medication information awaiting verification:**

```text
Patient reported taking Atorvastatin 10 mg nightly. Existing clinician documentation should be reviewed before any medication instruction is changed.
```

Expected checks:

- Each entry is labelled as a Staff note and persists after refresh.
- Staff cannot create or edit a Clinician note.
- Patient and Admin roles cannot use Add note.

## Honest failure handling

- If DeepSeek times out, returns 502, or fails schema/source validation, retain the failure state and explain that the service retries once and then fails closed. Never substitute a fake response in a claimed real-provider demonstration.
- If a stale-version warning appears, reload the latest version. Do not repeatedly overwrite it.
- If Patient view receives internal information, stop the recording and treat it as an RBAC defect.
- If a real secret or non-synthetic patient detail appears on screen, stop and re-record.
