package reader.experiment.model;

import java.nio.file.Path;
import java.util.List;

public record CanonicalDocument(String documentId, String documentVersion,
                               Path source, List<DocumentBlock> blocks) {
}
