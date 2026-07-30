# ADR-0002: Platform Core and Scenario SDK separation

- Status: `ACCEPTED_FOR_LOCAL_SYNTHETIC_ENGINEERING`
- Maps to: production ADR-0009/0010/0012

The fixed dependency direction is `scenario package -> scenario_sdk -> platform_contracts`. Platform Core and SDK contain only generic concepts and never import reference packages. Reference fixtures are data-only; executable code is not loaded by the API process.
