package reader.experiment.record;

import reader.experiment.model.Evidence;
import reader.experiment.model.ExperimentResult;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

public final class ExperimentRecordWriter {
    public void write(Path output, ExperimentResult result) throws IOException {
        StringBuilder markdown = new StringBuilder();
        markdown.append("# ").append(result.experimentId()).append("\n\n");
        markdown.append("| 字段 | 结果 |\n|---|---|\n");
        markdown.append("| 输入文件 | ").append(result.document().source()).append(" |\n");
        markdown.append("| 文档 ID | ").append(result.document().documentId()).append(" |\n");
        markdown.append("| 查询 | ").append(result.query()).append(" |\n");
        markdown.append("| 块数量 | ").append(result.document().blocks().size()).append(" |\n");
        markdown.append("| 引用校验 | ").append(result.citationCheck().valid() ? "PASS" : "FAIL").append(" |\n\n");
        markdown.append("## 检索证据\n\n");
        for (Evidence evidence : result.evidence()) {
            markdown.append("- `").append(evidence.block().blockId()).append("` score=")
                    .append(String.format("%.3f", evidence.score()))
                    .append(" lines=").append(evidence.block().lineStart()).append("-")
                    .append(evidence.block().lineEnd()).append("\n  ")
                    .append(evidence.block().text().replace("\n", " ")).append("\n");
        }
        markdown.append("\n## 模拟回答\n\n").append(result.answer().text()).append("\n\n");
        markdown.append("## 引用校验问题\n\n");
        if (result.citationCheck().problems().isEmpty()) {
            markdown.append("无。\n");
        } else {
            result.citationCheck().problems().forEach(problem -> markdown.append("- ").append(problem).append("\n"));
        }
        markdown.append("\n## 结论\n\n");
        markdown.append("这是 Markdown/TXT + 关键词检索 + 模拟模型的基线实验，不能外推到 PDF、OCR、向量检索、本地模型或云端模型。\n");
        Files.createDirectories(output.getParent());
        Files.writeString(output, markdown.toString(), StandardCharsets.UTF_8);
    }
}
