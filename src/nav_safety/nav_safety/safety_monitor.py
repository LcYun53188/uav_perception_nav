import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import Bool


class SafetyMonitor(Node):
    def __init__(self):
        super().__init__('safety_monitor')
        self.declare_parameter('min_points_threshold', 10)
        self.pub = self.create_publisher(Bool, '/nav/emergency', 10)
        self.sub = self.create_subscription(PointCloud2, '/oakd/points', self.pc_cb, 10)

    def pc_cb(self, msg: PointCloud2):
        threshold = int(self.get_parameter('min_points_threshold').value)
        approx_points = (msg.width * msg.height) if (msg.width and msg.height) else 0
        emergency = approx_points < threshold
        self.pub.publish(Bool(data=emergency))
        if emergency:
            self.get_logger().warn(f'Emergency: approx_points={approx_points} < {threshold}')


def main(args=None):
    rclpy.init(args=args)
    node = SafetyMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()