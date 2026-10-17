package reader.experiment.tika;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.regex.Pattern;

import org.apache.tika.config.TikaConfig;
import org.apache.tika.exception.TikaException;
import org.apache.tika.metadata.Metadata;
import org.apache.tika.parser.AutoDetectParser;
import org.apache.tika.parser.ParseContext;
import org.apache.tika.sax.BodyContentHandler;
import org.xml.sax.SAXException;

/** Java-native non-OCR text/metadata baseline for TECH-DOC-007-R01. */
public final class TikaStructureRunner {
    private static final Pattern SAMPLE = Pattern.compile("SELF-(001|002|003|005|006|007|008|009|010|011)");
    private static final String EXPERIMENT_ID = "TECH-DOC-007-R01-text-structure";
    private static final String CONFIG = "tika=3.2.1;parser=AutoDetectParser;ocr=false;handler=BodyContentHandler(-1)";

    private TikaStructureRunner() {}

    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            throw new IllegalArgumentException("Usage: TikaStructureRunner <sample-root> <result-dir>");
        }
        Path sampleRoot = Path.of(args[0]);
        Path resultDir = Path.of(args[1]);
        Files.createDirectories(resultDir);
        List<String> jsonResults = new ArrayList<>();
        try (var paths = Files.walk(sampleRoot)) {
            for (Path path : paths.filter(Files::isRegularFile).toList()) {
                String name = path.getFileName().toString();
                var match = SAMPLE.matcher(name);
                if (!match.find() || !(name.endsWith(".pdf") || name.endsWith(".docx") || name.endsWith(".md") || name.endsWith(".txt"))) {
                    continue;
                }
                jsonResults.add(parse(path, resultDir));
            }
        }
        String summary = "{\n" +
                "  \"experiment_id\": \"" + EXPERIMENT_ID + "\",\n" +
                "  \"parser\": \"Apache Tika\",\n" +
                "  \"parser_version\": \"3.2.1\",\n" +
                "  \"java\": \"" + escape(System.getProperty("java.version")) + "\",\n" +
                "  \"ocr_enabled\": false,\n" +
                "  \"outputs\": [\n" + String.join(",\n", jsonResults) + "\n  ],\n" +
                "  \"config_hash\": \"" + configHash() + "\",\n" +
                "  \"boundary\": \"No OCR, cloud service, vector retrieval, or QA evaluation.\"\n" +
                "}\n";
        Files.writeString(resultDir.resolve("summary.json"), summary, StandardCharsets.UTF_8);
        System.out.print(summary);
    }

    private static String parse(Path path, Path resultDir) throws IOException {
        String sampleId = path.getFileName().toString().split("[-.]", 3)[0] + "-" + path.getFileName().toString().split("[-.]", 3)[1];
        Metadata metadata = new Metadata();
        BodyContentHandler handler = new BodyContentHandler(-1);
        AutoDetectParser parser = new AutoDetectParser(TikaConfig.getDefaultConfig());
        try (InputStream input = Files.newInputStream(path)) {
            parser.parse(input, handler, metadata, new ParseContext());
        } catch (SAXException | TikaException error) {
            return failure(path, sampleId, error);
        }
        String text = handler.toString();
        Map<String, String> metadataMap = new TreeMap<>();
        for (String name : metadata.names()) {
            metadataMap.put(name, metadata.get(name));
        }
        boolean hasText = !text.isBlank();
        String status = hasText ? "scored" : "limited_no_text";
        String failureReason = hasText ? null : "Tika returned no text; likely unsupported encoding or EmptyParser path";
        StringBuilder json = new StringBuilder("    {\n");
        field(json, "sample_id", sampleId, true);
        field(json, "status", status, true);
        field(json, "format", extension(path), true);
        field(json, "parser", "Apache Tika", true);
        field(json, "parser_version", "3.2.1", true);
        field(json, "ocr_enabled", false, true);
        field(json, "config_hash", configHash(), true);
        field(json, "text_chars", text.length(), true);
        field(json, "source_path", path.toString(), true);
        field(json, "source_sha256", sha256(path), true);
        json.append("      \"query_hits\": ").append(queryHits(text)).append(",\n");
        if (failureReason == null) {
            json.append("      \"failure_reason\": null,\n");
        } else {
            field(json, "failure_reason", failureReason, true);
        }
        json.append("      \"metadata\": ").append(mapJson(metadataMap)).append(",\n");
        field(json, "text_preview", text.substring(0, Math.min(1500, text.length())), true);
        field(json, "boundary", "Text extraction and metadata only; no bbox, AST, OCR, cloud service, vector retrieval, or QA evaluation.", false);
        json.append("    }");
        Files.writeString(resultDir.resolve(sampleId + ".json"), json + "\n", StandardCharsets.UTF_8);
        return json.toString();
    }

    private static String failure(Path path, String sampleId, Exception error) {
        String sourceHash;
        try {
            sourceHash = sha256(path);
        } catch (IOException hashError) {
            sourceHash = "unavailable: " + hashError.getClass().getSimpleName();
        }
        return "    {\"sample_id\":\"" + escape(sampleId) + "\",\"status\":\"failed\",\"parser\":\"Apache Tika\",\"parser_version\":\"3.2.1\",\"ocr_enabled\":false,\"config_hash\":\"" +
                configHash() + "\",\"source_path\":\"" + escape(path.toString()) + "\",\"source_sha256\":\"" + sourceHash +
                "\",\"failure_reason\":\"" + escape(error.getClass().getSimpleName() + ": " + error) + "\"}";
    }

    private static String queryHits(String text) {
        String[] queries = {"physical_page", "heading_path", "脚注", "跨栏标题", "参考文献", "Recall@k", "合并单元格", "DOCX 标题样式", "引用定位", "block_id", "GB18030", "段落边界"};
        StringBuilder result = new StringBuilder("{");
        for (int i = 0; i < queries.length; i++) {
            if (i > 0) result.append(",");
            result.append("\"").append(escape(queries[i])).append("\":").append(text.contains(queries[i]));
        }
        return result.append("}").toString();
    }

    private static String configHash() {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(CONFIG.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception error) {
            throw new IllegalStateException(error);
        }
    }

    private static String mapJson(Map<String, String> values) {
        StringBuilder result = new StringBuilder("{");
        int index = 0;
        for (var entry : values.entrySet()) {
            if (index++ > 0) result.append(",");
            result.append("\"").append(escape(entry.getKey())).append("\":\"").append(escape(entry.getValue())).append("\"");
        }
        return result.append("}").toString();
    }

    private static void field(StringBuilder json, String key, String value, boolean comma) {
        json.append("      \"").append(escape(key)).append("\":\"").append(escape(value)).append("\"").append(comma ? ",\n" : "\n");
    }

    private static void field(StringBuilder json, String key, boolean value, boolean comma) {
        json.append("      \"").append(escape(key)).append("\":").append(value).append(comma ? ",\n" : "\n");
    }

    private static void field(StringBuilder json, String key, int value, boolean comma) {
        json.append("      \"").append(escape(key)).append("\":").append(value).append(comma ? ",\n" : "\n");
    }

    private static String extension(Path path) {
        String name = path.getFileName().toString();
        return name.substring(name.lastIndexOf('.') + 1).toUpperCase();
    }

    private static String sha256(Path path) throws IOException {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            digest.update(Files.readAllBytes(path));
            return HexFormat.of().formatHex(digest.digest());
        } catch (Exception error) {
            throw new IOException(error);
        }
    }

    private static String escape(String value) {
        StringBuilder escaped = new StringBuilder(value.length() + 16);
        for (int i = 0; i < value.length(); i++) {
            char character = value.charAt(i);
            switch (character) {
                case '\\' -> escaped.append("\\\\");
                case '"' -> escaped.append("\\\"");
                case '\b' -> escaped.append("\\b");
                case '\f' -> escaped.append("\\f");
                case '\n' -> escaped.append("\\n");
                case '\r' -> escaped.append("\\r");
                case '\t' -> escaped.append("\\t");
                default -> {
                    if (character < 0x20) {
                        escaped.append(String.format("\\u%04x", (int) character));
                    } else {
                        escaped.append(character);
                    }
                }
            }
        }
        return escaped.toString();
    }
}
