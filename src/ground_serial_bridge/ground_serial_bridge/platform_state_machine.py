from dataclasses import dataclass
from enum import Enum, auto


class PlatformState(Enum):
    IDLE = auto()
    ENABLE_BASE = auto()
    RUNNING = auto()
    EMERGENCY_STOP = auto()
    FAULT = auto()


@dataclass
class PlatformInputs:
    nav_cmd_active: bool = False
    emergency_active: bool = False
    serial_connected: bool = False
    base_enabled: bool = False
    cmd_timeout: bool = False
    feedback_timeout: bool = False
    fault_code: int = 0


class PlatformStateMachine:
    def __init__(self):
        self.current_state = PlatformState.IDLE
        self.previous_state = None

    def update(self, inputs: PlatformInputs) -> PlatformState:
        next_state = self.current_state

        if inputs.emergency_active:
            next_state = PlatformState.EMERGENCY_STOP
        elif inputs.fault_code != 0 or inputs.feedback_timeout:
            next_state = PlatformState.FAULT
        elif not inputs.serial_connected:
            next_state = PlatformState.IDLE
        elif self.current_state == PlatformState.IDLE:
            if inputs.nav_cmd_active:
                next_state = PlatformState.ENABLE_BASE
        elif self.current_state == PlatformState.ENABLE_BASE:
            if inputs.base_enabled:
                next_state = PlatformState.RUNNING
        elif self.current_state == PlatformState.RUNNING:
            if inputs.cmd_timeout:
                next_state = PlatformState.ENABLE_BASE
        elif self.current_state == PlatformState.EMERGENCY_STOP:
            if not inputs.emergency_active:
                next_state = PlatformState.IDLE
        elif self.current_state == PlatformState.FAULT:
            if inputs.fault_code == 0 and not inputs.feedback_timeout:
                next_state = PlatformState.IDLE

        if next_state != self.current_state:
            self.previous_state = self.current_state
            self.current_state = next_state

        return self.current_state

    @property
    def should_enable_base(self) -> bool:
        return self.current_state in (PlatformState.ENABLE_BASE, PlatformState.RUNNING)

    @property
    def should_send_motion(self) -> bool:
        return self.current_state == PlatformState.RUNNING

    @property
    def should_estop(self) -> bool:
        return self.current_state in (
            PlatformState.EMERGENCY_STOP,
            PlatformState.FAULT,
        )
