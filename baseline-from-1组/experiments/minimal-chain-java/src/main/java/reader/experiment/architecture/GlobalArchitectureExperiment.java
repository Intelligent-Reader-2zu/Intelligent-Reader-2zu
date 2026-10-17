package reader.experiment.architecture;

import reader.experiment.citation.CitationChecker;
import reader.experiment.model.CanonicalDocument;
import reader.experiment.model.Evidence;
import reader.experiment.model.ModelAnswer;
import reader.experiment.modeladapter.MockModelAdapter;
import reader.experiment.parser.DocumentParser;
import reader.experiment.retrieval.Retriever;

import java.io.IOException;
import java.nio.file.Path;
import java.util.List;

public final class GlobalArchitectureExperiment {
    private final DocumentParser parser;
    private final Retriever retriever;
    private final ArchitectureRouter router;
    private final CitationChecker citationChecker;

    public GlobalArchitectureExperiment(DocumentParser parser, Retriever retriever,
                                        ArchitectureRouter router, CitationChecker citationChecker) {
        this.parser = parser;
        this.retriever = retriever;
        this.router = router;
        this.citationChecker = citationChecker;
    }

    public ArchitectureCaseResult runCase(String caseId, ArchitectureMode mode,
                                           RouteRequest request, Path input,
                                           String query, String expectedRoute) throws IOException {
        CanonicalDocument document = parser.parse(input);
        List<Evidence> evidence = retriever.retrieve(document, query, 3);
        RouteDecision decision = router.route(mode, request);
        ModelAnswer answer = decision.modelAvailable()
                ? new MockModelAdapter().answer(query, evidence)
                : new ModelAnswer("模型不可用，退回证据展示和原文阅读。", true, List.of());
        return new ArchitectureCaseResult(caseId, mode, request, decision,
                evidence.size(), answer.refused(), citationChecker.check(answer, evidence),
                expectedRoute.equals(decision.route()));
    }
}
