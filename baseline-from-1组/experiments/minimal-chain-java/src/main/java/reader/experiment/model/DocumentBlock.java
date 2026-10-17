package reader.experiment.model;

public record DocumentBlock(String blockId, String type, String text,
                            int lineStart, int lineEnd, String headingPath) {
}
