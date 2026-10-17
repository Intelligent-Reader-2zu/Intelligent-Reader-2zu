package reader.experiment.architecture;

import reader.experiment.evidence.GateDecision;
import reader.experiment.evidence.GateResult;

public final class CloudQaSimulator {
    public CloudQaResult call(GateResult gate, CloudCallStatus simulatedStatus) {
        if (gate.decision() != GateDecision.ALLOW_CLOUD) {
            return new CloudQaResult(CloudCallStatus.NOT_CALLED,
                    "保留本地证据、原文阅读或人工复核");
        }
        if (simulatedStatus == CloudCallStatus.SUCCESS) {
            return new CloudQaResult(CloudCallStatus.SUCCESS, "无");
        }
        return new CloudQaResult(simulatedStatus, "云端失败，退回本地证据和原文阅读");
    }
}
