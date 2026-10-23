package reader.experiment.parser;

import reader.experiment.model.CanonicalDocument;

import java.io.IOException;
import java.nio.file.Path;

public interface DocumentParser {
    CanonicalDocument parse(Path file) throws IOException;
}
