import { useEffect, useState } from "react";

import { downloadBackup, fetchDatabaseLocation } from "../lib/dataApi.js";

// "Your data" (Issue #196, ADR-0030): the bottom of the Settings tab. For now
// it only shows where the Database lives and its size on disk; changing the
// location, Backup and delete land here in later tickets.

/** A byte count as B / KB / MB / GB, one decimal place above bytes. */
function formatSize(bytes) {
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return unit === 0 ? `${value} B` : `${value.toFixed(1)} ${units[unit]}`;
}

/** "Last backed up" text: the local time of the latest Backup, or "Never". */
function formatLastBackedUp(stamp) {
  return stamp ? new Date(stamp).toLocaleString() : "Never";
}

export default function YourData() {
  const [location, setLocation] = useState(null);
  const [error, setError] = useState(null);
  const [backingUp, setBackingUp] = useState(false);

  useEffect(() => {
    const controller = new AbortController();

    fetchDatabaseLocation({ signal: controller.signal })
      .then(setLocation)
      .catch((cause) => {
        if (cause.name !== "AbortError") {
          setError(cause.message);
        }
      });

    return () => controller.abort();
  }, []);

  async function backUp() {
    setBackingUp(true);
    setError(null);
    try {
      await downloadBackup();
      setLocation(await fetchDatabaseLocation());
    } catch (cause) {
      setError(cause.message);
    } finally {
      setBackingUp(false);
    }
  }

  return (
    <section className="card">
      <h3>Your data</h3>
      {error !== null && (
        <p className="state state--error" role="alert">
          {error}
        </p>
      )}
      {location && (
        <dl className="your-data">
          <dt>Database location</dt>
          <dd className="your-data__path">{location.path}</dd>
          <dt>Size on disk</dt>
          <dd>{formatSize(location.size_bytes)}</dd>
          <dt>Last backed up</dt>
          <dd>{formatLastBackedUp(location.last_backed_up)}</dd>
        </dl>
      )}
      <button type="button" className="button" onClick={backUp} disabled={backingUp}>
        Download Backup
      </button>
      <p className="card__note">
        A copy of your Database you can keep somewhere safe. Your browser saves it wherever you choose.
      </p>
    </section>
  );
}
