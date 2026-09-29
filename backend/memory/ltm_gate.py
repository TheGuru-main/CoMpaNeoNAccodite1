"""Accodite LTM Vault Gate — RBAC wrapper."""
from org.roles import can_read_ltm, can_write_ltm

class LTMGate:
    def __init__(self, cache, membership_lookup):
        self._cache = cache
        self._lookup = membership_lookup

    def read(self, *, user_id, organization_id, query):
        role = self._role_for(user_id, organization_id)
        if not can_read_ltm(role):
            raise PermissionError(f"role '{role}' may not read LTM vault")
        return self._cache.get_ltm(query)

    def write(self, *, user_id, organization_id, query, data):
        role = self._role_for(user_id, organization_id)
        if not can_write_ltm(role):
            raise PermissionError(f"role '{role}' may not write LTM vault")
        return self._cache.set_ltm(query, data)

    def _role_for(self, user_id, organization_id):
        if organization_id is None:
            return "owner"
        m = self._lookup(user_id, organization_id)
        if m is None:
            return "viewer"
        return m.role or "viewer"
