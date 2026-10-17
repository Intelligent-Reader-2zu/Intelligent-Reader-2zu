package reader.experiment.modeladapter;

import reader.experiment.model.Evidence;
import reader.experiment.model.ModelAnswer;

import java.util.List;
import java.util.stream.Collectors;

public final class MockModelAdapter implements ModelAdapter {
    @Override
    public ModelAnswer answer(String question, List<Evidence> evidence) {
        if (evidence.isEmpty()) {
            return new ModelAnswer("未找到足够的原文依据，无法回答该问题。", true, List.of());
        }
        String citations = evidence.stream()
                .map(item -> "[" + item.block().blockId() + "]")
                .collect(Collectors.joining(" "));
        String text = "基于检索到的原文证据，问题“" + question + "”可参考以下内容： "
                + evidence.get(0).block().text() + " " + citations;
        return new ModelAnswer(text, false,
                evidence.stream().map(item -> item.block().blockId()).toList());
    }
}
