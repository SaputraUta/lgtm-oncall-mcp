"""VCS adapters (Bitbucket Cloud, GitHub) implementing a common interface."""

from .base import Commit, PRResult, PipelineResult, TagInfo, VCSAdapter

__all__ = ["VCSAdapter", "TagInfo", "Commit", "PipelineResult", "PRResult"]
