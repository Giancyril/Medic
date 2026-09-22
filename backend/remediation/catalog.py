import enum
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

class RiskTier(str, enum.Enum):
    TIER_1_LOW = "TIER_1_LOW"          # Reversible, low impact (e.g. single pod restart)
    TIER_2_MEDIUM = "TIER_2_MEDIUM"    # Capacity change (e.g. scale up)
    TIER_3_HIGH = "TIER_3_HIGH"        # Destructive or state-altering (rollback, scale down, cordon)

class RemediationAction:
    def __init__(
        self,
        action_type: str,
        name: str,
        description: str,
        risk_tier: RiskTier,
        target_resource: str,
        parameters: Dict[str, Any],
        requires_human_approval: bool,
        is_auto_executable: bool = False
    ):
        self.action_type = action_type
        self.name = name
        self.description = description
        self.risk_tier = risk_tier
        self.target_resource = target_resource
        self.parameters = parameters
        self.requires_human_approval = requires_human_approval
        self.is_auto_executable = is_auto_executable

    def generate_diff(self) -> str:
        """Generates declarative kubectl-style diff preview."""
        if self.action_type == "ROLLBACK_DEPLOYMENT":
            current_rev = self.parameters.get("current_revision", "v1.4.2")
            target_rev = self.parameters.get("target_revision", "v1.4.1")
            svc = self.parameters.get("service", "app")
            ns = self.parameters.get("namespace", "production")
            return f"""--- a/deployment/{svc} (namespace: {ns}, rev: {current_rev})
+++ b/deployment/{svc} (namespace: {ns}, rev: {target_rev})
@@ -14,3 +14,3 @@
     spec:
       containers:
-      - image: registry.internal/apps/{svc}:{current_rev}
+      - image: registry.internal/apps/{svc}:{target_rev}
         imagePullPolicy: IfNotPresent"""

        elif self.action_type == "SCALE_DEPLOYMENT":
            svc = self.parameters.get("service", "app")
            current = self.parameters.get("current_replicas", 2)
            target = self.parameters.get("target_replicas", 4)
            return f"""--- a/deployment/{svc}
+++ b/deployment/{svc}
@@ -8,3 +8,3 @@
 spec:
-  replicas: {current}
+  replicas: {target}"""

        elif self.action_type == "RESTART_POD":
            pod = self.parameters.get("pod_name", "pod-xyz")
            return f"""# kubectl delete pod {pod} --grace-period=30
# ReplicaSet controller will provision new replacement pod"""

        return "# Custom remediation action execution diff"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type,
            "name": self.name,
            "description": self.description,
            "risk_tier": self.risk_tier.value,
            "target_resource": self.target_resource,
            "parameters": self.parameters,
            "requires_human_approval": self.requires_human_approval,
            "is_auto_executable": self.is_auto_executable,
            "diff_preview": self.generate_diff()
        }

def build_remediation_action(
    action_type: str,
    service: str,
    namespace: str = "production",
    extra_params: Optional[Dict[str, Any]] = None
) -> RemediationAction:
    params = extra_params or {}
    params.setdefault("service", service)
    params.setdefault("namespace", namespace)

    if action_type == "ROLLBACK_DEPLOYMENT":
        return RemediationAction(
            action_type="ROLLBACK_DEPLOYMENT",
            name=f"Rollback {service} to previous revision",
            description=f"Roll back deployment {service} to previous known-good revision to recover from fatal crash or bad release.",
            risk_tier=RiskTier.TIER_3_HIGH,
            target_resource=f"Deployment/{service}",
            parameters=params,
            requires_human_approval=True,
            is_auto_executable=False
        )

    elif action_type == "SCALE_DEPLOYMENT":
        return RemediationAction(
            action_type="SCALE_DEPLOYMENT",
            name=f"Scale {service} replicas",
            description=f"Increase replicas for {service} to mitigate CPU or queue backlog.",
            risk_tier=RiskTier.TIER_2_MEDIUM,
            target_resource=f"Deployment/{service}",
            parameters=params,
            requires_human_approval=True,
            is_auto_executable=False
        )

    elif action_type == "RESTART_POD":
        return RemediationAction(
            action_type="RESTART_POD",
            name=f"Restart pod in {service}",
            description=f"Terminate crashed/OOMKilled pod to allow Kubernetes controller to schedule fresh container.",
            risk_tier=RiskTier.TIER_1_LOW,
            target_resource=f"Pod/{params.get('pod_name', service)}",
            parameters=params,
            requires_human_approval=False,  # Low-risk / reversible
            is_auto_executable=True
        )

    return RemediationAction(
        action_type="ESCALATE_HUMAN",
        name="Escalate to on-call engineer",
        description="Notify SRE on-call team with gathered telemetry trail.",
        risk_tier=RiskTier.TIER_1_LOW,
        target_resource=f"Service/{service}",
        parameters=params,
        requires_human_approval=False,
        is_auto_executable=True
    )
