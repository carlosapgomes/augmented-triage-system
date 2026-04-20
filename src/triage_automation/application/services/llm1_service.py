"""LLM1 orchestration service for structured extraction and summary generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from triage_automation.application.dto.llm1_models import Llm1Response
from triage_automation.application.ports.case_repository_port import (
    CaseLlmInteractionCreateInput,
    CaseRepositoryPort,
)
from triage_automation.application.services.llm_json_parser import (
    LlmJsonParseError,
    decode_llm_json_object,
)
from triage_automation.application.services.prompt_template_service import (
    PROMPT_NAME_LLM1_SYSTEM,
    PROMPT_NAME_LLM1_USER,
    MissingActivePromptTemplateError,
    PromptTemplateService,
)
from triage_automation.application.services.ptbr_language_guard import (
    collect_forbidden_terms,
)
from triage_automation.infrastructure.llm.llm_client import LlmClientPort


@dataclass(frozen=True)
class Llm1ServiceResult:
    """Validated and normalized LLM1 artifacts for persistence."""

    structured_data_json: dict[str, object]
    summary_text: str
    prompt_system_name: str
    prompt_system_version: int
    prompt_user_name: str
    prompt_user_version: int


@dataclass(frozen=True)
class Llm1RetriableError(RuntimeError):
    """Retriable LLM1 failure with explicit cause label."""

    cause: str
    details: str

    def __str__(self) -> str:
        return f"{self.cause}: {self.details}"


class Llm1Service:
    """Execute LLM1 call, enforce schema, and normalize output."""

    _LANGUAGE_RETRY_INSTRUCTION = (
        "Regra obrigatoria adicional: todo texto narrativo deve estar em portugues "
        "brasileiro (pt-BR), sem palavras em ingles."
    )

    def __init__(
        self,
        *,
        llm_client: LlmClientPort,
        prompt_templates: PromptTemplateService | None = None,
        system_prompt_name: str = PROMPT_NAME_LLM1_SYSTEM,
        user_prompt_name: str = PROMPT_NAME_LLM1_USER,
    ) -> None:
        self._llm_client = llm_client
        self._prompt_templates = prompt_templates
        self._system_prompt_name = system_prompt_name
        self._user_prompt_name = user_prompt_name

    async def run(
        self,
        *,
        case_id: UUID,
        agency_record_number: str,
        clean_text: str,
        interaction_repository: CaseRepositoryPort | None = None,
    ) -> Llm1ServiceResult:
        """Execute LLM1 and return validated structured extraction artifacts."""

        (
            system_prompt,
            user_prompt_template,
            system_prompt_name,
            system_prompt_version,
            user_prompt_name,
            user_prompt_version,
        ) = await self._load_prompts()
        user_prompt = _render_user_prompt(
            template=user_prompt_template,
            case_id=case_id,
            agency_record_number=agency_record_number,
            clean_text=clean_text,
        )

        raw_response = await self._complete_and_capture(
            case_id=case_id,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            prompt_system_name=system_prompt_name,
            prompt_system_version=system_prompt_version,
            prompt_user_name=user_prompt_name,
            prompt_user_version=user_prompt_version,
            interaction_repository=interaction_repository,
        )
        validated = _decode_and_validate_llm1_response(
            raw_response=raw_response,
            agency_record_number=agency_record_number,
        )

        forbidden_terms = _collect_llm1_forbidden_terms(validated=validated)
        if forbidden_terms:
            retry_user_prompt = (
                f"{user_prompt}\n\n"
                f"{self._LANGUAGE_RETRY_INSTRUCTION}"
            )
            retry_response = await self._complete_and_capture(
                case_id=case_id,
                system_prompt=system_prompt,
                user_prompt=retry_user_prompt,
                prompt_system_name=system_prompt_name,
                prompt_system_version=system_prompt_version,
                prompt_user_name=user_prompt_name,
                prompt_user_version=user_prompt_version,
                interaction_repository=interaction_repository,
            )
            validated = _decode_and_validate_llm1_response(
                raw_response=retry_response,
                agency_record_number=agency_record_number,
            )
            forbidden_terms = _collect_llm1_forbidden_terms(validated=validated)
            if forbidden_terms:
                joined_terms = ", ".join(forbidden_terms)
                raise Llm1RetriableError(
                    cause="llm1",
                    details=(
                        "LLM1 output contains non-ptbr narrative terms after retry: "
                        f"{joined_terms}"
                    ),
                )

        structured = validated.model_dump(mode="json", by_alias=True)
        return Llm1ServiceResult(
            structured_data_json=structured,
            summary_text=validated.summary.one_liner,
            prompt_system_name=system_prompt_name,
            prompt_system_version=system_prompt_version,
            prompt_user_name=user_prompt_name,
            prompt_user_version=user_prompt_version,
        )

    async def _complete_and_capture(
        self,
        *,
        case_id: UUID,
        system_prompt: str,
        user_prompt: str,
        prompt_system_name: str,
        prompt_system_version: int,
        prompt_user_name: str,
        prompt_user_version: int,
        interaction_repository: CaseRepositoryPort | None,
    ) -> str:
        raw_response = await self._llm_client.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        if interaction_repository is not None:
            await interaction_repository.append_case_llm_interaction(
                CaseLlmInteractionCreateInput(
                    case_id=case_id,
                    stage="LLM1",
                    input_payload=_build_llm_input_payload(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                    ),
                    output_payload={"raw_response": raw_response},
                    prompt_system_name=prompt_system_name,
                    prompt_system_version=prompt_system_version,
                    prompt_user_name=prompt_user_name,
                    prompt_user_version=prompt_user_version,
                    model_name=_resolve_model_name(self._llm_client),
                )
            )
        return raw_response

    async def _load_prompts(self) -> tuple[str, str, str, int, str, int]:
        if self._prompt_templates is None:
            return (
                _default_system_prompt(),
                _default_user_prompt_template(),
                self._system_prompt_name,
                0,
                self._user_prompt_name,
                0,
            )

        try:
            pair = await self._prompt_templates.get_required_active_prompt_pair(
                system_prompt_name=self._system_prompt_name,
                user_prompt_name=self._user_prompt_name,
            )
        except MissingActivePromptTemplateError as error:
            raise Llm1RetriableError(cause="llm1", details=str(error)) from error

        return (
            pair.system.content,
            pair.user.content,
            pair.system.name,
            pair.system.version,
            pair.user.name,
            pair.user.version,
        )


def _default_system_prompt() -> str:
    return (
        "Voce e um assistente clinico para triagem de Endoscopia Digestiva Alta (EDA). "
        "Retorne APENAS JSON valido que siga estritamente o schema_version 1.1. "
        "Escreva todos os campos narrativos em portugues brasileiro (pt-BR). "
        "Nao use palavras em ingles nos campos narrativos. "
        "Nao inclua markdown, blocos de codigo ou chaves extras. "
        "Nao invente fatos; use null/unknown quando faltar informacao. "
        "Classifique o procedimento EDA suportado com subtype em standard, gastrostomy, "
        "esophageal_dilation ou foreign_body. Estime ASA pratico apenas nos buckets "
        "I-II, III ou mais, ou insufficient_data, sempre de forma conservadora e baseada "
        "no texto. Nao inferir Mallampati ou risco OSA."
    )


def _default_user_prompt_template() -> str:
    return (
        "Tarefa: extrair dados estruturados e gerar resumo conciso de triagem "
        "a partir de um relatorio clinico para triagem EDA. "
        "Exigir evidencia textual explicita para cada campo objetivo. "
        "Quando nao houver evidencia textual, retornar unknown (ou null para numericos). "
        "Preencher preop_screening.rulebook_signals para o novo rulebook, incluindo "
        "exames minimos, exames condicionais, subtipo EDA suportado e contexto de "
        "paciente pediatrico. Incluir preop_screening.evidence_spans com field_path "
        "e excerpt sempre que houver evidencia. "
        "Extrair origin_context (cidade/hospital/unidade/UF) quando disponivel no texto. "
        "Identificar exames rastreados (tracked_exams) com recencia determinada por "
        "data/hora ou posicao textual, com desempate pela ultima ocorrencia. "
        "Registrar had_transfusion como binario (yes/no); ausencia de evidencia como 'no'."
    )


def _render_user_prompt(
    *,
    template: str,
    case_id: UUID,
    agency_record_number: str,
    clean_text: str,
) -> str:
    return (
        f"{template}\n\n"
        f"case_id: {case_id}\n"
        f"agency_record_number: {agency_record_number}\n\n"
        "Retorne JSON schema_version 1.1 e preserve agency_record_number exatamente.\n"
        "Todos os campos narrativos devem estar em portugues brasileiro (pt-BR).\n"
        "Nao use palavras em ingles nos campos narrativos.\n"
        "Estimar ASA pratico apenas em I-II, III ou mais ou insufficient_data.\n"
        "Nao inferir Mallampati ou risco OSA.\n"
        "Cada campo objetivo deve ter evidencia textual; se nao houver, usar unknown.\n"
        "Para hb_g_dl, platelets_per_mm3 e inr sem evidencia numerica, usar null.\n"
        "Incluir preop_screening.evidence_spans com itens {field_path, excerpt}.\n"
        "Preencher eda.requested_procedure.subtype e preop_screening.rulebook_signals.eda_subtype "
        "com standard, gastrostomy, esophageal_dilation, foreign_body ou unknown.\n"
        "Para escopo do exame: classificar preop_screening.exam_type=eda para EDA padrao, "
        "gastrostomia/GTT/PEG, dilatacao esofagica e retirada de corpo estranho; usar non_eda "
        "apenas para solicitacoes claramente fora de escopo EDA, incluindo CPRE; usar unknown "
        "somente quando o tipo de exame permanecer indefinido.\n"
        "Quando houver gastrostomia/GTT/PEG, usar subtype gastrostomy; quando houver "
        "dilatacao esofagica, usar subtype esophageal_dilation; quando houver retirada de "
        "corpo estranho, usar subtype foreign_body; nos demais casos suportados, usar "
        "subtype standard.\n"
        "Preencher preop_screening.rulebook_signals.minimum_exam_evidence com hb_or_hct_present, "
        "hb_numeric_present, platelets_numeric_present, tp_inr_rni_numeric_present, ttpa_present, "
        "urea_present, creatinine_present, coagulogram_normal_supports_ttpa e "
        "renal_function_preserved_supports_urea_and_creatinine.\n"
        "Preencher preop_screening.rulebook_signals.conditional_exam_requirements com "
        "ecg_required, chest_xray_required, echocardiogram_required, "
        "ecg_report_finding_present, chest_xray_report_finding_present e "
        "echocardiogram_report_finding_present.\n"
        "Preencher preop_screening.rulebook_signals.clinical_flags com sinais clinicos do "
        "rulebook, inclusive contexto de paciente pediatrico, hepatopatia, cardiopatia, "
        "doenca cardiovascular, criterios respiratorios e gatilhos para ECG/ECO.\n"
        "Se patient.age < 16, marcar eda.is_pediatric=true e "
        "policy_precheck.pediatric_flag=true; se age >= 16, manter ambos false. "
        "Explicitar contexto de paciente pediatrico no resumo.\n\n"
        "Para origin_context (cidade/hospital/unidade): "
        "extrair cidade, hospital e unidade do texto; "
        "se houver sigla de UF (estado), preencher state_uf. "
        "Quando nao houver evidencia textual, preencher todos os subcampos como null.\n"
        "Para recencia de exames rastreados (tracked_exams): "
        "usar data/hora (exam_datetime_iso) quando disponivel para determinar o mais recente; "
        "sem data/hora, inferir recencia pela posicao textual; "
        "em caso de empate, desempate pela ultima ocorrencia no texto. "
        "Marcar is_most_recent=true apenas para o mais recente de cada tipo.\n"
        "Para had_transfusion: resposta estritamente binaria (yes/no); "
        "ausencia de evidencia de transfusao deve ser tratada como 'no'. "
        "Se had_transfusion=yes, informar total_units (inteiro) "
        "e hemocomponent quando disponivel.\n"
        f"Texto clinico do relatorio:\n{clean_text}"
    )


def _decode_and_validate_llm1_response(
    *,
    raw_response: str,
    agency_record_number: str,
) -> Llm1Response:
    try:
        decoded = decode_llm_json_object(raw_response)
    except LlmJsonParseError as error:
        raise Llm1RetriableError(
            cause="llm1",
            details="LLM1 returned non-JSON payload",
        ) from error

    try:
        validated = Llm1Response.model_validate(decoded)
    except ValidationError as error:
        raise Llm1RetriableError(
            cause="llm1",
            details=f"LLM1 schema validation failed: {error}",
        ) from error

    if validated.agency_record_number != agency_record_number:
        raise Llm1RetriableError(
            cause="llm1",
            details="LLM1 agency_record_number mismatch",
        )

    return validated


def _collect_llm1_forbidden_terms(*, validated: Llm1Response) -> list[str]:
    texts: list[str] = [
        validated.summary.one_liner,
        *validated.summary.bullet_points,
    ]
    optional_texts = [
        validated.policy_precheck.notes,
        validated.extraction_quality.notes,
    ]
    texts.extend(text for text in optional_texts if text is not None)
    return collect_forbidden_terms(texts=texts)


def _build_llm_input_payload(*, system_prompt: str, user_prompt: str) -> dict[str, Any]:
    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
    }


def _resolve_model_name(client: LlmClientPort) -> str | None:
    model_name = getattr(client, "model_name", None)
    if isinstance(model_name, str) and model_name.strip():
        return model_name
    return None
