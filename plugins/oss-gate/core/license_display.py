"""Bilingual explanations for deterministic license findings."""

REASONS = {
    "reviewed": ("Reviewed license classification", "검토된 라이선스 분류"),
    "missing_metadata": ("License metadata is missing; obtain the declaration", "라이선스 근거 누락: 선언 확인 필요"),
    "unclassified_spdx": (
        "Known SPDX ID, not yet classified by this policy",
        "SPDX 식별자 확인됨: 기본 정책 분류 미지원",
    ),
    "custom_license": ("Custom license: inspect the referenced text", "사용자 정의 라이선스: 원문 확인 필요"),
    "unrecognized_identifier": (
        "Identifier absent from the bundled SPDX list",
        "포함된 SPDX 목록에서 식별자 확인 불가",
    ),
    "unsupported_exception": ("Known exception, interpretation not supported", "예외 식별자 확인됨: 조건 해석 미지원"),
    "unrecognized_exception": ("Exception identifier not recognized", "예외 식별자 확인 불가"),
    "invalid_expression": ("Malformed or oversized license expression", "라이선스 표현 오류 또는 크기 제한 초과"),
    "invalid_metadata": ("Invalid license metadata format", "라이선스 메타데이터 형식 오류"),
    "selected_license_restriction": (
        "Selected policy requires additional review or restricts use",
        "선택한 정책의 추가 검토 또는 사용 제한",
    ),
}
STATUS = {
    "recorded": ("User acceptance recorded", "사용자 수용 결정 기록됨"),
    "not_matching": ("Does not match this evidence and policy", "현재 근거·정책과 일치하지 않음"),
    "evidence_unresolved": ("Unresolved license evidence remains", "미해결 라이선스 근거가 남아 있음"),
    "future_decision": ("Decision is later than the evaluation time", "평가 시점보다 이후의 결정"),
    "expired": ("Decision expired at evaluation time", "평가 시점에 만료된 결정"),
}


def explain(assessment, lang):
    column = int(lang == "ko")
    return (
        "; ".join(REASONS.get(code, (code, code))[column] for code in assessment["reasons"])
        + ". "
        + ACTIONS[assessment["category"]][column]
    )


ACTIONS = {
    "permissive": ("Retain the applicable notices and license terms.", "해당 고지와 라이선스 조건을 유지하세요."),
    "attribution": (
        "Check attribution, license links and change notices before sharing.",
        "공유 전 출처 표시·라이선스 링크·변경 고지를 확인하세요.",
    ),
    "weak-copyleft": (
        "Review modification and distribution obligations for the intended use.",
        "사용 방식에 따른 수정·배포 의무를 확인하세요.",
    ),
    "strong-copyleft": (
        "Review copyleft scope and distribution terms before adoption.",
        "도입 전 카피레프트 적용 범위와 배포 조건을 검토하세요.",
    ),
    "network-copyleft": (
        "Review network-use and source-sharing obligations.",
        "네트워크 제공과 소스 공개 의무를 검토하세요.",
    ),
    "unknown": ("Obtain or review the applicable license evidence.", "해당 라이선스 근거를 확보하고 검토하세요."),
}
