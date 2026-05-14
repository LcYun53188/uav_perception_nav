import rclpy
from geometry_msgs.msg import TransformStamped
from rclpy.node import Node
from sensor_msgs.msg import Imu
import tf2_ros


class OakDImuTfBroadcaster(Node):
    def __init__(self):
        super().__init__('oakd_imu_tf_broadcaster')

        self.declare_parameter('input_topic', '/oakd/imu')
        self.declare_parameter('parent_frame', 'map')
        self.declare_parameter('child_frame', 'oakd_imu_link')
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
    node = OakDImuTfBroadcaster()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()