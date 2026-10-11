import { useState } from "react";

import { saveSettings } from "./settingsApi.js";

// The state the Display Settings tile holds (ADR-0027): a draft of every
// setting being edited, one explicit save of whichever ones changed, and the
// server's refusal if it gives one. `saved` is the settings payload as the
// server last answered; `onSaved` receives the server's answer (every setting).
export function useSettingsSave(saved, onSaved) {
  const [draft, setDraft] = useState(saved);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const changes = Object.fromEntries(Object.keys(saved).filter((field) => draft[field] !== saved[field]).map((field) => [field, draft[field]]));
  const changeCount = Object.keys(changes).length;

  function set(field) {
    return (value) => setDraft((previous) => ({ ...previous, [field]: value }));
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      onSaved(await saveSettings(changes));
    } catch (cause) {
      setError(cause.message);
    } finally {
      setSaving(false);
    }
  }

  return { draft, set, saving, error, save, changeCount };
}
