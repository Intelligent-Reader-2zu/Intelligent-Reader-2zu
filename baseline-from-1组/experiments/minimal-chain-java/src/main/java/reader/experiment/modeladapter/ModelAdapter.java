package reader.experiment.modeladapter;

import reader.experiment.model.Evidence;
import reader.experiment.model.ModelAnswer;

import java.util.List;

public interface ModelAdapter {
    ModelAnswer answer(String question, List<Evidence> evidence);
}
