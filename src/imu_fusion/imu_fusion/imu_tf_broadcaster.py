import rclpy
from geometry_msgs.msg import TransformStamped
from rclpy.node import Node
from sensor_msgs.msg import Imu
import tf2_ros

"""
IMU TF Broadcaster - Publish orientation as TF transform

This node converts IMU orientation estimates into TF transforms.
It supports both single and multiple IMU setups.

Single IMU mode (default):
  Subscribes to: /imu
  Publishes: map -> imu_link

Multi-IMU mode:
  Run multiple instances with different topic/frame configurations:
    - imu_tf_broadcaster_0: /imu_0 -> map/imu_0_link
    - imu_tf_broadcaster_1: /imu_1 -> map/imu_1_link
    - imu_tf_broadcaster_2: /imu_2 -> map/imu_2_link

Configuration parameters:
  - input_topic: Fused IMU topic name (default: /imu)
  - parent_frame: Parent frame for TF (default: map)
  - child_frame: Child frame for TF (default: imu_link)
  - use_message_frame_id: Use msg.header.frame_id instead of child_frame (default: false)
"""


class ImuTfBroadcaster(Node):
    def __init__(self):
        super().__init__('imu_tf_broadcaster')

        self.declare_parameter('input_topic', '/oakd/imu/fused')
        self.declare_parameter('parent_frame', 'map')
        self.declare_parameter('child_frame', 'imu_link')
        self.declare_parameter('use_message_frame_id', False)

        self.input_topic = self.get_parameter('input_topic').value
        self.parent_frame = self.get_parameter('parent_frame').value
        self.child_frame = self.get_parameter('child_frame').value
        self.use_message_frame_id = self.get_parameter('use_message_frame_id').value

        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)
        self.subscription = self.create_subscription(Imu, self.input_topic, self.imu_callback, 10)

        self.get_logger().info(
            f'IMU TF broadcaster started: {self.parent_frame} -> {self.child_frame}, topic={self.input_topic}'
        )

    def imu_callback(self, msg):
        # Check if orientation is valid (orientation_covariance[0] >= 0 means valid)
        # Be careful with numpy arrays - can't use them directly in boolean context
        try:
            if hasattr(msg, 'orientation_covariance') and len(msg.orientation_covariance) > 0:
                if msg.orientation_covariance[0] < 0.0:
                    return
        except (TypeError, IndexError, ValueError):
            # If we can't check covariance, still proceed (assume valid)
            pass

        child_frame = msg.header.frame_id if self.use_message_frame_id and msg.header.frame_id else self.child_frame

        transform = TransformStamped()
        transform.header.stamp = msg.header.stamp
        transform.header.frame_id = self.parent_frame
        transform.child_frame_id = child_frame
        transform.transform.translation.x = 0.0
        transform.transform.translation.y = 0.0
        transform.transform.translation.z = 0.0
        transform.transform.rotation.x = float(msg.orientation.x)
        transform.transform.rotation.y = float(msg.orientation.y)
        transform.transform.rotation.z = float(msg.orientation.z)
        transform.transform.rotation.w = float(msg.orientation.w)
        self.tf_broadcaster.sendTransform(transform)


def main(args=None):
    rclpy.init(args=args)
    node = ImuTfBroadcaster()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
