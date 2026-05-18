import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import Header

try:
    from livox_ros_driver2.msg import CustomMsg
except Exception:
    CustomMsg = None

try:
    from sensor_msgs_py import point_cloud2 as pc2
except Exception:
    pc2 = None


class LivoxCustomToPointCloud2(Node):
    def __init__(self):
        super().__init__('livox_custom_to_pointcloud2')
        self.declare_parameter('input_topic', '/livox/lidar')
        self.declare_parameter('output_topic', '/mid360/points')
        self.declare_parameter('frame_id', 'mid360_link')
        self.declare_parameter('use_input_frame', False)

        if CustomMsg is None:
            raise RuntimeError(
                'livox_ros_driver2.msg.CustomMsg is unavailable. '
                'Build and source livox_ros_driver2 before starting this node.'
            )
        if pc2 is None:
            raise RuntimeError('sensor_msgs_py.point_cloud2 is unavailable')

        input_topic = self.get_parameter('input_topic').value
        output_topic = self.get_parameter('output_topic').value

        self.pub = self.create_publisher(PointCloud2, output_topic, 10)
        self.sub = self.create_subscription(
            CustomMsg, input_topic, self.callback, 10
        )
        self.get_logger().info(
            f'Converting Livox CustomMsg {input_topic} -> PointCloud2 {output_topic}'
        )

    def callback(self, msg):
        use_input_frame = bool(self.get_parameter('use_input_frame').value)
        frame_id = msg.header.frame_id if use_input_frame else self.get_parameter(
            'frame_id'
        ).value

        header = Header()
        header.stamp = msg.header.stamp
        header.frame_id = frame_id

        points = [
            (float(point.x), float(point.y), float(point.z))
            for point in msg.points
        ]
        self.pub.publish(pc2.create_cloud_xyz32(header, points))


def main(args=None):
    rclpy.init(args=args)
    node = LivoxCustomToPointCloud2()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
