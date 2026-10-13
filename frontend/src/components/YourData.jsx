import { useEffect, useState } from "react";

import { fetchDatabaseLocation } from "../lib/dataApi.js";
import ChangeLocation from "./ChangeLocation.jsx";

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

export default function YourData() {
  const [location, setLocation] = useState(null);
  const [error, setError] = useState(null);

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
        </dl>
      )}
      <ChangeLocation />
    </section>
  );
}
