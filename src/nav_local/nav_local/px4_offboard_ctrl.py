import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
from std_msgs.msg import Bool


class Px4OffboardCtrl(Node):
    def __init__(self):
        super().__init__('px4_offboard_ctrl')
        self.sub = self.create_subscription(TwistStamped, '/nav/cmd_vel', self.cmd_cb, 10)
        self.emer_sub = self.create_subscription(Bool, '/nav/emergency', self.em_cb, 10)
        self.get_logger().info('px4_offboard_ctrl started (stub)')

    def cmd_cb(self, msg: TwistStamped):
        # In a real implementation, convert Twist -> px4_msgs setpoint and send
        self.get_logger().info(f'Received cmd_vel (proto): linear.x={msg.twist.linear.x:.2f}')

    def em_cb(self, msg: Bool):
        if msg.data:
            self.get_logger().warn('Emergency signal received: consider halting or RTL')


def main(args=None):
    rclpy.init(args=args)
    node = Px4OffboardCtrl()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
