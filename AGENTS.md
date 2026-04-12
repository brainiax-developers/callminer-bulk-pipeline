# AGENTS.md

## Working style
- For non-trivial tasks, inspect the repository and relevant docs before making changes.
- Do not start coding immediately on complex tasks.
- Produce a short implementation plan before editing files.
- Prefer minimal, reviewable changes over broad refactors.

## Scope
- The current task is PPLNS-7739 only.
- Background docs are in `.docs/callminer/`.
- Read `.docs/callminer/README.md` first, then review the PDF and Jira XML files as needed.
- Use the current repository to understand the existing CallMiner implementation and Terraform structure.
- Do not implement unrelated Bulk API tickets unless a tiny shared abstraction is required.

## Language and implementation choice
- First determine whether PPLNS-7739 should:
  1. extend the current implementation, or
  2. be added as a new component/service within this repo.
- Explain that decision before coding.
- Unless the repository strongly dictates otherwise, prefer Python for the new Bulk API scheduler Lambda because this task is primarily API integration, auth, scheduling, config handling, and rerun validation.
- If choosing a different language, explain why.

## Functional expectations for PPLNS-7739
Implement a Lambda/service that:
- authenticates with the CallMiner identity/token endpoint
- retrieves existing export jobs
- finds an existing job by configured name
- creates the job if it does not exist
- updates the job if it already exists
- supports reruns for specific time periods
- restricts reruns so they can only change permitted time-period fields, not protected job configuration like storage target or other sensitive settings

## Terraform and config
- Reuse existing Terraform, Lambda, logging, configuration, and secrets conventions from the repo where appropriate.
- Keep infrastructure changes isolated and easy to review.
- Do not hardcode secrets.
- Keep sensitive values out of logs.

## Testing
- Add or update automated tests for new logic.
- Reuse existing test conventions where possible.
- If some validation cannot be run locally, say exactly what was and was not verified.

## Final output expectations
At the end of the task, provide:
- a summary of repository areas inspected
- the implementation decision (new component vs modify existing)
- files changed
- tests/commands run
- assumptions and follow-up items