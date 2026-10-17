package reader.experiment.model;

import java.util.List;

public record ExperimentResult(String experimentId, String query,
                               CanonicalDocument document, List<Evidence> evidence,
                               ModelAnswer answer, CitationCheck citationCheck) {
}
