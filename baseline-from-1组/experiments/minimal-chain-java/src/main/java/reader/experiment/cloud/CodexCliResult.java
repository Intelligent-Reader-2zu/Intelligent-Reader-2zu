package reader.experiment.cloud;

import java.util.List;

/** Raw and parsed outcome of one official Codex CLI invocation. */
public record CodexCliResult(
        int exitCode,
        long elapsedMs,
        String cliError,
        int rawEventCount,
        String finalText,
        boolean jsonValid,
        String answerStatus,
        List<String> citationIds) {

    public boolean succeeded() {
        return cliError == null && exitCode == 0 && jsonValid;
    }
}
