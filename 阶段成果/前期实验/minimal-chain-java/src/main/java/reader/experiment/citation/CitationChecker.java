package reader.experiment.citation;

import reader.experiment.model.CitationCheck;
import reader.experiment.model.Evidence;
import reader.experiment.model.ModelAnswer;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.Stream;

public final class CitationChecker {
    public CitationCheck check(ModelAnswer answer, List<Evidence> evidence) {
        Set<String> evidenceIds = evidence.stream().map(item -> item.block().blockId()).collect(Collectors.toSet());
        Set<String> citedIds = new HashSet<>(answer.citedBlockIds());
        List<String> problems = citedIds.stream()
                .filter(id -> !evidenceIds.contains(id))
                .map(id -> "引用不在本次检索证据中: " + id)
                .toList();
        if (!answer.refused() && answer.citedBlockIds().isEmpty()) {
            problems = Stream.concat(problems.stream(), Stream.of("非拒答回答没有引用证据")).toList();
        }
        return new CitationCheck(problems.isEmpty(), problems);
    }
}
