import { useState } from "react";

// Remembered per browser origin, which includes the port: a launch on a new
// port shows the notice again, which is when "open it from its icon, not a
// bookmark" matters most.
const STORAGE_KEY = "startupNoticeDismissed";

function wasDismissed() {
  try {
    return localStorage.getItem(STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

function rememberDismissed() {
  try {
    localStorage.setItem(STORAGE_KEY, "true");
  } catch {
    // Storage blocked: the notice just comes back next time.
  }
}

// What a Buyer needs to know about an app with no window of its own (Issue
// #249, decisions S10 and S16). Shown only when the launcher is running the
// Dashboard; the Collaborator Edition's terminal-launched Dashboard has no use
// for it.
export default function StartupNotice({ active }) {
  const [dismissed, setDismissed] = useState(wasDismissed);

  if (!active || dismissed) {
    return null;
  }

  function dismiss() {
    rememberDismissed();
    setDismissed(true);
  }

  return (
    <section className="startup-notice" aria-label="Before you start">
      <div className="startup-notice__text">
        <p>
          <strong>This app keeps running in the background</strong> after you close this tab. When you are finished, go
          to Settings and choose <strong>Quit</strong>.
        </p>
        <p>
          To open it again, use the app&rsquo;s icon rather than a bookmark: the address can change from one launch to
          the next.
        </p>
      </div>
      <button type="button" className="button" onClick={dismiss}>
        Got it
      </button>
    </section>
  );
}
