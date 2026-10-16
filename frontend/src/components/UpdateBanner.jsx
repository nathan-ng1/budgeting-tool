// "A new Version is available" (Issue #251, decision S7). The launcher found it
// on its daily check and handed it to the backend; this only shows it. Applying
// an update is manual: the Buyer re-runs the installer.
export default function UpdateBanner({ version }) {
  if (!version) {
    return null;
  }

  return (
    <section className="update-banner" role="status" aria-label="Update available">
      <p>
        <strong>Version {version} is available.</strong> To update, re-run the installer you downloaded.
      </p>
    </section>
  );
}
