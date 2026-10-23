package reader.experiment.retrieval;

import reader.experiment.model.CanonicalDocument;
import reader.experiment.model.DocumentBlock;
import reader.experiment.model.Evidence;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.Locale;
import java.util.Set;

public final class KeywordRetriever implements Retriever {
    @Override
    public java.util.List<Evidence> retrieve(CanonicalDocument document, String query, int topK) {
        Set<String> terms = terms(query);
        return document.blocks().stream()
                .map(block -> new Evidence(block, score(block, terms)))
                .filter(evidence -> evidence.score() > 0)
                .sorted(Comparator.comparingDouble(Evidence::score).reversed()
                        .thenComparing(evidence -> evidence.block().blockId()))
                .limit(topK)
                .toList();
    }

    private static double score(DocumentBlock block, Set<String> terms) {
        String text = block.text().toLowerCase(Locale.ROOT);
        long matches = terms.stream().filter(text::contains).count();
        return terms.isEmpty() ? 0 : (double) matches / terms.size();
    }

    private static Set<String> terms(String query) {
        String normalized = query.toLowerCase(Locale.ROOT);
        Set<String> terms = new LinkedHashSet<>();
        StringBuilder latinTerm = new StringBuilder();
        normalized.codePoints().forEach(codePoint -> {
            if (Character.UnicodeScript.of(codePoint) == Character.UnicodeScript.HAN) {
                flush(latinTerm, terms);
                terms.add(new String(Character.toChars(codePoint)));
            } else if (Character.isLetterOrDigit(codePoint)) {
                latinTerm.appendCodePoint(codePoint);
            } else {
                flush(latinTerm, terms);
            }
        });
        flush(latinTerm, terms);
        return terms;
    }

    private static void flush(StringBuilder term, Set<String> terms) {
        if (!term.isEmpty()) {
            terms.add(term.toString());
            term.setLength(0);
        }
    }
}
