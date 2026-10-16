// The Retail launcher's endpoints (Issue #249). `active` says whether the
// launcher is running this Dashboard: only then are there a startup notice and
// a Quit to show. Run straight from a clone (the Collaborator Edition) it is
// false, and Quit does not exist.

export async function fetchLauncher({ signal } = {}) {
  const response = await fetch("/api/launcher", { signal });

  if (!response.ok) {
    throw new Error(`The Dashboard backend returned ${response.status} for the launcher.`);
  }

  return response.json();
}

// Stops the server: the page stops answering as soon as this returns.
export async function quitApp() {
  const response = await fetch("/api/quit", { method: "POST" });

  if (!response.ok) {
    throw new Error(`The Dashboard backend returned ${response.status} when quitting.`);
  }
}
