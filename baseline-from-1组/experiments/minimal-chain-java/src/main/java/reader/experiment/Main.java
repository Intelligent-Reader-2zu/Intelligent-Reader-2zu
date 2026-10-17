package reader.experiment;

import reader.experiment.citation.CitationChecker;
import reader.experiment.model.CanonicalDocument;
import reader.experiment.model.Evidence;
import reader.experiment.model.ExperimentResult;
import reader.experiment.parser.MarkdownTextParser;
import reader.experiment.pipeline.MinimalChain;
import reader.experiment.record.ExperimentRecordWriter;
import reader.experiment.retrieval.KeywordRetriever;
import reader.experiment.modeladapter.MockModelAdapter;

import java.nio.file.Path;

public final class Main {
    private Main() {
    }

    public static void main(String[] args) throws Exception {
        Path input = args.length > 0 ? Path.of(args[0]) : Path.of("samples", "reading-note.md");
        String query = args.length > 1 ? args[1] : "统一中间表示有什么作用";

        MinimalChain chain = new MinimalChain(
                new MarkdownTextParser(),
                new KeywordRetriever(),
                new MockModelAdapter(),
                new CitationChecker());
        ExperimentResult result = chain.run(input, query, 3);
        Path output = Path.of("results", "TECH-ARCH-001-R01.md");
        new ExperimentRecordWriter().write(output, result);
        printResult(result, output);
    }

    private static void printResult(ExperimentResult result, Path output) {
        System.out.println("Experiment: TECH-ARCH-001-R01");
        System.out.println("Document: " + result.document().documentId());
        System.out.println("Blocks: " + result.document().blocks().size());
        System.out.println("Query: " + result.query());
        System.out.println("Evidence:");
        for (Evidence evidence : result.evidence()) {
            System.out.printf("  [%s] score=%.3f lines=%d-%d %s%n",
                    evidence.block().blockId(), evidence.score(),
                    evidence.block().lineStart(), evidence.block().lineEnd(), evidence.block().text());
        }
        System.out.println("Answer: " + result.answer().text());
        System.out.println("Citation check: " + (result.citationCheck().valid() ? "PASS" : "FAIL"));
        System.out.println("Record: " + output);
    }
}
