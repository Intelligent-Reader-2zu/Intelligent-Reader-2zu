package reader.experiment;

import reader.experiment.architecture.CloudCallStatus;
import reader.experiment.architecture.CloudQaResult;
import reader.experiment.architecture.CloudQaSimulator;
import reader.experiment.evidence.EvidenceContract;
import reader.experiment.evidence.EvidenceGate;
import reader.experiment.evidence.GateResult;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

public final class EvidenceGateExperimentMain {
    private EvidenceGateExperimentMain() {
    }

    public static void main(String[] args) throws Exception {
        EvidenceGate gate = new EvidenceGate();
        CloudQaSimulator cloud = new CloudQaSimulator();
        List<CaseResult> results = new ArrayList<>();
        results.add(run("ARCH-GATE-001", complete(true, false, 0.98, List.of()), CloudCallStatus.SUCCESS, gate, cloud));
        results.add(run("ARCH-GATE-002", complete(true, false, 0.98, List.of()).withMissingSourceHash(), CloudCallStatus.SUCCESS, gate, cloud));
        results.add(run("ARCH-GATE-003", complete(false, false, 0.98, List.of()), CloudCallStatus.SUCCESS, gate, cloud));
        results.add(run("ARCH-GATE-004", complete(true, false, 0.72, List.of("ocr_low_confidence")), CloudCallStatus.SUCCESS, gate, cloud));
        results.add(run("ARCH-GATE-005", complete(true, true, 0.98, List.of()), CloudCallStatus.SUCCESS, gate, cloud));
        results.add(run("ARCH-GATE-006", complete(true, false, 0.98, List.of()), CloudCallStatus.FORBIDDEN, gate, cloud));

        Path output = Path.of("results", "TECH-ARCH-003-R01.md");
        write(output, results);
        results.forEach(result -> System.out.printf(
                "%s gate=%s cloud=%s fallback=%s%n", result.caseId(),
                result.gate().decision(), result.cloud().status(), result.cloud().fallback()));
        System.out.println("Record: " + output);
    }

    private static CaseResult run(String caseId, EvidenceContract evidence,
                                  CloudCallStatus simulatedStatus, EvidenceGate gate,
                                  CloudQaSimulator cloud) {
        GateResult gateResult = gate.evaluate(evidence);
        CloudQaResult cloudResult = cloud.call(gateResult, simulatedStatus);
        return new CaseResult(caseId, evidence, gateResult, cloudResult);
    }

    private static EvidenceContract complete(boolean externalAllowed, boolean stale,
                                             double confidence, List<String> risks) {
        return new EvidenceContract("DOC-001", "v1", "sha256-demo", "DOC-001-B1",
                "统一中间表示用于隔离解析和下游模块。", 1, "架构 > 中间表示",
                0, 24, externalAllowed, stale, confidence, risks);
    }

    private static void write(Path output, List<CaseResult> results) throws Exception {
        StringBuilder text = new StringBuilder("# TECH-ARCH-003-R01 Evidence Contract 门控实验\n\n");
        text.append("本实验不调用真实云端服务，也不部署本地生成模型；只验证证据契约、云端准入和失败降级。\n\n");
        text.append("| 用例 | 门控决定 | 模拟云端状态 | 降级动作 |\n|---|---|---|---|\n");
        for (CaseResult result : results) {
            text.append("| ").append(result.caseId()).append(" | ")
                    .append(result.gate().decision()).append(" | ")
                    .append(result.cloud().status()).append(" | ")
                    .append(result.cloud().fallback()).append(" |\n");
        }
        text.append("\n## 阶段性结论\n\n");
        text.append("- 完整、已授权且高置信度证据才进入模拟云端路径。\n");
        text.append("- 缺少版本、源哈希或定位字段时不调用云端，退回本地证据。\n");
        text.append("- 敏感、stale、低置信度或结构风险证据不自动生成回答。\n");
        text.append("- 云端拒绝/不可用时保留本地证据和原文阅读。\n");
        text.append("- 本实验不能证明真实云端模型质量、费用、时延或合规性。\n");
        Files.createDirectories(output.getParent());
        Files.writeString(output, text.toString(), StandardCharsets.UTF_8);
    }

    private record CaseResult(String caseId, EvidenceContract evidence,
                              GateResult gate, CloudQaResult cloud) {
    }

}
