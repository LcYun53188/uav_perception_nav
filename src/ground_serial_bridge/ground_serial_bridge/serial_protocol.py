from dataclasses import dataclass
import struct
from typing import List, Optional


HEADER = b"\xAA\x55"
FRAME_TYPE_CMD_VEL = 0x01
FRAME_TYPE_STATUS = 0x81


@dataclass(frozen=True)
class BaseCommand:
    vx_mps: float
    vy_mps: float
    wz_radps: float
    enable: bool
    estop: bool


@dataclass(frozen=True)
class BaseStatus:
    enabled: bool
    estop: bool
    vx_mps: float
    vy_mps: float
    wz_radps: float
    fault_code: int
    yaw_rad: Optional[float] = None


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def checksum(frame_type: int, payload: bytes) -> int:
    value = frame_type ^ len(payload)
    for byte in payload:
        value ^= byte
    return value & 0xFF


def encode_command(command: BaseCommand) -> bytes:
    vx_mm_s = int(round(command.vx_mps * 1000.0))
    vy_mm_s = int(round(command.vy_mps * 1000.0))
    wz_mrad_s = int(round(command.wz_radps * 1000.0))
    payload = struct.pack(
        "<hhhBB",
        clamp(vx_mm_s, -32768, 32767),
        clamp(vy_mm_s, -32768, 32767),
        clamp(wz_mrad_s, -32768, 32767),
        1 if command.enable else 0,
        1 if command.estop else 0,
    )
    return (
        HEADER
        + bytes([FRAME_TYPE_CMD_VEL, len(payload)])
        + payload
        + bytes([checksum(FRAME_TYPE_CMD_VEL, payload)])
    )


def decode_status_payload(payload: bytes) -> BaseStatus:
    if len(payload) == 10:
        enabled, estop, vx_mm_s, vy_mm_s, wz_mrad_s, fault_code = struct.unpack(
            "<BBhhhH", payload
        )
        yaw_rad = None
    elif len(payload) == 12:
        (
            enabled,
            estop,
            vx_mm_s,
            vy_mm_s,
            wz_mrad_s,
            fault_code,
            yaw_mrad,
        ) = struct.unpack("<BBhhhHh", payload)
        yaw_rad = yaw_mrad / 1000.0
    else:
        raise ValueError(f"status payload length must be 10 or 12 bytes, got {len(payload)}")

    return BaseStatus(
        enabled=bool(enabled),
        estop=bool(estop),
        vx_mps=vx_mm_s / 1000.0,
        vy_mps=vy_mm_s / 1000.0,
        wz_radps=wz_mrad_s / 1000.0,
        fault_code=int(fault_code),
        yaw_rad=yaw_rad,
    )


class FrameParser:
    def __init__(self):
        self.buffer = bytearray()

    def feed(self, data: bytes) -> List[BaseStatus]:
        self.buffer.extend(data)
        statuses = []

        while True:
            header_index = self.buffer.find(HEADER)
            if header_index < 0:
                self.buffer.clear()
                break
            if header_index > 0:
                del self.buffer[:header_index]
            if len(self.buffer) < 5:
                break

            frame_type = self.buffer[2]
            payload_len = self.buffer[3]
            frame_len = 2 + 1 + 1 + payload_len + 1
            if len(self.buffer) < frame_len:
                break

            payload = bytes(self.buffer[4 : 4 + payload_len])
            expected_checksum = self.buffer[4 + payload_len]
            del self.buffer[:frame_len]

            if checksum(frame_type, payload) != expected_checksum:
                continue
            if frame_type != FRAME_TYPE_STATUS:
                continue

            statuses.append(decode_status_payload(payload))

        return statuses
