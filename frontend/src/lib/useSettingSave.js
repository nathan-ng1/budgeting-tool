import { useState } from "react";

import { saveSettings } from "./settingsApi.js";

// The state every Settings card shares (ADR-0027): the choice being edited, an
// explicit save of that one setting, and the server's refusal if it gives one.
// `field` is the setting's name in the settings payload, `saved` its current
// saved value, and `onSaved` receives the server's answer (every setting).
export function useSettingSave(field, saved, onSaved) {
  const [selected, setSelected] = useState(saved);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      onSaved(await saveSettings({ [field]: selected }));
    } catch (cause) {
      setError(cause.message);
    } finally {
      setSaving(false);
    }
  }

  return { selected, setSelected, saving, error, save, unchanged: selected === saved };
}
