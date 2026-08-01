import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import path from "node:path";

import { expect, test, type APIRequestContext } from "@playwright/test";

const ownerHeaders = {
  "X-ForgeOps-Actor": "local-owner",
  "X-Trace-ID": "playwright-semantic-owner-trace",
};
const semanticDigests = {
  ontology:
    "sha256:8f4ed5ac34d939a84e74f6a480046b11213d9fe839ed72520a389bf09f4856c9",
  terminology:
    "sha256:7cba32d0e3e759f4c7afe21bb7c56c6cfd3a8ba011d1339798e199ec7f2a1408",
  mapping:
    "sha256:c1880d51b5bbb57840309eeac0524a15de890cf7bdd62587df64c8c49aa8c488",
};

function withKey(key: string) {
  return { ...ownerHeaders, "Idempotency-Key": key };
}

function loadJson(relative: string): Record<string, unknown> {
  return JSON.parse(
    readFileSync(path.resolve(process.cwd(), `../../${relative}`), "utf8"),
  ) as Record<string, unknown>;
}

function digest(content: string): string {
  return `sha256:${createHash("sha256").update(content).digest("hex")}`;
}

function componentManifest(
  packageId: string,
  componentKind: string,
  contentDigest: string,
  capability: string,
): Record<string, unknown> {
  const manifest = structuredClone(
    loadJson("contracts/fds/examples/core-semantics.component.json"),
  );
  const artifact = manifest.artifact as Record<string, unknown>;
  const provenance = manifest.provenance as Record<string, unknown>;
  manifest.packageId = packageId;
  manifest.packageVersion = "1.0.0";
  manifest.componentKind = componentKind;
  manifest.contentDigest = contentDigest;
  manifest.providedCapabilities = [capability];
  manifest.providedNamespaces = [`${packageId}.namespace`];
  artifact.contentDigest = contentDigest;
  artifact.signature = `local-sha256:${contentDigest.replace("sha256:", "")}`;
  artifact.artifactRef = `local://playwright-semantic/${packageId}`;
  provenance.sourceRef = `local://playwright-semantic/${packageId}`;
  provenance.provenanceDigest = digest(`provenance:${packageId}`);
  return manifest;
}

function domainManifest(
  components: Record<string, unknown>[],
): Record<string, unknown> {
  const manifest = structuredClone(
    loadJson("contracts/fds/examples/reference-domain-a.domain.json"),
  );
  const artifact = manifest.artifact as Record<string, unknown>;
  const provenance = manifest.provenance as Record<string, unknown>;
  const domainDigest = digest(
    components.map((item) => String(item.packageId)).join("|"),
  );
  manifest.packageId = "org.forgeops.synthetic.browser-domain";
  manifest.domainNamespace = "org.forgeops.synthetic.browser-domain";
  manifest.contentDigest = domainDigest;
  manifest.providedCapabilities = ["domain.synthetic-browser"];
  manifest.providedNamespaces = ["org.forgeops.synthetic.browser-domain"];
  artifact.contentDigest = domainDigest;
  artifact.signature = `local-sha256:${domainDigest.replace("sha256:", "")}`;
  artifact.artifactRef = "local://playwright-semantic/domain";
  provenance.sourceRef = "local://playwright-semantic/domain";
  provenance.provenanceDigest = digest("browser-domain-provenance");
  manifest.components = components.map((item) => ({
    package: {
      packageId: item.packageId,
      versionConstraint: "==1.0.0",
      expectedKind: "COMPONENT",
      expectedCapability: (item.providedCapabilities as string[])[0],
      contentDigest: item.contentDigest,
    },
    componentKind: item.componentKind,
  }));
  manifest.competencyQuestionRefs = ["urn:forgeops:synthetic:browser:cq-1"];
  return manifest;
}

async function postJson(
  request: APIRequestContext,
  url: string,
  key: string,
  data: Record<string, unknown>,
) {
  const response = await request.post(url, { headers: withKey(key), data });
  expect(response.status(), await response.text()).toBe(201);
  return (await response.json()) as Record<string, unknown>;
}

test("real semantic pages resolve ambiguity, compile fixed context, validate grounding, and enforce Viewer scope", async ({
  page,
}) => {
  const organization = await postJson(
    page.request,
    "/v1/organizations",
    "browser-semantic-organization",
    { name: "Synthetic Semantic Lab", slug: "synthetic-semantic-lab" },
  );
  const organizationId = String(organization.organizationId);
  const workspace = await postJson(
    page.request,
    `/v1/organizations/${organizationId}/workspaces`,
    "browser-semantic-workspace",
    { name: "Context Workspace", slug: "context-workspace" },
  );
  const project = await postJson(
    page.request,
    `/v1/workspaces/${String(workspace.workspaceId)}/projects`,
    "browser-semantic-project",
    {
      name: "Semantic Evidence",
      slug: "semantic-evidence",
      description: "LOCAL_SYNTHETIC browser semantic evidence",
    },
  );
  const projectId = String(project.projectId);
  const activated = await page.request.post(
    `/v1/projects/${projectId}:activate`,
    {
      headers: ownerHeaders,
      data: { expectedVersion: project.version },
    },
  );
  expect(activated.status()).toBe(200);

  const ontology = loadJson(
    "contracts/semantic/examples/neutral-ontology-v1.json",
  );
  const terminology = loadJson(
    "contracts/semantic/examples/neutral-terminology-v1.json",
  );
  const mapping = loadJson(
    "contracts/semantic/examples/neutral-mapping-v1.json",
  );
  const knowledgeContent = readFileSync(
    path.resolve(
      process.cwd(),
      "../../contracts/semantic/examples/neutral-knowledge-usable.txt",
    ),
    "utf8",
  );
  const componentInputs = [
    {
      key: "ontology",
      manifest: componentManifest(
        "org.forgeops.synthetic.browser-ontology",
        "ONTOLOGY",
        semanticDigests.ontology,
        "semantic.browser-ontology",
      ),
      definition: ontology,
    },
    {
      key: "terminology",
      manifest: componentManifest(
        "org.forgeops.synthetic.browser-terminology",
        "TERMINOLOGY",
        semanticDigests.terminology,
        "semantic.browser-terminology",
      ),
      definition: terminology,
    },
    {
      key: "mapping",
      manifest: componentManifest(
        "org.forgeops.synthetic.browser-mapping",
        "DATA_MAPPING",
        semanticDigests.mapping,
        "semantic.browser-mapping",
      ),
      definition: mapping,
    },
  ];
  const knowledgeManifest = componentManifest(
    "org.forgeops.synthetic.browser-knowledge",
    "KNOWLEDGE",
    digest(knowledgeContent),
    "knowledge.browser-reference",
  );
  const allManifests = [
    ...componentInputs.map((item) => item.manifest),
    knowledgeManifest,
  ];
  const registered = new Map<string, Record<string, unknown>>();
  for (const manifest of allManifests) {
    const item = await postJson(
      page.request,
      "/v1/fds/package-versions",
      `browser-semantic-fds-${String(manifest.packageId)}`,
      { manifest },
    );
    registered.set(String(manifest.packageId), item);
  }
  const domain = await postJson(
    page.request,
    "/v1/fds/package-versions",
    "browser-semantic-fds-domain",
    { manifest: domainManifest(allManifests) },
  );
  const installation = await postJson(
    page.request,
    `/v1/organizations/${organizationId}/domain-installations`,
    "browser-semantic-installation",
    {
      rootPackageVersionId: domain.packageVersionId,
      targetVersions: {
        platform: "0.1.0",
        fds: "0.1.0",
        scenarioSdk: "0.1.0",
      },
      includeOptional: false,
    },
  );
  await postJson(
    page.request,
    `/v1/projects/${projectId}/domain-locks`,
    "browser-semantic-domain-lock",
    {
      installationId: installation.installationId,
      purpose: "browser deterministic semantic evidence",
    },
  );

  for (const input of componentInputs.filter(
    (item) => item.key !== "terminology",
  )) {
    const registeredPackage = registered.get(String(input.manifest.packageId));
    if (!registeredPackage)
      throw new Error("registered semantic component missing");
    const payload = await postJson(
      page.request,
      "/v1/semantic/payloads",
      `browser-semantic-payload-${input.key}`,
      {
        packageVersionId: registeredPackage.packageVersionId,
        definition: input.definition,
      },
    );
    const published = await page.request.post(
      `/v1/semantic/payloads/${String(payload.semanticPayloadId)}:publish`,
      {
        headers: {
          ...withKey(`browser-publish-${input.key}`),
          "If-Match": "1",
        },
        data: { reason: "browser local synthetic publish" },
      },
    );
    expect(published.status()).toBe(200);
  }

  const knowledgeAsset = await postJson(
    page.request,
    `/v1/organizations/${organizationId}/knowledge-assets`,
    "browser-knowledge-asset",
    {
      title: "Browser synthetic reference",
      description: "Untrusted local-synthetic content for Context E2E",
      assetType: "TEXT",
      language: "en",
      owner: "local-owner",
      reviewer: "local-reviewer",
    },
  );
  const knowledgePackage = registered.get(String(knowledgeManifest.packageId));
  if (!knowledgePackage)
    throw new Error("registered knowledge component missing");
  const knowledgeVersion = await postJson(
    page.request,
    `/v1/knowledge-assets/${String(knowledgeAsset.assetId)}/versions`,
    "browser-knowledge-version",
    {
      packageVersionId: knowledgePackage.packageVersionId,
      versionLabel: "1.0.0",
      title: "Browser synthetic reference v1",
      description: "Immutable browser context content",
      sourceRef: (knowledgeManifest.provenance as Record<string, unknown>)
        .sourceRef,
      provenanceDigest: (
        knowledgeManifest.provenance as Record<string, unknown>
      ).provenanceDigest,
      licenseId: "LOCAL-SYNTHETIC-ONLY",
      licenseTerms: "Local synthetic engineering only.",
      contentClassification: "SYNTHETIC_INTERNAL",
      allowedPurposes: ["OWNER_REVIEW"],
      validFrom: "2025-01-01T00:00:00Z",
      validTo: null,
      contentType: "text/plain",
      content: knowledgeContent,
    },
  );
  const publishedKnowledge = await page.request.post(
    `/v1/knowledge-versions/${String(knowledgeVersion.knowledgeVersionId)}:publish`,
    {
      headers: { ...withKey("browser-publish-knowledge"), "If-Match": "1" },
      data: { reason: "browser local synthetic publish" },
    },
  );
  expect(publishedKnowledge.status()).toBe(200);

  await page.goto("/");
  await page.getByLabel("组织", { exact: true }).selectOption(organizationId);
  await page
    .getByLabel("工作空间", { exact: true })
    .selectOption(String(workspace.workspaceId));
  await page.getByRole("button", { name: "语义与知识" }).click();
  await expect(page.getByTestId("semantic-knowledge-page")).toBeVisible();
  const terminologyPackage = registered.get(
    "org.forgeops.synthetic.browser-terminology",
  );
  if (!terminologyPackage) throw new Error("terminology component missing");
  await page
    .getByLabel("精确 Registry Component version")
    .selectOption(String(terminologyPackage.packageVersionId));
  await page.getByLabel("严格 payload JSON").fill(JSON.stringify(terminology));
  await page.getByRole("button", { name: "校验并登记" }).click();
  await expect(page.getByText("完成摘要校验", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "发布本地合成版本" }).click();
  await expect(
    page.getByText("语义版本已发布", { exact: false }),
  ).toBeVisible();
  await expect(page.getByText("NOT_ENTERPRISE_VERIFIED")).toBeVisible();

  await page.getByRole("button", { name: "项目中心" }).click();
  await page.getByRole("button", { name: "上下文" }).click();
  await expect(page.getByTestId("project-context-page")).toBeVisible();
  await expect(page.getByText("HEALTHY_FOR_SELECTION")).toBeVisible();
  await page.getByLabel("术语").fill("共享词");
  await page.getByRole("button", { name: "解析术语" }).click();
  await expect(page.locator(".query-result")).toContainText("AMBIGUOUS");
  await expect(page.locator(".query-result article")).toHaveCount(2);
  await page.getByLabel("术语").fill("目录项");
  await page.getByRole("button", { name: "解析术语" }).click();
  await expect(page.locator(".query-result")).toContainText("RESOLVED");

  await page
    .getByRole("button", { name: "编译不可变 ContextManifest" })
    .click();
  await expect(page.getByTestId("context-manifest-preview")).toBeVisible();
  await expect(page.getByTestId("context-manifest-preview")).toContainText(
    "Canonical digest",
  );
  await page.getByLabel("Candidate JSON").fill(
    JSON.stringify({
      entityRefs: ["urn:forgeops:synthetic:catalog:missing"],
      relationAssertions: [],
      mappingRefs: [],
      knowledgeCitations: ["00000000-0000-0000-0000-000000000001"],
      declaredConstraintIds: [],
    }),
  );
  await page.getByRole("button", { name: "运行结构校验" }).click();
  await expect(page.locator(".grounding-result")).toContainText("INVALID");
  await expect(page.locator(".grounding-result")).toContainText(
    "modelCalled = false",
  );

  const viewerGrant = await page.request.post(
    `/v1/organizations/${organizationId}/memberships`,
    {
      headers: withKey("browser-semantic-viewer"),
      data: {
        principalRef: "local-viewer",
        scopeType: "PROJECT",
        scopeId: projectId,
        role: "PROJECT_VIEWER",
      },
    },
  );
  expect(viewerGrant.status()).toBe(201);
  await page.getByLabel("演示角色").selectOption("local-viewer");
  await page.getByRole("button", { name: "上下文" }).click();
  await expect(page.getByTestId("project-context-page")).toBeVisible();
  await expect(page.getByRole("button", { name: "解析术语" })).toBeEnabled();
  await page.getByLabel("演示角色").selectOption("local-outsider");
  await expect(
    page.getByRole("heading", { name: "Semantic Evidence" }),
  ).toHaveCount(0);
});
