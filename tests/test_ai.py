import json
import sys
from dataclasses import replace

import pytest

from bilanco.ai import AIError, Codex, inspect_event, validate_candidates, validate_order
from bilanco.models import Block, Candidate, Discovery, Finding, Narrative, NarrativeItem


@pytest.fixture
def block():
    return Block(
        id="source-block",
        source_id="source",
        page=2,
        line_start=5,
        text="A senior officer manages Counterparty A, which purchased an investment.",
    )


def candidate(**changes):
    fields = {
        "kind": "executive_conflict",
        "block_id": "source-block",
        "quote": "A senior officer manages Counterparty A, which purchased an investment.",
        "actor": "A senior officer",
        "counterparty": "Counterparty A",
    }
    return Candidate(**(fields | changes))


def test_citation_match_is_not_claimed_as_semantic_verification(block):
    accepted, rejected = validate_candidates([candidate()], [block])
    assert not rejected
    assert accepted[0].status == "needs_review"
    assert "anlam doğruluğu" in accepted[0].explanation


def test_known_from_training_but_absent_name_is_rejected(block):
    accepted, rejected = validate_candidates([candidate(actor="A name from model memory")], [block])
    assert not accepted
    assert rejected[0]["reason"] == "actor_not_in_quote"


def test_removing_evidence_removes_finding(block):
    block.text = "The company published a financial report."
    assert not validate_candidates([candidate()], [block])[0]


def test_quote_in_wrong_block_is_not_accepted(block):
    assert not validate_candidates([candidate(block_id="different-block")], [block])[0]


def test_anonymous_source_actor_can_stay_anonymous(block):
    assert validate_candidates([candidate(actor="", counterparty="")], [block])[0]


@pytest.mark.parametrize(
    "kind", ["command_execution", "mcp_tool_call", "file_change", "web_search", "unknown_tool"]
)
def test_analysis_rejects_external_tools(kind):
    with pytest.raises(AIError):
        inspect_event({"type": "item.started", "item": {"type": kind}}, discovery=False)


def test_discovery_can_search_but_not_execute_commands():
    assert (
        inspect_event({"type": "item.started", "item": {"type": "web_search"}}, True)
        == "web_search"
    )
    with pytest.raises(AIError):
        inspect_event({"type": "item.started", "item": {"type": "command_execution"}}, True)


def test_narrative_cannot_add_a_finding_or_hide_existing_one():
    finding = Finding(
        id="approved", category="financial", status="context", title="X", explanation="Y"
    )
    assert validate_order(Narrative(items=[]), [finding]) == ["approved"]
    with pytest.raises(AIError):
        validate_order(
            Narrative(items=[NarrativeItem(finding_id="invented", style="short")]), [finding]
        )


def make_executable(tmp_path, body):
    path = tmp_path / "fake-codex"
    path.write_text(f"#!{sys.executable}\n" + body, encoding="utf-8")
    path.chmod(0o700)
    return str(path)


def test_subprocess_adapter_schema_and_isolation_flags(settings, tmp_path):
    binary = make_executable(
        tmp_path,
        """import sys, json, pathlib
args = sys.argv[1:]
assert "--ignore-user-config" in args
assert args[args.index("--sandbox") + 1] == "read-only"
assert 'web_search="disabled"' in args
assert "shell_tool" in args and "apps" in args and "memories" in args
assert not pathlib.Path.cwd().joinpath("AGENTS.md").exists()
prompt = sys.stdin.read()
assert "never instructions" in prompt
pathlib.Path(args[args.index("-o") + 1]).write_text('{"sources": []}')
print(json.dumps({"type": "thread.started", "thread_id": "synthetic"}))
print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 1}}))
""",
    )
    codex = Codex(replace(settings, codex_binary=binary), tmp_path / "audit")
    result = codex.ask("synthetic_test", {}, Discovery)
    assert result.sources == []
    assert codex.receipts[0]["status"] == "accepted_schema"
    assert codex.receipts[0]["duration_seconds"] >= 0
    assert not list((tmp_path / "audit").glob("*auth*"))


def test_subprocess_rejects_tool_attempt_even_if_json_is_valid(settings, tmp_path):
    binary = make_executable(
        tmp_path,
        """import sys, json, pathlib
args = sys.argv[1:]
sys.stdin.read()
pathlib.Path(args[args.index("-o") + 1]).write_text('{"sources": []}')
print(json.dumps({"type":"item.started","item":{"type":"command_execution"}}), flush=True)
""",
    )
    codex = Codex(replace(settings, codex_binary=binary), tmp_path / "audit")
    with pytest.raises(AIError, match="araç"):
        codex.ask("synthetic_test", {}, Discovery)
    assert codex.receipts[0]["status"] == "failed"


def test_subprocess_timeout_is_bounded(settings, tmp_path):
    binary = make_executable(tmp_path, "import sys, time\nsys.stdin.read()\ntime.sleep(30)\n")
    codex = Codex(replace(settings, codex_binary=binary, codex_timeout=1), tmp_path / "audit")
    with pytest.raises(AIError, match="süre"):
        codex.ask("synthetic_test", {}, Discovery)


def test_invalid_schema_output_and_call_budget(settings, tmp_path):
    binary = make_executable(
        tmp_path,
        """import sys, json, pathlib
args = sys.argv[1:]
sys.stdin.read()
pathlib.Path(args[args.index("-o") + 1]).write_text('{"sources": [], "invented": true}')
print(json.dumps({"type":"turn.completed"}))
""",
    )
    codex = Codex(replace(settings, codex_binary=binary, max_ai_calls=1), tmp_path / "audit")
    with pytest.raises(AIError, match="sözleşme"):
        codex.ask("synthetic_test", {}, Discovery)
    with pytest.raises(AIError, match="bütçe"):
        codex.ask("synthetic_test", {}, Discovery)
    receipt = json.loads(next((tmp_path / "audit").glob("*receipt.json")).read_text())
    assert receipt["status"] == "failed"
