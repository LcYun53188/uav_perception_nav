import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu

"""
IMU Fusion Node - Complementary Filtering for Multiple IMUs

This node implements a complementary filter to fuse raw IMU data (accel + gyro)
into orientation estimates. It supports both single and multiple IMU setups.

Single IMU mode (default):
  Subscribes to: /imu/raw
  Publishes to: /imu
  Frame ID: imu_link

Multi-IMU mode:
  Run multiple instances with different topic/frame configurations:
    - imu_fusion_node_0: /imu_0/raw -> /imu_0, frame_id=imu_0_link
    - imu_fusion_node_1: /imu_1/raw -> /imu_1, frame_id=imu_1_link
    - imu_fusion_node_2: /imu_2/raw -> /imu_2, frame_id=imu_2_link

Configuration parameters:
  - input_topic: Raw IMU topic name (default: /imu/raw)
  - output_topic: Fused IMU topic name (default: /imu)
  - frame_id: Frame identifier (default: imu_link)
  - complementary_alpha: Filter blend factor (default: 0.98)
    * Higher alpha → trust gyro more
    * Lower alpha → trust accel more
  - fallback_rate_hz: Fallback frequency when timestamps unavailable (default: 400Hz)
"""


class ImuFusionNode(Node):
    def __init__(self):
        super().__init__('imu_fusion_node')

        self.declare_parameter('input_topic', '/imu/raw')
        self.declare_parameter('output_topic', '/imu')
        self.declare_parameter('frame_id', 'imu_link')
        self.declare_parameter('complementary_alpha', 0.98)
        self.declare_parameter('fallback_rate_hz', 400.0)

        self.input_topic = self.get_parameter('input_topic').value
        self.output_topic = self.get_parameter('output_topic').value
        self.frame_id = self.get_parameter('frame_id').value
        self.complementary_alpha = float(self.get_parameter('complementary_alpha').value)
        self.fallback_rate_hz = float(self.get_parameter('fallback_rate_hz').value)

        self.publisher = self.create_publisher(Imu, self.output_topic, 10)
        self.subscription = self.create_subscription(Imu, self.input_topic, self.imu_callback, 10)

        self.orientation = [1.0, 0.0, 0.0, 0.0]
        self.have_orientation = False
        self.last_stamp_ns = None

        self.get_logger().info(
            f'IMU fusion node started: {self.input_topic} -> {self.output_topic}, frame={self.frame_id}'
        )

    @staticmethod
    def _normalize(quaternion):
        norm = math.sqrt(sum(component * component for component in quaternion))
        if norm <= 0.0:
            return [1.0, 0.0, 0.0, 0.0]
        return [component / norm for component in quaternion]

    @staticmethod
    def _multiply(left, right):
        w1, x1, y1, z1 = left
        w2, x2, y2, z2 = right
        return [
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        ]

    @staticmethod
    def _from_euler(roll, pitch, yaw):
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)

        return [
            cr * cp * cy + sr * sp * sy,
            sr * cp * cy - cr * sp * sy,
            cr * sp * cy + sr * cp * sy,
            cr * cp * sy - sr * sp * cy,
        ]

    @staticmethod
    def _to_euler(quaternion):
        w, x, y, z = quaternion

        sinr_cosp = 2.0 * (w * x + y * z)
        cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
        roll = math.atan2(sinr_cosp, cosr_cosp)

        sinp = 2.0 * (w * y - z * x)
        if abs(sinp) >= 1.0:
            pitch = math.copysign(math.pi / 2.0, sinp)
        else:
            pitch = math.asin(sinp)

        siny_cosp = 2.0 * (w * z + x * y)
        cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
        yaw = math.atan2(siny_cosp, cosy_cosp)

        return roll, pitch, yaw

    @staticmethod
    def _from_accel(ax, ay, az):
        norm = math.sqrt(ax * ax + ay * ay + az * az)
        if norm <= 0.0:
            return [1.0, 0.0, 0.0, 0.0]

        ax /= norm
        ay /= norm
        az /= norm
        roll = math.atan2(ay, az)
        pitch = math.atan2(-ax, math.sqrt(ay * ay + az * az))
        return ImuFusionNode._from_euler(roll, pitch, 0.0)

    def _integrate_gyro(self, quaternion, gx, gy, gz, dt):
        gyro_norm = math.sqrt(gx * gx + gy * gy + gz * gz)
        if gyro_norm <= 0.0 or dt <= 0.0:
            return quaternion

        angle = gyro_norm * dt
        axis_x = gx / gyro_norm
        axis_y = gy / gyro_norm
        axis_z = gz / gyro_norm
        delta = [
            math.cos(angle * 0.5),
            axis_x * math.sin(angle * 0.5),
            axis_y * math.sin(angle * 0.5),
            axis_z * math.sin(angle * 0.5),
        ]
        return self._normalize(self._multiply(quaternion, delta))

    def _fuse_accel(self, quaternion, ax, ay, az):
        norm = math.sqrt(ax * ax + ay * ay + az * az)
        if norm <= 0.0:
            return quaternion

        ax /= norm
        ay /= norm
        az /= norm
        roll_acc = math.atan2(ay, az)
        pitch_acc = math.atan2(-ax, math.sqrt(ay * ay + az * az))
        roll_gyro, pitch_gyro, yaw_gyro = self._to_euler(quaternion)

        alpha = self.complementary_alpha
        roll = alpha * roll_gyro + (1.0 - alpha) * roll_acc
        pitch = alpha * pitch_gyro + (1.0 - alpha) * pitch_acc
        return self._from_euler(roll, pitch, yaw_gyro)

    def imu_callback(self, msg):
        ax = float(msg.linear_acceleration.x)
        ay = float(msg.linear_acceleration.y)
        az = float(msg.linear_acceleration.z)
        gx = float(msg.angular_velocity.x)
        gy = float(msg.angular_velocity.y)
        gz = float(msg.angular_velocity.z)

        current_stamp_ns = msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec
        if self.last_stamp_ns is None:
            dt = 1.0 / self.fallback_rate_hz
        else:
            dt = max((current_stamp_ns - self.last_stamp_ns) * 1e-9, 1.0 / self.fallback_rate_hz)
        self.last_stamp_ns = current_stamp_ns

        if not self.have_orientation:
            self.orientation = self._from_accel(ax, ay, az)
            self.have_orientation = True

        self.orientation = self._integrate_gyro(self.orientation, gx, gy, gz, dt)
        self.orientation = self._fuse_accel(self.orientation, ax, ay, az)

        fused = Imu()
        fused.header.stamp = msg.header.stamp
        fused.header.frame_id = self.frame_id
        fused.linear_acceleration.x = ax
        fused.linear_acceleration.y = ay
        fused.linear_acceleration.z = az
        fused.angular_velocity.x = gx
        fused.angular_velocity.y = gy
        fused.angular_velocity.z = gz
        fused.orientation.x = self.orientation[1]
        fused.orientation.y = self.orientation[2]
        fused.orientation.z = self.orientation[3]
        fused.orientation.w = self.orientation[0]
        fused.linear_acceleration_covariance = [
            0.01, 0.0, 0.0,
            0.0, 0.01, 0.0,
            0.0, 0.0, 0.01,
        ]
        fused.angular_velocity_covariance = [
            0.001, 0.0, 0.0,
            0.0, 0.001, 0.0,
            0.0, 0.0, 0.001,
        ]
        fused.orientation_covariance = [
            0.05, 0.0, 0.0,
            0.0, 0.05, 0.0,
            0.0, 0.0, 0.05,
        ]
        self.publisher.publish(fused)


def main(args=None):
    rclpy.init(args=args)
    node = ImuFusionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
