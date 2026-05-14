import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid
from geometry_msgs.msg import TwistStamped


class LocalPlanner(Node):
    def __init__(self):
        super().__init__('local_planner')
        self.declare_parameter('forward_speed', 0.5)
        self.pub = self.create_publisher(TwistStamped, '/nav/cmd_vel', 10)
        self.sub = self.create_subscription(OccupancyGrid, '/local_map/occupancy', self.map_cb, 10)

    def map_cb(self, msg: OccupancyGrid):
        # Very simple policy: if map exists, publish a small forward velocity
        twist = TwistStamped()
        twist.header = msg.header
        speed = float(self.get_parameter('forward_speed').value)
        twist.twist.linear.x = speed
        twist.twist.linear.y = 0.0
        twist.twist.linear.z = 0.0
        twist.twist.angular.z = 0.0
        self.pub.publish(twist)
        self.get_logger().debug('Published proto cmd_vel')


def main(args=None):
    rclpy.init(args=args)
    node = LocalPlanner()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
