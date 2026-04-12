# CallMiner Bulk API migration context

This folder contains background material for the CallMiner Bulk API migration.

## Current implementation
- `Current Callminer Implementation.pdf` describes the current Eureka/API-based CallMiner ingestion and transfer flow.

## Jira context
- `PPLNS-7817.xml` = Epic: Migrate to Call Miner Bulk Export API
- `PPLNS-7737.xml` = Configure AWS key/secret rotation for CallMiner BulkAPI storage target
- `PPLNS-7738.xml` = Configure lakehouse-copy-file job to unpack/copy export files from holding to landing
- `PPLNS-7739.xml` = Create a lambda function to schedule Callminer BulkAPI export jobs
- `PPLNS-7740.xml` = Create a Callminer ingestion job for the new BulkAPI

## Current task
Codex is being asked to work specifically on `PPLNS-7739`.

## Intent
Codex must:
1. understand the current CallMiner implementation from the existing repo and this documentation
2. determine whether PPLNS-7739 should be implemented as a new component/service or as a modification to the current implementation
3. produce a plan before coding
4. then implement only PPLNS-7739