import { useEffect, useState } from "react";

import {
  fetchPlatformState,
  type Installation,
  type PlatformStatus,
} from "./status";
import "./styles.css";

type LoadState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; status: PlatformStatus; installations: Installation[] };

export function App() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    let current = true;
    fetchPlatformState()
      .then(({ status, installations }) => {
        if (current) setState({ kind: "ready", status, installations });
      })
      .catch((error: unknown) => {
        if (current) {
          setState({
            kind: "error",
            message: error instanceof Error ? error.message : "Unknown error",
          });
        }
      });
    return () => {
      current = false;
    };
  }, []);

  return (
    <main>
      <header>
        <p className="eyebrow">FORGEOPS / ENGINEERING BASELINE</p>
        <h1>Platform state, not a product simulation.</h1>
        <p className="lede">
          This page reads persisted API state. It is limited to local synthetic
          contracts and carries no enterprise or business approval.
        </p>
      </header>

      {state.kind === "loading" && (
        <section className="panel">Reading platform state…</section>
      )}
      {state.kind === "error" && (
        <section className="panel error">
          <h2>API unavailable</h2>
          <p>{state.message}</p>
        </section>
      )}
      {state.kind === "ready" && (
        <>
          <section className="boundary" aria-label="safety boundary">
            <Status label="Scope" value={state.status.scope} />
            <Status label="Data" value={state.status.dataMode} />
            <Status label="Action adapter" value={state.status.actionAdapter} />
            <Status
              label="Enterprise approval"
              value={state.status.enterpriseApproval}
              warning
            />
          </section>
          <section className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">PERSISTED REGISTRY</p>
                <h2>Scenario package installations</h2>
              </div>
              <span>{state.installations.length} records</span>
            </div>
            {state.installations.length === 0 ? (
              <p>
                No packages installed. Installation never implies permission,
                release, or enablement.
              </p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Package</th>
                    <th>Version</th>
                    <th>State</th>
                    <th>Digest</th>
                  </tr>
                </thead>
                <tbody>
                  {state.installations.map((item) => (
                    <tr key={item.installationId}>
                      <td>{item.packageId}</td>
                      <td>{item.packageVersion}</td>
                      <td>
                        <code>{item.state}</code>
                      </td>
                      <td className="digest">{item.contentDigest}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </>
      )}
    </main>
  );
}

function Status({
  label,
  value,
  warning = false,
}: {
  label: string;
  value: string;
  warning?: boolean;
}) {
  return (
    <article className={warning ? "status warning" : "status"}>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}
