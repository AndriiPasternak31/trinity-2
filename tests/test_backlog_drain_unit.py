"""
Backlog drain spawn unit tests (test_backlog_drain_unit.py)

Issue #496. Pins two contracts that, if either drifts, silently break
BACKLOG-001:

1. **Import contract** — `routers.chat` must define a public-enough
   `_run_async_task_with_persistence` symbol that `BacklogService._spawn_drain`
   can import. The previous symbol (`_execute_task_background`) was deleted by
   #95 (PR #316) without updating the lazy import here, leaving every drain
   raising `ImportError` and silently marking queued executions as failed.

2. **Signature contract** — `_spawn_drain` must call the helper with the
   kwargs the helper actually accepts. Drift here would also be caught only
   at runtime, behind the same exception swallow at
   `services/backlog_service.py:218-228`.

Pure unit test — no backend, no live database, no router import side effects.

The contract checks (tests 1 + 2) are static AST scans on the source files
and need no stubbing at all. The runtime spy tests (3 + 4 + 5) build their
stubs inside fixtures with `monkeypatch.setitem` so sys.modules is restored
between tests and other unit-style test files in the suite are not polluted.
"""

from __future__ import annotations

import ast
import asyncio
import importlib.util
import os
import sys
import types
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

# Make src/backend importable for the AST-based tests (cheap, side-effect-free).
_BACKEND_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "src", "backend")
)
if _BACKEND_PATH not in sys.path:
    sys.path.insert(0, _BACKEND_PATH)


# Override the backend-requiring autouse fixtures from the package conftest.
@pytest.fixture(scope="session")
def api_client():
    yield None


@pytest.fixture(autouse=True)
def cleanup_after_test():
    yield


# ---------------------------------------------------------------------------
# Test 1 — Import contract (AST, no imports of routers/chat at runtime)
# ---------------------------------------------------------------------------


def test_routers_chat_defines_run_async_task_with_persistence():
    """`_run_async_task_with_persistence` must remain defined at the top of
    routers/chat.py. A pure-text/AST check is used (not a real import) so the
    test stays fast and self-contained — importing routers/chat would pull in
    the full backend dependency graph. If the function is renamed or removed,
    this test fails immediately rather than waiting for a capacity-overflow
    scenario in production.
    """
    chat_path = os.path.join(_BACKEND_PATH, "routers", "chat.py")
    with open(chat_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=chat_path)

    names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "_run_async_task_with_persistence" in names, (
        "`_run_async_task_with_persistence` must remain defined in "
        "routers/chat.py — BacklogService._spawn_drain depends on it via "
        "lazy import. If this helper is renamed, update "
        "services/backlog_service.py at the same time."
    )

    # Negative guard: the prior name must not come back without an
    # explicit migration of the drain.
    assert "_execute_task_background" not in names, (
        "`_execute_task_background` was deleted by issue #95. If a function "
        "with this name is reintroduced, ensure backlog_service.py is "
        "updated and remove this guard."
    )


# ---------------------------------------------------------------------------
# Test 2 — Signature contract (AST)
# ---------------------------------------------------------------------------


def test_run_async_task_with_persistence_signature_includes_drain_kwargs():
    """The helper must accept every kwarg `_spawn_drain` passes. Mirrors the
    call-site at `services/backlog_service.py:_spawn_drain`. If the helper
    drops or renames any of these parameters without a coordinated update,
    this test fails before the runtime ImportError-equivalent shows up.
    """
    chat_path = os.path.join(_BACKEND_PATH, "routers", "chat.py")
    with open(chat_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=chat_path)

    target = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.AsyncFunctionDef)
            and node.name == "_run_async_task_with_persistence"
        ),
        None,
    )
    assert target is not None, "Function not found (covered by other test)."

    params = {a.arg for a in target.args.args}
    required = {
        "agent_name",
        "request",
        "execution_id",
        "collaboration_activity_id",
        "x_source_agent",
        "user_id",
        "user_email",
        "subscription_id",
        "is_self_task",
        "self_task_activity_id",
    }
    missing = required - params
    assert not missing, (
        f"_run_async_task_with_persistence is missing kwargs that "
        f"BacklogService._spawn_drain passes: {sorted(missing)}. "
        "Coordinated update needed."
    )


# ---------------------------------------------------------------------------
# Test 3+ — Runtime spy on _spawn_drain
#
# We need a real `BacklogService` instance plus a fake `routers.chat` module
# the drain can lazy-import. All sys.modules manipulation is fixture-scoped
# via monkeypatch.setitem so other unit tests in the suite don't see leaked
# stubs.
# ---------------------------------------------------------------------------


@pytest.fixture
def backlog_module(monkeypatch):
    """Load services.backlog_service in isolation with stubbed dependencies.

    Stubs are installed via monkeypatch (auto-restored after each test) and
    the module itself is loaded via importlib so a real backend isn't needed.
    """
    # Stub `database` for the late `from database import db` calls in
    # backlog_service. The fake_db is configured per-test if needed.
    fake_db = MagicMock()
    fake_database = types.SimpleNamespace(db=fake_db)
    monkeypatch.setitem(sys.modules, "database", fake_database)

    # Stub `utils.helpers` — only `utc_now_iso` is consumed at module load.
    if "utils.helpers" not in sys.modules:
        helpers = types.ModuleType("utils.helpers")
        helpers.utc_now_iso = lambda: datetime.utcnow().isoformat() + "Z"
        monkeypatch.setitem(sys.modules, "utils.helpers", helpers)
        if "utils" not in sys.modules:
            monkeypatch.setitem(sys.modules, "utils", types.ModuleType("utils"))

    # Stub `models` with the symbols backlog_service imports. Use setdefault
    # so a richer stub installed by another test (e.g. with `User`) is
    # preserved.
    if "models" not in sys.modules:
        models_mod = types.ModuleType("models")

        class _StubParallelTaskRequest:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        models_mod.ParallelTaskRequest = _StubParallelTaskRequest
        models_mod.TaskExecutionStatus = MagicMock()
        models_mod.User = type("User", (), {})  # forward-compat for other unit tests
        monkeypatch.setitem(sys.modules, "models", models_mod)
    else:
        # Ensure the existing module satisfies what backlog_service imports.
        existing = sys.modules["models"]
        if not hasattr(existing, "ParallelTaskRequest"):
            class _StubParallelTaskRequest:
                def __init__(self, **kwargs):
                    self.__dict__.update(kwargs)

            existing.ParallelTaskRequest = _StubParallelTaskRequest
        if not hasattr(existing, "TaskExecutionStatus"):
            existing.TaskExecutionStatus = MagicMock()

    # Stub services.slot_service to avoid importing redis.
    services_pkg = sys.modules.get("services") or types.ModuleType("services")
    monkeypatch.setitem(sys.modules, "services", services_pkg)

    fake_slot = types.ModuleType("services.slot_service")
    fake_slot.get_slot_service = lambda: MagicMock()
    monkeypatch.setitem(sys.modules, "services.slot_service", fake_slot)

    # Load services.backlog_service via importlib (bypasses services/__init__.py).
    bs_path = os.path.join(_BACKEND_PATH, "services", "backlog_service.py")
    spec = importlib.util.spec_from_file_location(
        "_test_backlog_service", bs_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _install_chat_module_stub(monkeypatch, spy: AsyncMock) -> None:
    """Install a fake `routers.chat` exposing `_run_async_task_with_persistence`."""
    if "routers" not in sys.modules:
        monkeypatch.setitem(sys.modules, "routers", types.ModuleType("routers"))
    fake_chat = types.ModuleType("routers.chat")
    fake_chat._run_async_task_with_persistence = spy
    monkeypatch.setitem(sys.modules, "routers.chat", fake_chat)


def _make_metadata(x_source_agent: Any = None) -> Dict[str, Any]:
    return {
        "message": "hello",
        "model": "claude-sonnet-4-6",
        "allowed_tools": ["Read"],
        "system_prompt": None,
        "timeout_seconds": 600,
        "max_turns": None,
        "save_to_session": False,
        "user_message": None,
        "create_new_session": False,
        "chat_session_id": None,
        "resume_session_id": None,
        "user_id": 42,
        "user_email": "user@example.com",
        "subscription_id": "sub-1",
        "x_source_agent": x_source_agent,
        "x_mcp_key_id": None,
        "x_mcp_key_name": None,
        "triggered_by": "agent",
        "collaboration_activity_id": "collab-1",
        "task_activity_id": "task-1",  # ignored by the new helper
    }


def _run_drain(backlog_module, monkeypatch, metadata, agent_name, execution_id):
    """Execute `_spawn_drain` and the spawned coroutine, returning captured kwargs."""
    captured_kwargs: List[Dict[str, Any]] = []

    async def _spy(**kwargs):
        captured_kwargs.append(kwargs)

    spy = AsyncMock(side_effect=_spy)
    _install_chat_module_stub(monkeypatch, spy)

    captured_coros: List[Any] = []

    def _fake_create_task(coro):
        captured_coros.append(coro)

        class _T:
            def add_done_callback(self, *_a, **_kw):
                pass

            def cancel(self):
                pass

        return _T()

    monkeypatch.setattr(
        backlog_module.asyncio, "create_task", _fake_create_task
    )

    service = backlog_module.BacklogService()
    asyncio.run(
        service._spawn_drain(
            agent_name=agent_name,
            execution_id=execution_id,
            metadata=metadata,
        )
    )
    assert len(captured_coros) == 1, (
        "Expected exactly one asyncio.create_task() call from _spawn_drain"
    )
    asyncio.run(captured_coros[0])
    assert len(captured_kwargs) == 1, (
        "Expected exactly one call to _run_async_task_with_persistence"
    )
    return captured_kwargs[0]


def test_spawn_drain_calls_helper_with_expected_kwargs(backlog_module, monkeypatch):
    """Runtime contract: _spawn_drain forwards the right kwargs."""
    kwargs = _run_drain(
        backlog_module,
        monkeypatch,
        _make_metadata(x_source_agent="caller-agent"),
        agent_name="target-agent",
        execution_id="exec-1",
    )

    assert kwargs["agent_name"] == "target-agent"
    assert kwargs["execution_id"] == "exec-1"
    assert kwargs["collaboration_activity_id"] == "collab-1"
    assert kwargs["x_source_agent"] == "caller-agent"
    assert kwargs["user_id"] == 42
    assert kwargs["user_email"] == "user@example.com"
    assert kwargs["subscription_id"] == "sub-1"
    assert kwargs["is_self_task"] is False  # caller != target
    assert kwargs["self_task_activity_id"] is None

    request = kwargs["request"]
    assert request.message == "hello"
    assert request.async_mode is True
    assert request.timeout_seconds == 600

    # Ensure no stale params from the deleted helper leak through.
    assert "task_activity_id" not in kwargs
    assert "release_slot" not in kwargs


def test_spawn_drain_marks_self_task_when_source_matches_target(
    backlog_module, monkeypatch
):
    """is_self_task is derived from x_source_agent == agent_name."""
    kwargs = _run_drain(
        backlog_module,
        monkeypatch,
        _make_metadata(x_source_agent="self-agent"),
        agent_name="self-agent",
        execution_id="exec-2",
    )
    assert kwargs["is_self_task"] is True


def test_spawn_drain_marks_non_self_when_source_missing(
    backlog_module, monkeypatch
):
    """No x_source_agent → not a self-task."""
    kwargs = _run_drain(
        backlog_module,
        monkeypatch,
        _make_metadata(x_source_agent=None),
        agent_name="target-agent",
        execution_id="exec-3",
    )
    assert kwargs["is_self_task"] is False
    assert kwargs["x_source_agent"] is None
