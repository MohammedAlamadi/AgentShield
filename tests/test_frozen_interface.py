"""Guards against accidental changes to the frozen prompt and tool interface (frozen 13 Nov 2026,
before any evaluation run). If a change is ever intended, it must be recorded in
docs/implementation_deviations.md and all affected runs repeated."""

import hashlib
import json

from agentshield.config import DefenceConfig
from agentshield.isolation import SYSTEM_PROMPT_ADDENDUM
from agentshield.prompts import BASE_SYSTEM_PROMPT, PROMPT_VERSION, PROMPTS, prompt_sha256
from agentshield.tools import TOOL_SCHEMAS

FROZEN_PROMPT_VERSION = "v2"
FROZEN_PROMPT_SHA256 = "fd45f2411f437c8b1235369383a227f11340309c44d660bd99f09474e9036039"
FROZEN_L2_PROMPT_SHA256 = "07959b6b2753b96d94cfd757fbddce3f44fa79275319219e67548eb7596e4701"
FROZEN_TOOL_SCHEMA_SHA256 = "a6c3f448a7ee2424edd57ef1f06dff413e46b95be7fa230bfee5177552c34334"


def test_prompt_is_frozen():
    assert PROMPT_VERSION == FROZEN_PROMPT_VERSION
    assert BASE_SYSTEM_PROMPT == PROMPTS[FROZEN_PROMPT_VERSION]
    assert prompt_sha256(BASE_SYSTEM_PROMPT) == FROZEN_PROMPT_SHA256
    assert prompt_sha256(BASE_SYSTEM_PROMPT + "\n\n" + SYSTEM_PROMPT_ADDENDUM) == FROZEN_L2_PROMPT_SHA256


def test_tool_interface_is_frozen():
    digest = hashlib.sha256(json.dumps(TOOL_SCHEMAS, sort_keys=True).encode()).hexdigest()
    assert digest == FROZEN_TOOL_SCHEMA_SHA256
    read_inbox = next(s for s in TOOL_SCHEMAS if s["function"]["name"] == "read_inbox")
    assert read_inbox["function"]["parameters"]["properties"] == {}


def test_all_five_configs_share_prompt_and_tools(tmp_path):
    """Same base prompt and tool list in every configuration; only L2 appends its addendum."""
    from agentshield.agent import run_scenario
    from agentshield.guard import AuthorizationGuard
    from agentshield.isolation import ContentIsolator
    from agentshield.llm import FakeModel, ModelTurn

    from .conftest import make_scenario
    from .test_pipeline_integration import StubDetector

    class Recorder(FakeModel):
        def chat(self, messages, tools):
            self.tools_seen = tools
            return super().chat(messages, tools)

    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "configs"
    for name in ("unprotected", "l1_only", "l2_only", "l3_only", "full"):
        cfg = DefenceConfig.load(root / f"{name}.json")
        layers = {}
        if cfg.guard:
            layers["guard"] = AuthorizationGuard()
        if cfg.detector:
            layers["detector"] = StubDetector()
        if cfg.isolation:
            layers["isolator"] = ContentIsolator()
        m = Recorder([ModelTurn("ok")])
        run_scenario(make_scenario(), m, cfg, **layers)
        system = m.calls[0][0]["content"]
        assert system.startswith(BASE_SYSTEM_PROMPT)
        assert (system != BASE_SYSTEM_PROMPT) == cfg.isolation
        assert m.tools_seen == TOOL_SCHEMAS
