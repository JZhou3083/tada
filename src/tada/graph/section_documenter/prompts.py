from collections.abc import Sequence
from textwrap import dedent

from tada.llm.schemas import EvalResult

_FEEDBACK_SEPARATOR = "---------------------------------------------------------"


def _append_feedback_prompt(prompt: str, feedback_history: Sequence[str]) -> str:
    """Append failed evaluation feedback to a documentation prompt."""
    feedback_history = [
        feedback.strip() for feedback in feedback_history if feedback.strip()
    ]

    if not feedback_history:
        return prompt

    if len(feedback_history) == 1:
        feedback_prompt = dedent(f"""
            ### CRITICAL FEEDBACK (MUST FIX):
            The Quality Assurance team flagged errors in your previous attempt.
            You must correct these in the new version.

            {_FEEDBACK_SEPARATOR}
            {feedback_history[0]}
            {_FEEDBACK_SEPARATOR}
        """).lstrip()

        return f"{prompt}\n\n{feedback_prompt}"

    latest_feedback = feedback_history[-1]
    older_feedback = "\n".join(f"- {feedback}" for feedback in feedback_history[:-1])

    feedback_prompt = dedent(f"""
        ## CRITICAL FEEDBACK (MUST FIX):
        The Quality Assurance team identified issues in previous attempts.

        Some older issues may already have been corrected, but they are included
        to ensure they do not reappear.

        Most Recent Feedback (Must Fix NOW):
        {_FEEDBACK_SEPARATOR}
        {latest_feedback}
        {_FEEDBACK_SEPARATOR}

        Past Feedback:
        {older_feedback}

        You must ensure:
        1. All items in the most recent feedback are fully corrected.
        2. No issues from past feedback reappear in this version.
    """).lstrip()

    return f"{prompt}\n\n{feedback_prompt}"


def append_eval_feedback_prompt(prompt: str, feedback: Sequence[EvalResult]) -> str:
    """Append feedback from failed evaluation results to a prompt."""
    feedback_history = [
        result.feedback_for_generator for result in feedback if not result.passed
    ]

    return _append_feedback_prompt(prompt, feedback_history)
