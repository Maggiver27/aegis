from __future__ import annotations

from app.core.capabilities.capability_handler import CapabilityResult
from app.core.capabilities.capability_input import CapabilityInput
from app.core.capabilities.capability_registry import CapabilityRegistry
from app.core.logging.core_logger import CoreLogger


class ActionBus:
    """
    Action Bus executes registered capabilities through the stable
    capability contract.

    Rules:
    - accepts CapabilityInput as the execution boundary
    - resolves the handler from CapabilityRegistry
    - executes handler.handle(capability_input)
    - returns CapabilityResult
    - logs execution start and completion
    """

    def __init__(self, capability_registry: CapabilityRegistry) -> None:
        self._registry = capability_registry
        self._logger = CoreLogger(component="action_bus")

    def execute(self, capability_input: CapabilityInput) -> CapabilityResult:
        self._logger.info(
            "Executing capability",
            capability_name=capability_input.capability_name,
            request_id=capability_input.request_id,
            payload=capability_input.payload,
            metadata=capability_input.metadata,
        )

        registered_capability = self._registry.get(
            capability_input.capability_name
        )

        result = registered_capability.handler.handle(capability_input)

        self._logger.info(
            "Capability executed",
            capability_name=result.capability_name,
            request_id=capability_input.request_id,
            success=result.success,
            result_message=result.message,
            result_metadata=result.metadata,
        )

        return result