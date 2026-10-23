package reader.experiment.retrieval;

import reader.experiment.model.CanonicalDocument;
import reader.experiment.model.Evidence;

import java.util.List;

public interface Retriever {
    List<Evidence> retrieve(CanonicalDocument document, String query, int topK);
}
