package reader.experiment.evidence;

import java.util.List;

public final class EvidenceGate {
    private static final double MIN_CONFIDENCE_FOR_AUTOMATION = 0.90;

    public GateResult evaluate(EvidenceContract evidence) {
        if (evidence.stale()) {
            return new GateResult(GateDecision.REFUSE, "证据版本已过期或文档已删除");
        }
        if (!evidence.externalProcessingAllowed()) {
            return new GateResult(GateDecision.LOCAL_EVIDENCE_ONLY, "文档不允许外部处理");
        }
        List<String> missing = missingRequiredFields(evidence);
        if (!missing.isEmpty()) {
            return new GateResult(GateDecision.LOCAL_EVIDENCE_ONLY,
                    "证据契约缺少字段: " + String.join(", ", missing));
        }
        if (evidence.confidence() < MIN_CONFIDENCE_FOR_AUTOMATION
                || !evidence.riskFlags().isEmpty()) {
            return new GateResult(GateDecision.HUMAN_REVIEW,
                    "证据置信度或结构风险不足以自动生成回答");
        }
        return new GateResult(GateDecision.ALLOW_CLOUD, "证据字段完整且允许云端处理");
    }

    private List<String> missingRequiredFields(EvidenceContract evidence) {
        java.util.ArrayList<String> missing = new java.util.ArrayList<>();
        if (blank(evidence.documentId())) missing.add("document_id");
        if (blank(evidence.documentVersion())) missing.add("document_version");
        if (blank(evidence.sourceHash())) missing.add("source_hash");
        if (blank(evidence.blockId())) missing.add("block_id");
        if (blank(evidence.text())) missing.add("text");
        if (evidence.physicalPage() == null) missing.add("physical_page");
        if (blank(evidence.sectionPath())) missing.add("section_path");
        if (evidence.charStart() == null) missing.add("char_start");
        if (evidence.charEnd() == null) missing.add("char_end");
        return missing;
    }

    private boolean blank(String value) {
        return value == null || value.isBlank();
    }
}
