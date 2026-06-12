import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import llm as srv  # noqa: E402

def _user(t): return srv.UserMessage(role="user", content=t)

def test_retrieve_hit():
    hits = srv.retrieve("what is your refund policy?")
    assert hits and hits[0][0] == "refund policy"

def test_retrieve_miss():
    assert srv.retrieve("tell me a joke") == []

def test_run_agent_turn_grounds_answer():
    out = srv.run_agent_turn([_user("how long is shipping?")])
    assert "three to five business days" in out

def test_run_agent_turn_miss():
    out = srv.run_agent_turn([_user("tell me a joke")])
    assert "don't have anything" in out.lower()

def test_retrieve_no_false_positive_on_substring():
    # "business" appears as a token only in the topic, not the query phrase below
    assert srv.retrieve("I want to do good work with you") == []
