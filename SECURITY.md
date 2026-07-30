# Security policy

ForgeOps is advisory-only. This repository contains no production write adapter, enterprise credential, real industrial data, or control-system integration.

## Non-negotiable boundary

- DEV/TEST/INT use a local `MockActionAdapter` only for recording an unexecuted proposal.
- PREPROD/PROD are hard-bound to `DenyAllActionAdapter`.
- The application has no MES/ERP/WMS/LIMS/CMMS write client, RPA path, or PLC/DCS/interlock control API.
- Unknown environments, permissions, package code, manifests, or action adapters fail closed.
- External model calls are disabled. Deterministic template output is the only local fallback.

Do not report a vulnerability with real credentials or production data in an issue. Enterprise reporting and response ownership remain TBD; stop deployment if a serious issue is discovered.
