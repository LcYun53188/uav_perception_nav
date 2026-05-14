import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from nav_msgs.msg import OccupancyGrid
from std_msgs.msg import Header
import time


class LocalMapBuilder(Node):
    def __init__(self):
        super().__init__('local_map_builder')
        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('resolution', 0.5)
        self.declare_parameter('width', 40)
        self.declare_parameter('height', 40)
        self.pub = self.create_publisher(OccupancyGrid, '/local_map/occupancy', 10)
        self.sub = self.create_subscription(PointCloud2, '/oakd/points', self.pc_callback, 10)
        self.timer = self.create_timer(1.0, self.publish_empty_map)
        self.last_pc_time = None

    def pc_callback(self, msg: PointCloud2):
        # record arrival, real processing will be added later
        self.last_pc_time = self.get_clock().now()

    def publish_empty_map(self):
        # Prototype: publish an empty occupancy grid with configured resolution
        res = self.get_parameter('resolution').value
        w = self.get_parameter('width').value
        h = self.get_parameter('height').value
        frame_id = self.get_parameter('frame_id').value

        grid = OccupancyGrid()
        grid.header = Header()
        grid.header.stamp = self.get_clock().now().to_msg()
        grid.header.frame_id = frame_id
        grid.info.resolution = float(res)
        grid.info.width = int(w)
        grid.info.height = int(h)
        grid.info.origin.position.x = - (w * res) / 2.0
        grid.info.origin.position.y = - (h * res) / 2.0
        grid.info.origin.orientation.w = 1.0
        grid.data = [0] * (int(w) * int(h))

        self.pub.publish(grid)
        self.get_logger().debug('Published prototype occupancy grid')


def main(args=None):
    rclpy.init(args=args)
    node = LocalMapBuilder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
