package reader.experiment.architecture;

public record RouteDecision(String route, String reason, boolean cloudUsed,
                            boolean modelAvailable) {
}
