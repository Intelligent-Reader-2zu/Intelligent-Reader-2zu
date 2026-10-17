package reader.experiment.model;

import java.util.List;

public record CitationCheck(boolean valid, List<String> problems) {
}
