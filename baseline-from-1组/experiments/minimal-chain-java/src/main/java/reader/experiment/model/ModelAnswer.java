package reader.experiment.model;

import java.util.List;

public record ModelAnswer(String text, boolean refused, List<String> citedBlockIds) {
}
