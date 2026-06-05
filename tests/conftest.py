"""Shared test fixtures."""

from __future__ import annotations

import re

import pytest

from lgtm_oncall_mcp.config import (
    BitbucketConfig,
    Config,
    DeployTagConfig,
    GrafanaConfig,
    LabelConfig,
    ServerConfig,
    VCSConfig,
)


@pytest.fixture
def cfg() -> Config:
    """A minimal Config that exercises every dataclass without hitting env vars."""
    return Config(
        grafana=GrafanaConfig(
            url="https://grafana.test",
            token="test-token",
            mimir_ds_uid="mimir-uid",
            loki_ds_uid="loki-uid",
            ca_cert_path=None,
        ),
        labels=LabelConfig(env_key="env", team_key="team", team_value="testteam"),
        deploy_tags=DeployTagConfig(
            prod_regex=re.compile(r"^v\d+\.\d+\.\d+$"),
            nonprod_suffixes={"dev": "-dev", "staging": "-stag"},
        ),
        vcs=VCSConfig(
            provider="bitbucket",
            bitbucket=BitbucketConfig(
                email="a@b.com",
                api_token="x",
                workspace="ws",
                repo_slug="repo",
            ),
            github=None,
        ),
        server=ServerConfig(host="127.0.0.1", port=8765, bearer_token=""),
    )
