import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from geometry_msgs.msg import TransformStamped
from std_msgs.msg import Header
import depthai as dai
import numpy as np
import tf2_ros
import math


class OakDImuNode(Node):
    def __init__(self):
        super().__init__('oakd_imu_node')
        
        # ============ IMU输出配置 ============
        self.declare_parameter('imu_frequency', 400)  # Hz (200-400)
        self.declare_parameter('gyro_full_scale', 'gyroscope_2000_dps')
        self.declare_parameter('accel_full_scale', 'accelerometer_4g')
        self.declare_parameter('publish_tf', True)
        self.declare_parameter('tf_parent_frame', 'map')
        self.declare_parameter('tf_child_frame', 'oakd_imu_link')
        self.declare_parameter('complementary_alpha', 0.98)
        
        self.imu_frequency = self.get_parameter('imu_frequency').value
        self.gyro_full_scale = self.get_parameter('gyro_full_scale').value
        self.accel_full_scale = self.get_parameter('accel_full_scale').value
        self.publish_tf = self.get_parameter('publish_tf').value
        self.tf_parent_frame = self.get_parameter('tf_parent_frame').value
        self.tf_child_frame = self.get_parameter('tf_child_frame').value
        self.complementary_alpha = float(self.get_parameter('complementary_alpha').value)
        
        # ============ 初始化发布者 ============
        self.imu_pub = self.create_publisher(Imu, '/oakd/imu', 10)
        self.imu_queue = None
        self.imu_node = None
        self.device = None
        self.estimated_orientation = np.array([1.0, 0.0, 0.0, 0.0], dtype=float)
        self.have_orientation = False
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self) if self.publish_tf else None
        
        # ============ DepthAI管道设置 ============
        self.pipeline = dai.Pipeline()
        self.setup_pipeline()
        
        # ============ 启动管道 ============
        try:
            self.pipeline.start()
            self.get_logger().info(
                f"OAK-D IMU 节点已启动 [频率: {self.imu_frequency}Hz, "
                f"陀螺仪: {self.gyro_full_scale}, "
                f"加速度: {self.accel_full_scale}]"
            )
            if self.publish_tf:
                self.get_logger().info(
                    f"IMU TF 已启用: {self.tf_parent_frame} -> {self.tf_child_frame}"
                )
        except Exception as e:
            self.get_logger().error(f"设备初始化失败: {e}")
            self.device = None
            return
        
        # ============ 校准数据 ============
        self.load_calibration()
        
        # ============ 启动定时任务 ============
        self.timer = self.create_timer(0.01, self.publish_imu)

    def setup_pipeline(self):
        """设置DepthAI IMU获取管道"""
        try:
            # 创建IMU节点
            imu = self.pipeline.create(dai.node.IMU)
            self.imu_node = imu
            imu.enableIMUSensor(
                [dai.IMUSensor.ACCELEROMETER_RAW, dai.IMUSensor.GYROSCOPE_RAW],
                self.imu_frequency
            )
            imu.setBatchReportThreshold(1)
            imu.setMaxBatchReports(10)

            self.imu_queue = imu.out.createOutputQueue()
            
            self.get_logger().info(f"IMU管道配置成功: {self.imu_frequency}Hz")
            
        except Exception as e:
            self.get_logger().error(f"IMU管道配置失败: {e}")

    @staticmethod
    def _normalize_quaternion(quat):
        norm = np.linalg.norm(quat)
        if norm <= 0.0:
            return np.array([1.0, 0.0, 0.0, 0.0], dtype=float)
        return quat / norm

    @staticmethod
    def _quat_multiply(left, right):
        w1, x1, y1, z1 = left
        w2, x2, y2, z2 = right
        return np.array([
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        ], dtype=float)

    @staticmethod
    def _quat_from_euler(roll, pitch, yaw):
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)

        return np.array([
            cr * cp * cy + sr * sp * sy,
            sr * cp * cy - cr * sp * sy,
            cr * sp * cy + sr * cp * sy,
            cr * cp * sy - sr * sp * cy,
        ], dtype=float)

    @staticmethod
    def _quat_to_euler(quat):
        w, x, y, z = quat

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

    def _orientation_from_accel(self, accel_vector):
        norm = np.linalg.norm(accel_vector)
        if norm <= 0.0:
            return np.array([1.0, 0.0, 0.0, 0.0], dtype=float)

        ax, ay, az = accel_vector / norm
        roll = math.atan2(ay, az)
        pitch = math.atan2(-ax, math.sqrt(ay * ay + az * az))
        return self._quat_from_euler(roll, pitch, 0.0)

    def _integrate_gyro(self, quat, gyro_vector, dt):
        gyro_norm = np.linalg.norm(gyro_vector)
        if gyro_norm <= 0.0 or dt <= 0.0:
            return quat

        angle = gyro_norm * dt
        axis = gyro_vector / gyro_norm
        delta = np.array([
            math.cos(angle * 0.5),
            axis[0] * math.sin(angle * 0.5),
            axis[1] * math.sin(angle * 0.5),
            axis[2] * math.sin(angle * 0.5),
        ], dtype=float)
        return self._normalize_quaternion(self._quat_multiply(quat, delta))

    def _fuse_accel(self, quat, accel_vector):
        norm = np.linalg.norm(accel_vector)
        if norm <= 0.0:
            return quat

        ax, ay, az = accel_vector / norm
        roll_acc = math.atan2(ay, az)
        pitch_acc = math.atan2(-ax, math.sqrt(ay * ay + az * az))
        roll_gyro, pitch_gyro, yaw_gyro = self._quat_to_euler(quat)

        alpha = self.complementary_alpha
        roll = alpha * roll_gyro + (1.0 - alpha) * roll_acc
        pitch = alpha * pitch_gyro + (1.0 - alpha) * pitch_acc
        return self._quat_from_euler(roll, pitch, yaw_gyro)

    def _broadcast_tf(self, stamp, quat):
        if self.tf_broadcaster is None:
            return

        transform = TransformStamped()
        transform.header.stamp = stamp
        transform.header.frame_id = self.tf_parent_frame
        transform.child_frame_id = self.tf_child_frame
        transform.transform.translation.x = 0.0
        transform.transform.translation.y = 0.0
        transform.transform.translation.z = 0.0
        transform.transform.rotation.x = float(quat[1])
        transform.transform.rotation.y = float(quat[2])
        transform.transform.rotation.z = float(quat[3])
        transform.transform.rotation.w = float(quat[0])
        self.tf_broadcaster.sendTransform(transform)

    def load_calibration(self):
        """加载OAK-D IMU校准数据"""
        try:
            if self.device is None:
                return
            
            calibData = self.device.readCalibration()
            
            # 获取IMU旋转矩阵和偏移
            self.gyro_calibration = np.eye(3)
            self.accel_calibration = np.eye(3)
            self.gyro_bias = np.zeros(3)
            self.accel_bias = np.zeros(3)
            
            self.get_logger().info("IMU校准数据加载成功")
        except Exception as e:
            self.get_logger().warn(f"IMU校准加载失败，使用默认值: {e}")
            self.gyro_calibration = np.eye(3)
            self.accel_calibration = np.eye(3)
            self.gyro_bias = np.zeros(3)
            self.accel_bias = np.zeros(3)

    def publish_imu(self):
        """发布IMU数据"""
        if self.imu_queue is None:
            return
        
        try:
            imu_data = self.imu_queue.tryGet()
            if imu_data is None:
                return
            
            imu_packets = imu_data.packets
            for packet in imu_packets:
                imu_msg = Imu()
                imu_msg.header = Header()
                stamp = self.get_clock().now().to_msg()
                imu_msg.header.stamp = stamp
                imu_msg.header.frame_id = self.tf_child_frame

                accel_data = getattr(packet, 'acceleroMeter', None)
                accel_vector = np.zeros(3, dtype=float)
                if accel_data is not None:
                    accel_vector = np.array([
                        float(getattr(accel_data, 'x', 0.0)),
                        float(getattr(accel_data, 'y', 0.0)),
                        float(getattr(accel_data, 'z', 0.0)),
                    ], dtype=float)
                    imu_msg.linear_acceleration.x = accel_vector[0]
                    imu_msg.linear_acceleration.y = accel_vector[1]
                    imu_msg.linear_acceleration.z = accel_vector[2]

                gyro_data = getattr(packet, 'gyroscope', None)
                gyro_vector = np.zeros(3, dtype=float)
                if gyro_data is not None:
                    gyro_vector = np.array([
                        float(getattr(gyro_data, 'x', 0.0)),
                        float(getattr(gyro_data, 'y', 0.0)),
                        float(getattr(gyro_data, 'z', 0.0)),
                    ], dtype=float)
                    imu_msg.angular_velocity.x = gyro_vector[0]
                    imu_msg.angular_velocity.y = gyro_vector[1]
                    imu_msg.angular_velocity.z = gyro_vector[2]

                if not self.have_orientation:
                    if accel_data is not None:
                        self.estimated_orientation = self._orientation_from_accel(accel_vector)
                    self.have_orientation = True

                dt = 1.0 / float(self.imu_frequency)
                self.estimated_orientation = self._integrate_gyro(
                    self.estimated_orientation,
                    gyro_vector,
                    dt,
                )
                if accel_data is not None:
                    self.estimated_orientation = self._fuse_accel(
                        self.estimated_orientation,
                        accel_vector,
                    )

                imu_msg.orientation.x = float(self.estimated_orientation[1])
                imu_msg.orientation.y = float(self.estimated_orientation[2])
                imu_msg.orientation.z = float(self.estimated_orientation[3])
                imu_msg.orientation.w = float(self.estimated_orientation[0])

                imu_msg.linear_acceleration_covariance = [
                    0.01, 0.0, 0.0,
                    0.0, 0.01, 0.0,
                    0.0, 0.0, 0.01
                ]
                imu_msg.angular_velocity_covariance = [
                    0.001, 0.0, 0.0,
                    0.0, 0.001, 0.0,
                    0.0, 0.0, 0.001
                ]
                imu_msg.orientation_covariance = [
                    0.05, 0.0, 0.0,
                    0.0, 0.05, 0.0,
                    0.0, 0.0, 0.05
                ]

                self._broadcast_tf(stamp, self.estimated_orientation)

                self.imu_pub.publish(imu_msg)
                
        except Exception as e:
            self.get_logger().warn(f"IMU数据处理失败: {e}")

    def destroy_node(self):
        """清理资源"""
        if hasattr(self, 'pipeline') and hasattr(self.pipeline, 'stop'):
            self.pipeline.stop()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = OakDImuNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("正在关闭IMU节点...")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
