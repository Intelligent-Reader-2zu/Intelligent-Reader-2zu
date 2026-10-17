package reader.experiment.architecture;

public final class ArchitectureRouter {
    public RouteDecision route(ArchitectureMode mode, RouteRequest request) {
        if (mode == ArchitectureMode.LOCAL_FIRST) {
            return localDecision(request, "本地优先策略");
        }
        if (!request.online()) {
            return localDecision(request, "网络不可用，切换本地路径");
        }
        if (!request.cloudAllowed()) {
            return localDecision(request, "未授权云端处理，留在本地路径");
        }
        if (request.sensitivity() != Sensitivity.ORDINARY) {
            return localDecision(request, "敏感级别未确认，禁止自动外传");
        }
        return new RouteDecision("CLOUD_SIMULATED", mode + "允许普通文档使用模拟云端路径",
                true, true);
    }

    private RouteDecision localDecision(RouteRequest request, String reason) {
        return new RouteDecision("LOCAL", reason, false, request.localModelAvailable());
    }
}
