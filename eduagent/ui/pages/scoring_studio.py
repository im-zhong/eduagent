from __future__ import annotations

import json
from typing import Any, cast

import streamlit as st

from eduagent.ui import common
from eduagent.ui.api_client import EduAgentAPIClient


def render(client: EduAgentAPIClient) -> None:
    st.title("Scoring Studio")
    quiz_job_id = st.text_input("Quiz Job ID for Scoring")
    questions = common.json_text_area("Questions JSON", "score_questions")
    rules_text = st.text_area(
        "Optional Rules JSON",
        height=120,
        placeholder='{"allow_distractors": true}',
    )
    rules: dict[str, Any] | None = None
    if rules_text.strip():
        try:
            parsed = json.loads(rules_text)
            if isinstance(parsed, dict):
                rules = cast(dict[str, Any], parsed)
            else:
                st.warning("Rules JSON should be an object/dict")
        except json.JSONDecodeError as exc:
            st.warning(f"Rules JSON invalid: {exc}")
    if st.button("Score Quiz") and quiz_job_id and questions:
        with st.spinner("Requesting scoring job..."):
            response = client.request_quiz_scoring(quiz_job_id, questions, rules)
        st.json(response)
