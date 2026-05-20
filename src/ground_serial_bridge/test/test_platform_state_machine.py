from ground_serial_bridge.platform_state_machine import (
    PlatformInputs,
    PlatformState,
    PlatformStateMachine,
)


def test_state_machine_nominal_flow():
    sm = PlatformStateMachine()
    assert sm.current_state == PlatformState.IDLE

    sm.update(PlatformInputs(serial_connected=True, nav_cmd_active=True))
    assert sm.current_state == PlatformState.ENABLE_BASE

    sm.update(
        PlatformInputs(
            serial_connected=True,
            nav_cmd_active=True,
            base_enabled=True,
        )
    )
    assert sm.current_state == PlatformState.RUNNING
    assert sm.should_send_motion


def test_state_machine_emergency_overrides_motion():
    sm = PlatformStateMachine()
    sm.update(
        PlatformInputs(
            serial_connected=True,
            nav_cmd_active=True,
            base_enabled=True,
        )
    )
    sm.update(PlatformInputs(serial_connected=True, emergency_active=True))
    assert sm.current_state == PlatformState.EMERGENCY_STOP
    assert sm.should_estop
    assert not sm.should_send_motion


def test_state_machine_feedback_timeout_fault():
    sm = PlatformStateMachine()
    sm.update(
        PlatformInputs(
            serial_connected=True,
            nav_cmd_active=True,
            feedback_timeout=True,
        )
    )
    assert sm.current_state == PlatformState.FAULT
    assert sm.should_estop
