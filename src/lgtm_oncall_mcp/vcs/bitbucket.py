"""Bitbucket Cloud adapter."""

from __future__ import annotations

import httpx

from ..config import BitbucketConfig
from .base import Commit, PipelineResult, PRResult, TagInfo
from .util import sort_tags_newest_first


class BitbucketAdapter:
    def __init__(self, cfg: BitbucketConfig):
        self._cfg = cfg
        self._repo = f"{cfg.workspace}/{cfg.repo_slug}"
        self._client = httpx.Client(
            base_url="https://api.bitbucket.org",
            auth=(cfg.email, cfg.api_token),
            timeout=20.0,
        )

    def list_tags(self, limit: int = 50) -> list[TagInfo]:
        # We deliberately do NOT use `?sort=-target.date` here. That sorts by
        # the underlying COMMIT date, which gives wrong answers whenever a new
        # tag is created at an older commit (re-deploy of a previous version,
        # hotfix branch tagged from a side commit, etc.). Instead, we fetch a
        # generous page and sort by tag NAME (semver) in Python.
        r = self._client.get(
            f"/2.0/repositories/{self._repo}/refs/tags",
            params={"pagelen": 100},
        )
        r.raise_for_status()
        out: list[TagInfo] = []
        for t in r.json().get("values", []):
            target = t.get("target", {})
            out.append(
                TagInfo(
                    tag=t["name"],
                    sha=target.get("hash", "")[:12],
                    date=target.get("date", ""),
                    message=(target.get("message") or "").strip().split("\n")[0],
                )
            )
        return sort_tags_newest_first(out)[:limit]

    def get_commit_diff(self, sha: str, max_chars: int = 50_000) -> str:
        r = self._client.get(f"/2.0/repositories/{self._repo}/diff/{sha}")
        r.raise_for_status()
        text = r.text
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + f"\n... [truncated, full diff is {len(text)} chars]"

    def get_file_commits(self, path: str, limit: int = 10) -> list[Commit]:
        r = self._client.get(
            f"/2.0/repositories/{self._repo}/commits",
            params={"path": path, "pagelen": min(limit, 50)},
        )
        r.raise_for_status()
        return [
            Commit(
                sha=c["hash"][:12],
                date=c.get("date", ""),
                message=(c.get("message") or "").strip().split("\n")[0],
            )
            for c in r.json().get("values", [])[:limit]
        ]

    def trigger_deploy(self, env: str, ref: str) -> PipelineResult:
        """Rerun the Bitbucket pipeline for an existing tag.

        Bitbucket triggers deploys by ref name (tag or branch). For rollback,
        pass the previous good tag here — pipelines.yml is responsible for
        dispatching the deploy to the matching env.
        """
        r = self._client.post(
            f"/2.0/repositories/{self._repo}/pipelines/",
            json={
                "target": {
                    "type": "pipeline_ref_target",
                    "ref_type": "tag",
                    "ref_name": ref,
                }
            },
        )
        r.raise_for_status()
        j = r.json()
        return PipelineResult(
            pipeline_id=j.get("uuid", "").strip("{}"),
            build_number=j.get("build_number"),
            url=j.get("links", {}).get("html", {}).get("href", ""),
            state=j.get("state", {}).get("name", ""),
        )

    def open_pr(
        self,
        branch_name: str,
        file_path: str,
        new_content: str,
        title: str,
        body: str,
        base_branch: str = "main",
    ) -> PRResult:
        # Get base branch HEAD sha
        r = self._client.get(
            f"/2.0/repositories/{self._repo}/refs/branches/{base_branch}"
        )
        r.raise_for_status()
        base_sha = r.json()["target"]["hash"]

        # Create branch
        r = self._client.post(
            f"/2.0/repositories/{self._repo}/refs/branches",
            json={"name": branch_name, "target": {"hash": base_sha}},
        )
        r.raise_for_status()

        # Commit the file
        r = self._client.post(
            f"/2.0/repositories/{self._repo}/src",
            data={
                file_path: new_content,
                "message": f"{title}",
                "branch": branch_name,
            },
        )
        r.raise_for_status()

        # Open PR
        r = self._client.post(
            f"/2.0/repositories/{self._repo}/pullrequests",
            json={
                "title": title,
                "description": body,
                "source": {"branch": {"name": branch_name}},
                "destination": {"branch": {"name": base_branch}},
                "close_source_branch": True,
            },
        )
        r.raise_for_status()
        pr = r.json()
        return PRResult(
            pr_url=pr.get("links", {}).get("html", {}).get("href", ""),
            pr_id=pr.get("id", 0),
            branch=branch_name,
        )
