import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { App } from "./App";
import { ApiError, describeApiError } from "./project-api";

describe("Project Center shell", () => {
  it("starts in a truthful persisted-state loading view", () => {
    const markup = renderToStaticMarkup(<App />);
    expect(markup).toContain("Opening Project Center");
    expect(markup).toContain("LOCAL SYNTHETIC");
    expect(markup).not.toContain("Enterprise identity connected");
  });

  it("maps concealed and concurrent failures to actionable UI states", () => {
    expect(
      describeApiError(new ApiError(404, "RESOURCE_NOT_FOUND", "hidden")),
    ).toMatch(/outside your scope/);
    expect(
      describeApiError(new ApiError(409, "CONCURRENCY_CONFLICT", "stale")),
    ).toMatch(/Refresh/);
  });
});
