import { useDateFormat } from "../lib/settings.jsx";

// The Version History view (ADR-0029): every Version newest-first with its
// release date and plain-text changes, the running Version marked "Current".
// `history` is null when the changelog couldn't be read; the Version under the
// title is App's and stays put either way. A running Version with no entry
// just leaves every row unmarked.
export default function VersionHistory({ history, currentVersion, onBack }) {
  const { dayMonthYear } = useDateFormat();

  return (
    <section className="version-history">
      <button type="button" className="link-button" onClick={onBack}>
        Back to Dashboard
      </button>

      <h2>Version history</h2>

      {history === null ? (
        <p className="state state--page">Version history isn&apos;t available</p>
      ) : (
        <ol className="version-history__list">
          {history.map(({ version, date, entries }) => (
            <li key={version} className="card version-history__version" aria-label={`v${version}`}>
              <div className="version-history__head">
                <h3>v{version}</h3>
                <span className="version-history__date">{dayMonthYear(date)}</span>
                {version === currentVersion && <span className="version-history__current">Current</span>}
              </div>
              <ul className="version-history__entries">
                {entries.map((entry) => (
                  <li key={entry}>{entry}</li>
                ))}
              </ul>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
