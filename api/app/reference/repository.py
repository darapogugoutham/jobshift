from typing import Protocol

from app.core.models import ReferenceArtifact


class ReferenceRepository(Protocol):
    """Read metadata about releases and artifacts; no real occupational source is bundled."""

    def list_artifacts(self, source: str | None = None) -> list[ReferenceArtifact]: ...
    def get_release(self, source: str, release: str) -> list[ReferenceArtifact]: ...
