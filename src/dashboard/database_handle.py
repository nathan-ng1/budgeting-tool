"""The Dashboard server's holder for its open Database (Issue #196, ADR-0030).

Handlers talk to the handle as if it were the store - every attribute is
forwarded to the store currently inside it - so the Database can be swapped
for another one while the server keeps running (move, switch, delete). Swapping
is safe because every request already runs under the server's one lock, so no
handler is mid-read when the store changes.
"""


class DatabaseHandle:
    def __init__(self, store):
        self._store = store

    @property
    def store(self):
        return self._store

    @property
    def path(self):
        """Where the current Database file lives."""
        return self._store.path

    def swap(self, new_store):
        """Make `new_store` the Database requests read from, and hand back the
        store it replaced. The caller closes the old one once it is finished
        with its file (e.g. after copying it, or before deleting it)."""
        old, self._store = self._store, new_store
        return old

    def __getattr__(self, name):
        # Only reached for names the handle doesn't define itself.
        return getattr(self._store, name)
