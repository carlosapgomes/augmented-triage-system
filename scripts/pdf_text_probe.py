"""CLI tool to inspect extracted PDF text and detect patient registration codes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from triage_automation.domain.patient_registration_code import (
    count_patient_registration_codes,
    extract_patient_registration_matches,
)
from triage_automation.infrastructure.pdf.text_extractor import (
    PdfTextExtractionError,
    PdfTextExtractor,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Extract text from PDF files and detect patient registration codes "
            "matching 'Codigo: <digits>'/'Código: <digits>' or the flow "
            "'RELATÓRIO DE OCORRÊNCIAS' followed by a numeric token."
        )
    )
    parser.add_argument("pdf_paths", nargs="+", help="One or more PDF file paths.")
    parser.add_argument(
        "--show-text",
        action="store_true",
        help="Print the full extracted text after analysis.",
    )
    return parser


def _analyze_pdf(path: Path, extractor: PdfTextExtractor, show_text: bool) -> int:
    try:
        pdf_bytes = path.read_bytes()
    except OSError as error:
        print(f"[ERROR] Could not read '{path}': {error}", file=sys.stderr)
        return 1

    try:
        extracted_text = extractor.extract_text(pdf_bytes)
    except PdfTextExtractionError as error:
        print(f"[ERROR] Could not extract text from '{path}': {error}", file=sys.stderr)
        return 1

    matches = extract_patient_registration_matches(extracted_text)
    counts = count_patient_registration_codes(extracted_text)

    print(f"\n=== {path} ===")
    print(f"Extracted characters: {len(extracted_text)}")
    print(f"Detected matches: {len(matches)}")

    if counts:
        print("Counts by code:")
        for code in sorted(counts):
            print(f"- {code}: {counts[code]}")
    else:
        print(
            "No supported registration code pattern found "
            "('Código: <digits>' or report-header flow)."
        )

    if matches:
        print("Line-level matches:")
        for match in matches:
            print(f"- line {match.line_number}: code={match.code} | {match.line_text}")

    if show_text:
        print("\nExtracted text:")
        print(extracted_text)

    return 0


def main() -> int:
    """Run CLI for PDF text probing and return process exit code."""

    parser = _build_parser()
    args = parser.parse_args()
    extractor = PdfTextExtractor()

    exit_code = 0
    for raw_path in args.pdf_paths:
        path = Path(raw_path)
        status = _analyze_pdf(path=path, extractor=extractor, show_text=args.show_text)
        if status != 0:
            exit_code = status
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
