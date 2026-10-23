package reader.experiment.architecture;

public record RouteRequest(Sensitivity sensitivity, boolean online,
                           boolean cloudAllowed, boolean localModelAvailable) {
}
