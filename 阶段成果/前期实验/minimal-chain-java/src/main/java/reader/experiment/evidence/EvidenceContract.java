package reader.experiment.evidence;

import java.util.List;

public record EvidenceContract(
        String documentId,
        String documentVersion,
        String sourceHash,
        String blockId,
        String text,
        Integer physicalPage,
        String sectionPath,
        Integer charStart,
        Integer charEnd,
        boolean externalProcessingAllowed,
        boolean stale,
        double confidence,
        List<String> riskFlags) {

    public EvidenceContract withMissingSourceHash() {
        return new EvidenceContract(documentId, documentVersion, "", blockId, text,
                physicalPage, sectionPath, charStart, charEnd,
                externalProcessingAllowed, stale, confidence, riskFlags);
    }
}
