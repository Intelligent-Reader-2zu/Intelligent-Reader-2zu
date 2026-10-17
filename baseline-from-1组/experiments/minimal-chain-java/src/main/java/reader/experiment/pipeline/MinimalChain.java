package reader.experiment.pipeline;

import reader.experiment.citation.CitationChecker;
import reader.experiment.model.CanonicalDocument;
import reader.experiment.model.CitationCheck;
import reader.experiment.model.Evidence;
import reader.experiment.model.ExperimentResult;
import reader.experiment.model.ModelAnswer;
import reader.experiment.modeladapter.ModelAdapter;
import reader.experiment.parser.DocumentParser;
import reader.experiment.retrieval.Retriever;

import java.io.IOException;
import java.nio.file.Path;
import java.util.List;

public final class MinimalChain {
    private final DocumentParser parser;
    private final Retriever retriever;
    private final ModelAdapter model;
    private final CitationChecker citationChecker;

    public MinimalChain(DocumentParser parser, Retriever retriever,
                        ModelAdapter model, CitationChecker citationChecker) {
        this.parser = parser;
        this.retriever = retriever;
        this.model = model;
        this.citationChecker = citationChecker;
    }

    public ExperimentResult run(Path input, String query, int topK) throws IOException {
        CanonicalDocument document = parser.parse(input);
        List<Evidence> evidence = retriever.retrieve(document, query, topK);
        ModelAnswer answer = model.answer(query, evidence);
        CitationCheck citationCheck = citationChecker.check(answer, evidence);
        return new ExperimentResult("TECH-ARCH-001-R01", query,
                document, evidence, answer, citationCheck);
    }
}
