from ground_serial_bridge.serial_protocol import (
    FRAME_TYPE_STATUS,
    HEADER,
    BaseCommand,
    FrameParser,
    checksum,
    encode_command,
)


def test_encode_command_frame_shape():
    frame = encode_command(
        BaseCommand(vx_mps=0.25, vy_mps=-0.1, wz_radps=0.5, enable=True, estop=False)
    )
    assert frame[:2] == HEADER
    assert frame[2] == 0x01
    assert frame[3] == 8
    assert len(frame) == 13


def test_parse_status_frame():
    payload = bytes([1, 0]) + (250).to_bytes(2, "little", signed=True)
    payload += (-100).to_bytes(2, "little", signed=True)
    payload += (500).to_bytes(2, "little", signed=True)
    payload += (0).to_bytes(2, "little", signed=False)
    frame = (
        HEADER
        + bytes([FRAME_TYPE_STATUS, len(payload)])
        + payload
        + bytes([checksum(FRAME_TYPE_STATUS, payload)])
    )

    statuses = FrameParser().feed(frame)
    assert len(statuses) == 1
    assert statuses[0].enabled is True
    assert statuses[0].estop is False
    assert statuses[0].vx_mps == 0.25
    assert statuses[0].vy_mps == -0.1
    assert statuses[0].wz_radps == 0.5
    assert statuses[0].fault_code == 0
    assert statuses[0].yaw_rad is None


def test_parse_status_frame_with_yaw():
    payload = bytes([1, 0]) + (250).to_bytes(2, "little", signed=True)
    payload += (-100).to_bytes(2, "little", signed=True)
    payload += (500).to_bytes(2, "little", signed=True)
    payload += (0).to_bytes(2, "little", signed=False)
    payload += (1570).to_bytes(2, "little", signed=True)
    frame = (
        HEADER
        + bytes([FRAME_TYPE_STATUS, len(payload)])
        + payload
        + bytes([checksum(FRAME_TYPE_STATUS, payload)])
    )

    statuses = FrameParser().feed(frame)
    assert len(statuses) == 1
    assert statuses[0].yaw_rad == 1.57
