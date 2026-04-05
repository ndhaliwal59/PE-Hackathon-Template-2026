"""Remediation actions for ServiceDown alerts.

Uses the Docker SDK to inspect and restart containers identified by their
``com.docker.compose.service`` label.  Mirrors the manual steps in
docs/RUNBOOK.md.
"""

from __future__ import annotations

import logging

import docker

logger = logging.getLogger("auto-healer.remediation")

CLIENT: docker.DockerClient | None = None


def _docker() -> docker.DockerClient:
    global CLIENT
    if CLIENT is None:
        CLIENT = docker.from_env()
    return CLIENT


def _find_containers(service: str) -> list[docker.models.containers.Container]:
    """Return running-or-stopped containers for a Compose service name."""
    return _docker().containers.list(
        all=True,
        filters={"label": f"com.docker.compose.service={service}"},
    )


def _ensure_running(service: str) -> str:
    """Start the container for *service* if it is not running. Returns action taken."""
    containers = _find_containers(service)
    if not containers:
        return f"{service}: no container found"

    actions = []
    for c in containers:
        c.reload()
        if c.status != "running":
            logger.info("starting container %s (%s)", c.name, service)
            c.start()
            actions.append(f"started {c.name}")
        else:
            actions.append(f"{c.name} already running")
    return "; ".join(actions)


def heal_service_down() -> str:
    """RUNBOOK: Alert ServiceDown.

    1. Start nginx if stopped.
    2. If nginx is running, check and start web replicas.
    """
    actions = []

    nginx_action = _ensure_running("nginx")
    actions.append(f"nginx -> {nginx_action}")

    for svc in ("web1", "web2", "web3"):
        result = _ensure_running(svc)
        actions.append(f"{svc} -> {result}")

    return " | ".join(actions)
