import { describe, expect, it } from "vitest";

import { assertPlatformStatus } from "./status";

describe("platform status contract", () => {
  it("accepts only the local synthetic advisory boundary", () => {
    const result = assertPlatformStatus({
      environment: "DEV",
      scope: "LOCAL_SYNTHETIC_ENGINEERING",
      advisoryMode: true,
      dataMode: "SYNTHETIC_ONLY",
      externalModelEnabled: false,
      runtimePluginsEnabled: false,
      actionAdapter: "MOCK",
      sdkVersion: "1.0.0",
      enterpriseApproval: "NOT_GRANTED",
      identityMode: "LOCAL_SYNTHETIC",
      enterpriseIdentityConnected: false,
      projectScopeEnabled: true,
    });
    expect(result.advisoryMode).toBe(true);
  });

  it("rejects any production approval claim", () => {
    expect(() =>
      assertPlatformStatus({
        scope: "LOCAL_SYNTHETIC_ENGINEERING",
        advisoryMode: true,
        dataMode: "SYNTHETIC_ONLY",
        externalModelEnabled: false,
        runtimePluginsEnabled: false,
        enterpriseApproval: "GRANTED",
        identityMode: "LOCAL_SYNTHETIC",
        enterpriseIdentityConnected: false,
        projectScopeEnabled: true,
      }),
    ).toThrow(/unsafe or incompatible/);
  });
});
