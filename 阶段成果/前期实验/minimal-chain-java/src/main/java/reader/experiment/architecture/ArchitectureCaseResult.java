package reader.experiment.architecture;

import reader.experiment.model.CitationCheck;

public record ArchitectureCaseResult(String caseId, ArchitectureMode mode,
                                     RouteRequest request, RouteDecision decision,
                                     int evidenceCount, boolean refused,
                                     CitationCheck citationCheck, boolean routeExpected) {
}
