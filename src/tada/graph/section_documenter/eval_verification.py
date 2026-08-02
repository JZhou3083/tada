from tada.llm.schemas import BlockingIssue, EvalResult, NonBlockingIssue


def _absent_from_source(keys: list[str], source_json: str) -> bool:
    """Return True only if none of `keys` appear anywhere in the raw source JSON.

    A literal substring check against the serialized JSON is a cheap, reliable way
    to confirm a field genuinely doesn't exist anywhere in the source data,
    regardless of nesting depth or exact path. This deliberately avoids asking the
    evaluator model to make that same "is it really missing" judgement itself --
    Tableau's XML schema varies significantly by version and data-source/model
    type, and evaluator models were observed to be inconsistent at recognising
    when a field is legitimately absent versus a real omission.
    """
    if not keys:
        return False

    return not any(key in source_json for key in keys)


def verify_blocking_issues(eval_result: EvalResult, source_json: str) -> EvalResult:
    """Downgrade `critical_omission` issues for fields absent from the source JSON.

    For each `critical_omission`, the evaluator names the literal JSON key(s) it
    expected but couldn't find (`BlockingIssue.source_json_keys`). If none of
    those keys appear anywhere in `source_json`, the field was never present in
    the source data in the first place -- so the omission is legitimate rather
    than a documentation defect, and is moved to `non_blocking_issues` instead of
    blocking a pass/retry.

    Args:
        eval_result: Structured evaluation result from the LLM.
        source_json: The same source JSON string the evaluator was given.

    Returns:
        `eval_result` unchanged if nothing was downgraded, otherwise a copy with
        the affected issues moved from `blocking_issues` to `non_blocking_issues`.
    """
    verified_blocking: list[BlockingIssue] = []
    demoted: list[NonBlockingIssue] = []

    for issue in eval_result.blocking_issues:
        if issue.type == "critical_omission" and _absent_from_source(
            issue.source_json_keys, source_json
        ):
            demoted.append(NonBlockingIssue(type="benign_omission", item=issue.item))
        else:
            verified_blocking.append(issue)

    if not demoted:
        return eval_result

    return eval_result.model_copy(
        update={
            "blocking_issues": verified_blocking,
            "non_blocking_issues": [*eval_result.non_blocking_issues, *demoted],
        }
    )
