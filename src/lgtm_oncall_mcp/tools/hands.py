"""Destructive actions: rollback_deploy, propose_fix_pr.

These tools route through the VCS adapter so the same code works for
Bitbucket Cloud or GitHub.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from fastmcp import FastMCP

    from ..config import Config
    from ..vcs.base import VCSAdapter


@dataclass
class HandsCtx:
    cfg: "Config"
    vcs: "VCSAdapter"


def register(mcp: "FastMCP", ctx: HandsCtx) -> None:
    rules = ctx.cfg.deploy_tags

    def rollback_deploy(env: str, target_tag: str) -> dict:
        """Re-run the deploy pipeline against an existing tag (rollback).

        Does NOT create a new tag — it reruns the pipeline/workflow for the
        tag you pass. Use after get_recent_deploys identifies a known-good tag.

        Args:
            env: Environment ('prod', 'staging', 'dev', ...). The tag must
                 match this env's naming convention (see DEPLOY_TAG_*).
            target_tag: Existing tag name, e.g. 'v1.2.3' or 'v1.2.3-stag'.

        Returns {"pipeline_id", "build_number", "url", "state"}.
        Call ONLY after the user (or an alert flow) has confirmed the rollback.
        This is a destructive action.
        """
        if not rules.matches(env, target_tag):
            raise ValueError(
                f"tag {target_tag!r} doesn't match the naming convention for env={env!r}"
            )
        result = ctx.vcs.trigger_deploy(env=env, ref=target_tag)
        return {
            "pipeline_id": result.pipeline_id,
            "build_number": result.build_number,
            "url": result.url,
            "state": result.state,
        }

    def propose_fix_pr(
        branch_name: str,
        file_path: str,
        new_content: str,
        title: str,
        body: str,
        base_branch: str = "main",
    ) -> dict:
        """Open a PR that replaces a file's contents with `new_content`.

        Use when the bug is in code, you've analyzed via get_commit_diff, and
        you have a corrected version of the file. The PR is opened against
        `base_branch` — humans review and merge.

        Args:
            branch_name: New branch name, e.g. 'ai-fix/null-form-1717'.
            file_path: Path within the repo, e.g. 'internal/handlers/form.go'.
            new_content: Complete new file content.
            title: PR title.
            body: PR description (markdown ok).
            base_branch: Branch to branch from + open PR against (default 'main').

        Returns {"pr_url", "pr_id", "branch"}.
        Call ONLY after the fix is confirmed. Destructive action.
        """
        result = ctx.vcs.open_pr(
            branch_name=branch_name,
            file_path=file_path,
            new_content=new_content,
            title=title,
            body=body,
            base_branch=base_branch,
        )
        return {"pr_url": result.pr_url, "pr_id": result.pr_id, "branch": result.branch}

    for fn in (rollback_deploy, propose_fix_pr):
        mcp.tool(fn)
