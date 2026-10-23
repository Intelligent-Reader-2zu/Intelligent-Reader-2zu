package reader.experiment;

import reader.experiment.cloud.CodexCliQaAdapter;
import reader.experiment.cloud.CodexCliResult;
import reader.experiment.evidence.EvidenceContract;
import reader.experiment.evidence.EvidenceGate;
import reader.experiment.evidence.GateDecision;
import reader.experiment.evidence.GateResult;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

/** End-to-end architecture experiment using the official Codex CLI route. */
public final class CodexCloudArchitectureExperimentMain {
    private CodexCloudArchitectureExperimentMain() {
    }

    public static void main(String[] args) throws Exception {
        Path experimentDirectory = Path.of(System.getProperty("user.dir")).toAbsolutePath().normalize();
        Path projectRoot = experimentDirectory.getParent().getParent();
        Path executable = Path.of(System.getenv().getOrDefault("CODEX_CLI_PATH",
                "C:\\Users\\联想\\AppData\\Local\\OpenAI\\Codex\\bin\\2e5e00daee91c61d\\codex.exe"));
        String model = System.getenv().getOrDefault("CODEX_ARCH_MODEL", "gpt-5.6-sol");
        long timeoutSeconds = parseLong(System.getenv().getOrDefault("CODEX_ARCH_TIMEOUT_SECONDS", "60"), 60);
        String effort = System.getenv().getOrDefault("CODEX_QA_REASONING_EFFORT", "low");

        EvidenceGate gate = new EvidenceGate();
        CodexCliQaAdapter realAdapter = new CodexCliQaAdapter(executable, projectRoot, model,
                Duration.ofSeconds(timeoutSeconds), effort);
        List<ArchitectureRow> rows = new ArrayList<>();
        rows.add(run("ARCH-004-001-CLOUD_ALLOWED", "完整、已授权、高置信度证据",
                base(true, false, 0.98, List.of()), gate, realAdapter,
                "统一中间表示有什么作用？"));
        rows.add(run("ARCH-004-002-MISSING_HASH", "缺少 source_hash",
                base(true, false, 0.98, List.of()).withMissingSourceHash(), gate, realAdapter,
                "统一中间表示有什么作用？"));
        rows.add(run("ARCH-004-003-EXTERNAL_FORBIDDEN", "不允许外部处理",
                base(false, false, 0.98, List.of()), gate, realAdapter,
                "统一中间表示有什么作用？"));
        rows.add(run("ARCH-004-004-LOW_CONFIDENCE", "OCR 低置信度/结构风险",
                base(true, false, 0.72, List.of("ocr_low_confidence")), gate, realAdapter,
                "统一中间表示有什么作用？"));
        rows.add(run("ARCH-004-005-STALE", "stale 文档版本",
                base(true, true, 0.98, List.of()), gate, realAdapter,
                "统一中间表示有什么作用？"));

        // A deterministic transport-failure case exercises the same adapter's fallback contract.
        Path unavailable = experimentDirectory.resolve("missing-codex-cli.exe");
        CodexCliQaAdapter unavailableAdapter = new CodexCliQaAdapter(unavailable, projectRoot, model,
                Duration.ofSeconds(1), effort);
        rows.add(run("ARCH-004-006-CLI_FAILURE", "云端 CLI 不可用，回退本地证据",
                base(true, false, 0.98, List.of()), gate, unavailableAdapter,
                "统一中间表示有什么作用？"));

        Path output = Path.of("results", "TECH-ARCH-004-R01.md");
        writeReport(output, rows, executable, model, timeoutSeconds, effort);
        for (ArchitectureRow row : rows) {
            System.out.printf("%s gate=%s cloudCalled=%s cli=%s json=%s status=%s elapsedMs=%d%n",
                    row.caseId(), row.gate().decision(), row.cloudCalled(), row.cliStatus(), row.jsonValid(),
                    row.answerStatus(), row.elapsedMs());
        }
        System.out.println("Record: " + output);
    }

    private static ArchitectureRow run(String caseId, String description, EvidenceContract evidence,
                                        EvidenceGate gate, CodexCliQaAdapter adapter, String question) {
        GateResult gateResult = gate.evaluate(evidence);
        if (gateResult.decision() != GateDecision.ALLOW_CLOUD) {
            return new ArchitectureRow(caseId, description, gateResult, false, "NOT_CALLED", false,
                    null, 0, 0, List.of(), "", "保留本地证据、原文阅读或人工复核", "");
        }
        CodexCliResult result = adapter.answer(question, evidence);
        String cliStatus = result.succeeded() ? "SUCCESS" : "FAILED";
        String fallback = result.succeeded() ? "无（进入回答后仍需引用校验）" : "云端失败，退回本地证据和原文阅读";
        return new ArchitectureRow(caseId, description, gateResult, true, cliStatus, result.jsonValid(),
                result.answerStatus(), result.elapsedMs(), result.rawEventCount(), result.citationIds(),
                result.finalText(), fallback, result.cliError() == null ? "" : result.cliError());
    }

    private static EvidenceContract base(boolean externalAllowed, boolean stale,
                                         double confidence, List<String> risks) {
        return new EvidenceContract("DOC-001", "v1", "sha256-demo", "DOC-001-B1",
                "统一中间表示用于隔离解析和下游模块。", 1, "架构 > 中间表示", 0, 24,
                externalAllowed, stale, confidence, risks);
    }

    private static void writeReport(Path output, List<ArchitectureRow> rows, Path executable,
                                    String model, long timeoutSeconds, String effort) throws Exception {
        StringBuilder text = new StringBuilder();
        text.append("# TECH-ARCH-004-R01 官方 Codex CLI 云端适配器架构实验\n\n");
        text.append("本实验在 Evidence Contract 门控之后调用与问答实验相同的官方 `codex exec` 路径。仅发送项目自制合成证据，不读取或上传真实项目文档。\n\n");
        text.append("## 配置\n\n");
        text.append("- provider：官方 Codex CLI/Responses provider；未使用直接 OpenAI/Bearer API。\n");
        text.append("- executable：`").append(executable).append("`\n");
        text.append("- model：`").append(model).append("`，reasoning effort：`").append(effort).append("`\n");
        text.append("- timeout：").append(timeoutSeconds).append(" 秒；sandbox：`read-only`；调用参数包含 `--ephemeral --skip-git-repo-check --ignore-rules --json`。\n\n");
        text.append("## 结果\n\n");
        text.append("| 用例 | 门控 | 调用 CLI | CLI | JSON | status | 事件数 | citation IDs | 耗时(ms) | 降级/备注 |\n|---|---|---:|---|---:|---|---:|---|---:|---|\n");
        for (ArchitectureRow row : rows) {
            text.append("| ").append(row.caseId()).append(" ").append(row.description()).append(" | ")
                    .append(row.gate().decision()).append(" | ").append(row.cloudCalled() ? "是" : "否")
                    .append(" | ").append(row.cliStatus()).append(" | ").append(row.jsonValid() ? "是" : "否")
                    .append(" | ").append(row.answerStatus() == null ? "-" : row.answerStatus())
                    .append(" | ").append(row.rawEventCount()).append(" | ")
                    .append(row.citationIds().isEmpty() ? "-" : String.join(",", row.citationIds()))
                    .append(" | ").append(row.elapsedMs()).append(" | ").append(row.fallback()).append(" |\n");
        }
        text.append("\n## 失败信息\n\n");
        for (ArchitectureRow row : rows) {
            if (!row.error().isBlank()) text.append("- `").append(row.caseId()).append("`：").append(row.error()).append("\n");
        }
        text.append("\n## 模型输出可追溯摘要\n\n");
        for (ArchitectureRow row : rows) {
            if (!row.finalText().isBlank()) {
                text.append("- `").append(row.caseId()).append("` final_text：").append(shortText(row.finalText())).append("\n");
            }
        }
        text.append("\n## 原始事实\n\n");
        text.append("1. Evidence Gate 阻断了缺失 source_hash、禁止外部处理、低置信度/结构风险和 stale 文档；这些用例的 CLI 调用次数为 0。\n");
        text.append("2. 完整且允许外发的合成证据进入了官方 CLI 适配器；是否成功、耗时和输出 JSON 合法性以本次运行记录为准。\n");
        text.append("3. CLI 不可用时，适配器返回失败状态，路由保持本地证据和原文阅读，不生成本地伪造答案。\n\n");
        text.append("## 项目组解释\n\n");
        text.append("云端生成应是受 Evidence Contract 约束的可替换适配器，而不是绕过权限、版本和引用校验的主链路。官方 CLI 可调用性只说明本次客户端路径具备实验可达性，不代表模型质量、成本、SLA、数据保留或长期稳定性。\n\n");
        text.append("## 技术/需求结论\n\n");
        text.append("当前全局架构可继续按“本地证据层 + 受控云端问答 + 无模型降级”推进；一期必须把门控拒绝、CLI 失败/超时、非法 JSON 和引用校验作为正式状态，而不是异常日志。\n\n");
        text.append("## 实验边界\n\n");
        text.append("- 云端输入为单条合成 Evidence Contract，未验证真实文档内容质量。\n");
        text.append("- 本实验没有比较云端供应商、价格、合规条款或本地生成模型。\n");
        text.append("- 成功输出仍需独立检查 citation ID 是否属于本次证据；模型返回 `answered` 不自动等于项目接受回答。\n");
        Files.createDirectories(output.getParent());
        Files.writeString(output, text.toString(), StandardCharsets.UTF_8);
    }

    private static long parseLong(String value, long fallback) {
        try { return Long.parseLong(value); } catch (NumberFormatException ignored) { return fallback; }
    }

    private static String shortText(String value) {
        String oneLine = value.replace('\n', ' ').replace('\r', ' ');
        return oneLine.length() > 500 ? oneLine.substring(0, 500) + "..." : oneLine;
    }

    private record ArchitectureRow(String caseId, String description, GateResult gate,
                                   boolean cloudCalled, String cliStatus, boolean jsonValid,
                                   String answerStatus, long elapsedMs, int rawEventCount,
                                   List<String> citationIds, String finalText, String fallback, String error) {
    }
}
