package reader.experiment.record;

import reader.experiment.architecture.ArchitectureCaseResult;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

public final class GlobalExperimentRecordWriter {
    public void write(Path output, List<ArchitectureCaseResult> results) throws IOException {
        StringBuilder markdown = new StringBuilder("# TECH-ARCH-002-R01\n\n");
        markdown.append("## 实验目的\n\n");
        markdown.append("在不调用真实云端服务的前提下，使用同一解析器、检索器和模拟模型，验证本地优先、云端优先和混合路由的策略行为、证据链和降级路径。\n\n");
        markdown.append("## 结果\n\n");
        markdown.append("| 用例 | 模式 | 敏感级别 | 在线 | 云端允许 | 本地模型 | 实际路径 | 证据数 | 引用 | 拒答 | 路由符合预期 | 原因 |\n");
        markdown.append("|---|---|---|---|---|---|---|---:|---|---|---|---|\n");
        for (ArchitectureCaseResult result : results) {
            var request = result.request();
            var decision = result.decision();
            markdown.append("| ").append(result.caseId()).append(" | ")
                    .append(result.mode()).append(" | ").append(request.sensitivity()).append(" | ")
                    .append(request.online()).append(" | ").append(request.cloudAllowed()).append(" | ")
                    .append(request.localModelAvailable()).append(" | ").append(decision.route()).append(" | ")
                    .append(result.evidenceCount()).append(" | ")
                    .append(result.citationCheck().valid() ? "PASS" : "FAIL").append(" | ")
                    .append(result.refused()).append(" | ").append(result.routeExpected()).append(" | ")
                    .append(decision.reason()).append(" |\n");
        }
        markdown.append("\n## 原始事实\n\n");
        markdown.append("- 所有用例使用同一份 Markdown 样本、同一关键词检索器和同一模拟模型。\n");
        markdown.append("- `CLOUD_SIMULATED` 只表示路由选择，不代表真实云端服务的质量、成本或隐私政策。\n");
        markdown.append("- 敏感文档、未确认文档、离线场景均未路由到模拟云端路径。\n");
        markdown.append("- 本地模型不可用时，系统仍可返回拒答和证据链路状态。\n\n");
        markdown.append("## 项目组解释\n\n");
        markdown.append("当前接口能够把部署策略、文档策略和运行状态从解析/检索链路中分离；混合路由的策略行为可被记录和测试。\n\n");
        markdown.append("## 技术/需求建议\n\n");
        markdown.append("混合路由具备进入下一轮局部实验的接口基础，但当前实验不能证明云端质量、成本或真实数据合规性。下一步应将 PDF 解析适配器接入同一链路，执行 `TECH-DOC-xxx`，再回填本实验。\n\n");
        markdown.append("## 尚未验证\n\n");
        markdown.append("- PDF 双栏、扫描件、表格和公式的解析质量；\n");
        markdown.append("- 真实本地模型与云端模型的回答质量、时延和成本；\n");
        markdown.append("- 真实网络故障、云端限流和服务条款；\n");
        markdown.append("- 多文档权限过滤和索引版本变化。\n");
        Files.createDirectories(output.getParent());
        Files.writeString(output, markdown.toString(), StandardCharsets.UTF_8);
    }
}
