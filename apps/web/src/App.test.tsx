import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { App } from "./App";
import { ApiError, describeApiError } from "./project-api";

describe("Project Center shell", () => {
  it("starts in a truthful persisted-state loading view", () => {
    const markup = renderToStaticMarkup(<App />);
    expect(markup).toContain("正在打开项目中心");
    expect(markup).toContain("本地合成环境");
    expect(markup).not.toContain("企业身份已连接");
  });

  it("maps concealed and concurrent failures to actionable UI states", () => {
    expect(
      describeApiError(new ApiError(404, "RESOURCE_NOT_FOUND", "hidden")),
    ).toMatch(/没有查看权限/);
    expect(
      describeApiError(new ApiError(409, "CONCURRENCY_CONFLICT", "stale")),
    ).toMatch(/刷新/);
  });
});
