package reader.experiment.parser;

import reader.experiment.model.CanonicalDocument;
import reader.experiment.model.DocumentBlock;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.List;

public final class MarkdownTextParser implements DocumentParser {
    @Override
    public CanonicalDocument parse(Path file) throws IOException {
        List<String> lines = Files.readAllLines(file, StandardCharsets.UTF_8);
        String documentId = digest(lines.toString());
        List<DocumentBlock> blocks = new ArrayList<>();
        List<String> headings = new ArrayList<>();
        StringBuilder paragraph = new StringBuilder();
        int paragraphStart = -1;
        int blockNumber = 1;

        for (int index = 0; index < lines.size(); index++) {
            int lineNumber = index + 1;
            String line = lines.get(index);
            if (line.isBlank()) {
                if (paragraphStart >= 0) {
                    blocks.add(block(documentId, blockNumber++, "paragraph", paragraph.toString(),
                            paragraphStart, lineNumber - 1, headings));
                    paragraph.setLength(0);
                    paragraphStart = -1;
                }
                continue;
            }
            int level = headingLevel(line);
            if (level > 0) {
                if (paragraphStart >= 0) {
                    blocks.add(block(documentId, blockNumber++, "paragraph", paragraph.toString(),
                            paragraphStart, lineNumber - 1, headings));
                    paragraph.setLength(0);
                    paragraphStart = -1;
                }
                while (headings.size() >= level) {
                    headings.remove(headings.size() - 1);
                }
                headings.add(line.substring(level).trim());
                blocks.add(block(documentId, blockNumber++, "title", headings.get(headings.size() - 1),
                        lineNumber, lineNumber, String.join(" > ", headings)));
                continue;
            }
            if (paragraphStart < 0) {
                paragraphStart = lineNumber;
            } else {
                paragraph.append('\n');
            }
            paragraph.append(line.trim());
        }
        if (paragraphStart >= 0) {
            blocks.add(block(documentId, blockNumber, "paragraph", paragraph.toString(),
                    paragraphStart, lines.size(), headings));
        }
        return new CanonicalDocument(documentId, documentId, file.toAbsolutePath(), List.copyOf(blocks));
    }

    private static DocumentBlock block(String documentId, int number, String type, String text,
                                       int lineStart, int lineEnd, List<String> headings) {
        return block(documentId, number, type, text, lineStart, lineEnd, String.join(" > ", headings));
    }

    private static DocumentBlock block(String documentId, int number, String type, String text,
                                       int lineStart, int lineEnd, String headingPath) {
        return new DocumentBlock(documentId + "-b" + number, type, text,
                lineStart, lineEnd, headingPath);
    }

    private static int headingLevel(String line) {
        int count = 0;
        while (count < line.length() && line.charAt(count) == '#') {
            count++;
        }
        return count > 0 && count <= 6 && count < line.length() && line.charAt(count) == ' ' ? count : 0;
    }

    private static String digest(String value) {
        try {
            byte[] hash = MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder result = new StringBuilder();
            for (int i = 0; i < 8; i++) {
                result.append(String.format("%02x", hash[i]));
            }
            return result.toString();
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is unavailable", exception);
        }
    }
}
