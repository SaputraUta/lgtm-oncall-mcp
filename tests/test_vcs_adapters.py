"""VCS adapter contracts — both Bitbucket and GitHub satisfy the Protocol."""

from __future__ import annotations

import respx

from lgtm_oncall_mcp.config import BitbucketConfig, GitHubConfig
from lgtm_oncall_mcp.vcs.bitbucket import BitbucketAdapter
from lgtm_oncall_mcp.vcs.github import GitHubAdapter


@respx.mock
def test_bitbucket_list_tags():
    respx.get("https://api.bitbucket.org/2.0/repositories/ws/repo/refs/tags").respond(
        json={
            "values": [
                {
                    "name": "v1.2.3",
                    "target": {
                        "hash": "abc123def456",
                        "date": "2026-01-01T00:00:00+00:00",
                        "message": "release",
                    },
                }
            ]
        }
    )
    bb = BitbucketAdapter(
        BitbucketConfig(email="a@b.com", api_token="x", workspace="ws", repo_slug="repo")
    )
    tags = bb.list_tags(limit=5)
    assert len(tags) == 1
    assert tags[0].tag == "v1.2.3"
    assert tags[0].sha == "abc123def456"[:12]


@respx.mock
def test_bitbucket_trigger_deploy():
    respx.post("https://api.bitbucket.org/2.0/repositories/ws/repo/pipelines/").respond(
        json={
            "uuid": "{abc-pipeline-uuid}",
            "build_number": 42,
            "links": {"html": {"href": "https://bitbucket.org/.../42"}},
            "state": {"name": "PENDING"},
        }
    )
    bb = BitbucketAdapter(
        BitbucketConfig(email="a@b.com", api_token="x", workspace="ws", repo_slug="repo")
    )
    res = bb.trigger_deploy(env="staging", ref="v1.2.3-stag")
    assert res.pipeline_id == "abc-pipeline-uuid"
    assert res.build_number == 42
    assert res.state == "PENDING"


@respx.mock
def test_github_list_tags():
    respx.get("https://api.github.com/repos/myorg/myrepo/tags").respond(
        json=[{"name": "v1.2.3", "commit": {"sha": "abc123def456"}}]
    )
    respx.get("https://api.github.com/repos/myorg/myrepo/commits/abc123def456").respond(
        json={
            "commit": {
                "committer": {"date": "2026-01-01T00:00:00Z"},
                "message": "release v1.2.3",
            }
        }
    )
    gh = GitHubAdapter(
        GitHubConfig(
            token="ghp_x",
            owner="myorg",
            repo="myrepo",
            deploy_workflow="deploy.yml",
            api_base="https://api.github.com",
        )
    )
    tags = gh.list_tags(limit=5)
    assert len(tags) == 1
    assert tags[0].tag == "v1.2.3"
    assert tags[0].message == "release v1.2.3"


@respx.mock
def test_github_trigger_deploy():
    respx.post(
        "https://api.github.com/repos/myorg/myrepo/actions/workflows/deploy.yml/dispatches"
    ).respond(status_code=204)
    gh = GitHubAdapter(
        GitHubConfig(
            token="ghp_x",
            owner="myorg",
            repo="myrepo",
            deploy_workflow="deploy.yml",
            api_base="https://api.github.com",
        )
    )
    res = gh.trigger_deploy(env="staging", ref="v1.2.3")
    assert res.state == "dispatched"
    assert "myorg/myrepo" in res.url
