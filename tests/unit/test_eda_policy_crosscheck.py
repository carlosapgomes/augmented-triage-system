from __future__ import annotations

from triage_automation.domain.policy.eda_policy import (
    EdaPolicyPrecheckInput,
    Llm2PolicyAlignmentInput,
    Llm2SuggestionInput,
    reconcile_eda_policy,
)


def _base_precheck() -> EdaPolicyPrecheckInput:
    return EdaPolicyPrecheckInput(
        excluded_from_eda_flow=False,
        indication_category="dyspepsia",
        labs_required=True,
        labs_pass="yes",
        ecg_required=True,
        ecg_present="yes",
        pediatric_flag=False,
    )


def _base_llm2() -> Llm2SuggestionInput:
    return Llm2SuggestionInput(
        suggestion="accept",
        policy_alignment=Llm2PolicyAlignmentInput(
            excluded_request=False,
            labs_ok="yes",
            ecg_ok="yes",
            pediatric_flag=False,
            notes=None,
        ),
    )


def test_excluded_request_forces_deny() -> None:
    precheck = _base_precheck()
    precheck = EdaPolicyPrecheckInput(
        excluded_from_eda_flow=True,
        indication_category=precheck.indication_category,
        labs_required=precheck.labs_required,
        labs_pass=precheck.labs_pass,
        ecg_required=precheck.ecg_required,
        ecg_present=precheck.ecg_present,
        pediatric_flag=precheck.pediatric_flag,
    )

    result = reconcile_eda_policy(precheck=precheck, llm2=_base_llm2())

    assert result.suggestion == "deny"
    assert result.policy_alignment.excluded_request is True


def test_foreign_body_sets_labs_and_ecg_to_not_required() -> None:
    precheck = EdaPolicyPrecheckInput(
        excluded_from_eda_flow=False,
        indication_category="foreign_body",
        labs_required=False,
        labs_pass="unknown",
        ecg_required=False,
        ecg_present="unknown",
        pediatric_flag=False,
    )

    result = reconcile_eda_policy(precheck=precheck, llm2=_base_llm2())

    assert result.policy_alignment.labs_ok == "not_required"
    assert result.policy_alignment.ecg_ok == "not_required"


def test_missing_required_labs_and_ecg_force_deny_aligned_output() -> None:
    precheck = EdaPolicyPrecheckInput(
        excluded_from_eda_flow=False,
        indication_category="dyspepsia",
        labs_required=True,
        labs_pass="unknown",
        ecg_required=True,
        ecg_present="unknown",
        pediatric_flag=False,
    )

    result = reconcile_eda_policy(precheck=precheck, llm2=_base_llm2())

    assert result.suggestion == "deny"
    assert result.policy_alignment.labs_ok == "unknown"
    assert result.policy_alignment.ecg_ok == "unknown"


def test_contradictions_are_reported_when_policy_forces_changes() -> None:
    precheck = EdaPolicyPrecheckInput(
        excluded_from_eda_flow=True,
        indication_category="dyspepsia",
        labs_required=True,
        labs_pass="no",
        ecg_required=True,
        ecg_present="no",
        pediatric_flag=False,
    )

    result = reconcile_eda_policy(precheck=precheck, llm2=_base_llm2())

    assert result.contradictions
    assert any(item.field == "suggestion" for item in result.contradictions)
