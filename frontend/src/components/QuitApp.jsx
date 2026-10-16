import { useState } from "react";

import { quitApp } from "../lib/launcherApi.js";

// "Quit" in Settings (Issue #249, decision S4): stops the server the launcher
// started, since the app has no window or tray icon to close. Renders nothing
// unless the launcher is running this Dashboard.
export default function QuitApp({ active }) {
  const [quitting, setQuitting] = useState(false);
  const [stopped, setStopped] = useState(false);
  const [error, setError] = useState(null);

  if (!active) {
    return null;
  }

  async function quit() {
    setError(null);
    setQuitting(true);
    try {
      await quitApp();
      setStopped(true);
    } catch (cause) {
      setError(cause.message);
      setQuitting(false);
    }
  }

  return (
    <section className="card">
      <h3>Quit</h3>
      {stopped ? (
        <p role="status">The app has stopped. You can close this tab.</p>
      ) : (
        <>
          <p className="card__note">
            Stops the app running in the background. Open it again from its icon whenever you like.
          </p>
          <div className="your-data__actions">
            <button type="button" className="button" disabled={quitting} onClick={quit}>
              {quitting ? "Quitting…" : "Quit"}
            </button>
          </div>
        </>
      )}
      {error !== null && (
        <p className="state state--error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
