package reader.experiment;

import reader.experiment.architecture.ArchitectureCaseResult;
import reader.experiment.architecture.ArchitectureMode;
import reader.experiment.architecture.ArchitectureRouter;
import reader.experiment.architecture.GlobalArchitectureExperiment;
import reader.experiment.architecture.RouteRequest;
import reader.experiment.architecture.Sensitivity;
import reader.experiment.citation.CitationChecker;
import reader.experiment.parser.MarkdownTextParser;
import reader.experiment.record.GlobalExperimentRecordWriter;
import reader.experiment.retrieval.KeywordRetriever;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

public final class GlobalExperimentMain {
    private GlobalExperimentMain() {
    }

    public static void main(String[] args) throws Exception {
        Path input = Path.of("samples", "reading-note.md");
        String query = "统一中间表示有什么作用";
        GlobalArchitectureExperiment experiment = new GlobalArchitectureExperiment(
                new MarkdownTextParser(), new KeywordRetriever(),
                new ArchitectureRouter(), new CitationChecker());

        List<ArchitectureCaseResult> results = new ArrayList<>();
        results.add(experiment.runCase("ARCH-L-001", ArchitectureMode.LOCAL_FIRST,
                new RouteRequest(Sensitivity.ORDINARY, true, true, true),
                input, query, "LOCAL"));
        results.add(experiment.runCase("ARCH-C-001", ArchitectureMode.CLOUD_FIRST,
                new RouteRequest(Sensitivity.ORDINARY, true, true, true),
                input, query, "CLOUD_SIMULATED"));
        results.add(experiment.runCase("ARCH-H-001", ArchitectureMode.HYBRID,
                new RouteRequest(Sensitivity.SENSITIVE, true, false, true),
                input, query, "LOCAL"));
        results.add(experiment.runCase("ARCH-H-002", ArchitectureMode.HYBRID,
                new RouteRequest(Sensitivity.ORDINARY, true, true, true),
                input, query, "CLOUD_SIMULATED"));
        results.add(experiment.runCase("ARCH-H-003", ArchitectureMode.HYBRID,
                new RouteRequest(Sensitivity.ORDINARY, false, true, true),
                input, query, "LOCAL"));
        results.add(experiment.runCase("ARCH-H-004", ArchitectureMode.HYBRID,
                new RouteRequest(Sensitivity.SENSITIVE, false, false, false),
                input, query, "LOCAL"));

        Path output = Path.of("results", "TECH-ARCH-002-R01.md");
        new GlobalExperimentRecordWriter().write(output, results);
        results.forEach(result -> System.out.printf(
                "%s mode=%s route=%s evidence=%d citation=%s refused=%s routeExpected=%s%n",
                result.caseId(), result.mode(), result.decision().route(), result.evidenceCount(),
                result.citationCheck().valid() ? "PASS" : "FAIL", result.refused(), result.routeExpected()));
        System.out.println("Record: " + output);
    }
}
