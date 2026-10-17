package reader.experiment.cloud;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Small dependency-free parser for the JSONL envelope emitted by codex exec --json. */
public final class CodexCliEventParser {
    private static final Pattern STATUS = Pattern.compile("\\\"status\\\"\\s*:\\s*\\\"([^\\\"]+)\\\"");
    private static final Pattern CITATIONS = Pattern.compile("\\\"citations\\\"\\s*:\\s*\\[([^]]*)\\]", Pattern.DOTALL);
    private static final Pattern STRING = Pattern.compile("\\\"((?:\\\\.|[^\\\"])*)\\\"");

    private CodexCliEventParser() {
    }

    public static ParsedEvents parseEvents(String stdout) {
        int eventCount = 0;
        String finalText = "";
        if (stdout == null || stdout.isBlank()) return new ParsedEvents(0, "");
        for (String line : stdout.split("\\R")) {
            if (line.isBlank()) continue;
            String trimmed = line.trim();
            if (!trimmed.startsWith("{")) continue;
            eventCount++;
            if (trimmed.contains("agent_message") && trimmed.contains("\"text\"")) {
                String text = extractStringValue(trimmed, "text");
                if (text != null) finalText = text;
            }
        }
        return new ParsedEvents(eventCount, finalText);
    }

    public static ParsedAnswer parseAnswer(String text) {
        String json = objectSlice(text);
        if (json == null) return new ParsedAnswer(false, null, List.of());
        Matcher status = STATUS.matcher(json);
        String answerStatus = status.find() ? status.group(1) : null;
        Matcher citations = CITATIONS.matcher(json);
        List<String> ids = new ArrayList<>();
        if (citations.find()) {
            Matcher strings = STRING.matcher(citations.group(1));
            while (strings.find()) ids.add(unescape(strings.group(1)));
        }
        boolean valid = answerStatus != null &&
                (json.contains("\"answer\"") || json.contains("\"citations\""));
        return new ParsedAnswer(valid, answerStatus, List.copyOf(ids));
    }

    private static String objectSlice(String text) {
        if (text == null || text.isBlank()) return null;
        int start = text.indexOf('{');
        int end = text.lastIndexOf('}');
        return start >= 0 && end > start ? text.substring(start, end + 1) : null;
    }

    private static String extractStringValue(String json, String key) {
        String needle = "\"" + key + "\"";
        int keyStart = json.indexOf(needle);
        if (keyStart < 0) return null;
        int colon = json.indexOf(':', keyStart + needle.length());
        if (colon < 0) return null;
        int quote = json.indexOf('\"', colon + 1);
        if (quote < 0) return null;
        StringBuilder value = new StringBuilder();
        boolean escaped = false;
        for (int i = quote + 1; i < json.length(); i++) {
            char ch = json.charAt(i);
            if (escaped) {
                value.append(switch (ch) {
                    case 'n' -> '\n'; case 'r' -> '\r'; case 't' -> '\t';
                    case 'b' -> '\b'; case 'f' -> '\f';
                    case 'u' -> {
                        if (i + 4 < json.length()) {
                            String hex = json.substring(i + 1, i + 5);
                            i += 4;
                            yield (char) Integer.parseInt(hex, 16);
                        }
                        yield 'u';
                    }
                    default -> ch;
                });
                escaped = false;
            } else if (ch == '\\') escaped = true;
            else if (ch == '\"') return value.toString();
            else value.append(ch);
        }
        return null;
    }

    private static String unescape(String value) {
        return value.replace("\\\"", "\"").replace("\\\\", "\\");
    }

    public record ParsedEvents(int eventCount, String finalText) {}
    public record ParsedAnswer(boolean valid, String status, List<String> citationIds) {}
}
