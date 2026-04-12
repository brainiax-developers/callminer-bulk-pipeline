# CallMiner fixes (PPLNS-7142, PPLNS-7143) – 2025-11-03

Summary of changes applied to address production timeout/failure signalling and null threshold rerun issue.

- Step Functions failure semantics
  - Catch blocks for Landing, Events, Transfer now use `States.ALL` and capture error to `$.error`.
  - Added Pass states to annotate which state failed (Landing/Events/Transfer) to `$.failedState`.
  - SNS message now includes actual `Error` and `Cause` and failed state name.
  - Execution transitions to a `Fail` state after notification so the overall status is FAILED.

- Rerun lambda null-threshold guard
  - `src/python/CallMinerLandingRerunLambda.py` exits early (status `skipped_no_threshold`) if CloudWatch anomaly band does not provide a threshold.
  - Emits CloudWatch custom metric `CallMiner/Rerun: MissingThreshold=1` and optionally publishes to SNS (`MISSING_THRESHOLD_SNS_ARN`) for visibility when skipping.
  - Prevents passing `null` threshold into Landing Lambda (previously caused JsResultException).

Deployment notes
- Apply Terraform in each environment to update the state machine.
- Redeploy the rerun Lambda package via your standard CI/CD pipeline.

Validation checklist
- Rerun without threshold: lambda should skip triggering the state machine.
- Any failed task state: OpsGenie alert contains state name and error, Step Function ends as FAILED.
- Normal runs unaffected and end as Succeeded.


Summary
- Prevent downstream false-success executions by capturing task errors, notifying via SNS with context, and terminating the Step Function with a Fail state.
- Prevent the rerun Lambda from invoking the workflow when CloudWatch does not provide an anomaly threshold (avoids null threshold errors).

What changed
1) Step Functions (tf/modules/step_functions/step_functions.tf)
   - Each Task (Landing, Events, Transfer) now catches all failures ("ErrorEquals": ["States.ALL"]) and writes the error object to $.error (ResultPath).
   - Added small Pass states to mark which state failed (Mark_Landing_Failed, Mark_Events_Failed, Mark_Transfer_Failed). These set $.failedState so alerts identify the failing state.
   - SNS publish state now formats the message using States.Format to include $.failedState, $.error.Error and $.error.Cause (Message.$).
   - After publishing the SNS message the workflow transitions to an explicit FailState which sets the state machine Error and Cause from $.error, ensuring the execution is marked FAILED.
   - This replaces prior behavior where an SNS publish ended the execution (End: true) and left the overall run as Succeeded.

2) Rerun Lambda (src/python/CallMinerLandingRerunLambda.py)
   - Added an early-return path when the anomaly band / threshold cannot be derived from CloudWatch. The function now logs and returns status "skipped_no_threshold" and does not start a Step Function execution.
   - This avoids passing a null threshold into downstream Lambdas which previously caused JsResultException and spurious failures.

Files modified
- tf/modules/step_functions/step_functions.tf
- src/python/CallMinerLandingRerunLambda.py

Behavioral impact
- Failures in Landing/Events/Transfer will:
  - Be caught and captured into $.error
  - Produce an OpsGenie/SNS notification with the failing state name and real error/cause
  - Terminate the Step Function execution as FAILED (useful for monitoring/alerting and CI gating)
- Rerun lambda invocations without a derived threshold will be safe no-ops (skipped) instead of triggering failing workflows.

Testing / Validation
- Induce a controlled failure in each task to verify:
  - SNS message reads: "Callminer <STATE> failed: <Error> - <Cause>"
  - State machine ends with FAILED status and correct Error/Cause
- Invoke rerun lambda where CloudWatch returns no anomaly band and verify:
  - Lambda returns status "skipped_no_threshold"
  - No Step Function execution is started
- Run normal workflows to confirm no regression in successful paths

Deployment
- Terraform: plan/apply tf changes (tf/modules/step_functions/step_functions.tf) in your environment(s)
- Lambda: redeploy updated CallMinerLandingRerunLambda.py via your CI/CD pipeline

Notes and recommendations
- The Catchers now use States.ALL; this ensures any unforeseen failure types are handled uniformly.
- SNS messages include the raw $.error.Cause which can be large or JSON. Consider truncation or extracting specific fields if message size is a concern.
- If desired, add the failing state name into monitoring dashboards or metrics to enable quicker triage.
- Rollback: revert the Step Functions definition and redeploy if SNS behavior must be reverted quickly.

References
- PPLNS-7142: ensure SFN marks failed and sends useful alert
- PPLNS-7143: avoid null threshold being passed from rerun lambda
