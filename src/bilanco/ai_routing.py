"""Short, audited model route with one shared physical-call budget."""

from dataclasses import replace

from .ai import AIError, Codex


class RoutedCodex:
    def __init__(self, settings, audit_dir, fallback_model, *, factory=Codex):
        self.settings = settings
        self.primary = factory(settings, audit_dir / "primary")
        self.fallback = factory(
            replace(settings, codex_model=fallback_model), audit_dir / "fallback"
        )
        self.routes = []
        self.last_model = settings.codex_model

    @property
    def calls(self):
        return self.primary.calls + self.fallback.calls

    @property
    def receipts(self):
        return [*self.primary.receipts, *self.fallback.receipts]

    def _call(self, client, task, packet, schema, discovery, reason):
        if self.calls >= self.settings.max_ai_calls:
            raise AIError("Codex ortak çağrı bütçesi doldu.")
        route = {
            "sequence": len(self.routes) + 1,
            "task": task,
            "model": client.settings.codex_model,
            "reason": reason,
            "status": "failed",
        }
        self.routes.append(route)
        self.last_model = client.settings.codex_model
        result = client.ask(task, packet, schema, discovery=discovery)
        route["status"] = "completed"
        return result

    def ask(self, task, packet, schema, *, discovery=False):
        try:
            return self._call(self.primary, task, packet, schema, discovery, "primary")
        except AIError:
            if self.primary.settings.codex_model == self.fallback.settings.codex_model:
                raise
            return self._call(self.fallback, task, packet, schema, discovery, "primary_call_failed")

    def escalate(
        self,
        task,
        packet,
        schema,
        *,
        from_model=None,
        discovery=False,
        reason="evidence_validation_failed",
    ):
        if (from_model or self.last_model) == self.fallback.settings.codex_model:
            return None
        return self._call(self.fallback, task, packet, schema, discovery, reason)
