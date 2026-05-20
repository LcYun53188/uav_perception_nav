import math

import rclpy
from nav_msgs.msg import OccupancyGrid
from rclpy.node import Node
from rclpy.duration import Duration
from rclpy.time import Time
from tf2_ros import Buffer, TransformException, TransformListener
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import Header

try:
    from sensor_msgs_py import point_cloud2 as pc2
except Exception:
    pc2 = None


class LocalMapBuilder(Node):
    def __init__(self):
        super().__init__('local_map_builder')
        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('pointcloud_topic', '/oakd/points_filtered')
        self.declare_parameter('output_topic', '/local_map/occupancy')
        self.declare_parameter('resolution', 0.5)
        self.declare_parameter('width', 40)
        self.declare_parameter('height', 40)
        self.declare_parameter('min_z', -1.0)
        self.declare_parameter('max_z', 2.0)
        self.declare_parameter('inflation_radius', 0.5)
        self.declare_parameter('publish_rate', 1.0)
        self.declare_parameter('transform_timeout_sec', 0.2)

        pointcloud_topic = self.get_parameter('pointcloud_topic').value
        output_topic = self.get_parameter('output_topic').value

        self.pub = self.create_publisher(OccupancyGrid, output_topic, 10)
        self.sub = self.create_subscription(
            PointCloud2, pointcloud_topic, self.pc_callback, 10
        )
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        rate = float(self.get_parameter('publish_rate').value)
        self.timer = self.create_timer(max(0.01, 1.0 / rate), self.publish_map)
        self.last_pc = None

        self.get_logger().info(
            f'nav_mapping/local_map_builder started, subscribing to {pointcloud_topic}, '
            f'publishing {output_topic}'
        )

    def pc_callback(self, msg: PointCloud2):
        self.last_pc = msg

    def publish_map(self):
        resolution = float(self.get_parameter('resolution').value)
        width = int(self.get_parameter('width').value)
        height = int(self.get_parameter('height').value)
        frame_id = self.get_parameter('frame_id').value
        min_z = float(self.get_parameter('min_z').value)
        max_z = float(self.get_parameter('max_z').value)
        inflation_radius = float(self.get_parameter('inflation_radius').value)
        transform_timeout_sec = float(self.get_parameter('transform_timeout_sec').value)

        grid = OccupancyGrid()
        grid.header = Header()
        grid.header.stamp = self.get_clock().now().to_msg()
        grid.header.frame_id = frame_id
        grid.info.resolution = resolution
        grid.info.width = width
        grid.info.height = height

        origin_x = -(width * resolution) / 2.0
        origin_y = -(height * resolution) / 2.0
        grid.info.origin.position.x = origin_x
        grid.info.origin.position.y = origin_y
        grid.info.origin.orientation.w = 1.0

        data = [0] * (width * height)

        if self.last_pc is None:
            grid.data = data
            self.pub.publish(grid)
            return

        if pc2 is None:
            self.get_logger().error('sensor_msgs_py.point_cloud2 is unavailable')
            grid.data = data
            self.pub.publish(grid)
            return

        source_frame = self.last_pc.header.frame_id
        if not source_frame:
            self.get_logger().warning('PointCloud2 frame_id is empty; cannot transform points')
            grid.data = data
            self.pub.publish(grid)
            return

        try:
            transform = self.tf_buffer.lookup_transform(
                frame_id,
                source_frame,
                Time(),
                timeout=Duration(seconds=transform_timeout_sec),
            )
        except TransformException as exc:
            self.get_logger().warning(
                f'No TF available from {source_frame} to {frame_id}: {exc}'
            )
            grid.data = data
            self.pub.publish(grid)
            return

        occupied = set()
        try:
            points = pc2.read_points(self.last_pc, field_names=('x', 'y', 'z'), skip_nans=True)
        except Exception as exc:
            self.get_logger().error(f'Failed to read PointCloud2: {exc}')
            grid.data = data
            self.pub.publish(grid)
            return

        for point in points:
            try:
                x = float(point[0])
                y = float(point[1])
                z = float(point[2])
            except Exception:
                continue

            if math.isnan(x) or math.isnan(y) or math.isnan(z):
                continue
            if math.isinf(x) or math.isinf(y) or math.isinf(z):
                continue

            transformed = self._apply_transform(x, y, z, transform)
            if transformed is None:
                continue

            tx, ty, tz = transformed
            if math.isnan(tx) or math.isnan(ty) or math.isnan(tz):
                continue
            if math.isinf(tx) or math.isinf(ty) or math.isinf(tz):
                continue
            if tz < min_z or tz > max_z:
                continue

            ix = int((tx - origin_x) / resolution)
            iy = int((ty - origin_y) / resolution)
            if ix < 0 or ix >= width or iy < 0 or iy >= height:
                continue
            occupied.add((ix, iy))

        inflation_cells = max(0, int(math.ceil(inflation_radius / resolution)))
        for ix, iy in occupied:
            for dx in range(-inflation_cells, inflation_cells + 1):
                for dy in range(-inflation_cells, inflation_cells + 1):
                    nx = ix + dx
                    ny = iy + dy
                    if nx < 0 or nx >= width or ny < 0 or ny >= height:
                        continue
                    data[ny * width + nx] = 100

        grid.data = data
        self.pub.publish(grid)

    @staticmethod
    def _apply_transform(x, y, z, transform):
        translation = transform.transform.translation
        rotation = transform.transform.rotation

        qw = rotation.w
        qx = rotation.x
        qy = rotation.y
        qz = rotation.z

        # Rotation matrix from quaternion
        r00 = 1.0 - 2.0 * (qy * qy + qz * qz)
        r01 = 2.0 * (qx * qy - qz * qw)
        r02 = 2.0 * (qx * qz + qy * qw)
        r10 = 2.0 * (qx * qy + qz * qw)
        r11 = 1.0 - 2.0 * (qx * qx + qz * qz)
        r12 = 2.0 * (qy * qz - qx * qw)
        r20 = 2.0 * (qx * qz - qy * qw)
        r21 = 2.0 * (qy * qz + qx * qw)
        r22 = 1.0 - 2.0 * (qx * qx + qy * qy)

        tx = r00 * x + r01 * y + r02 * z + translation.x
        ty = r10 * x + r11 * y + r12 * z + translation.y
        tz = r20 * x + r21 * y + r22 * z + translation.z
        return tx, ty, tz


def main(args=None):
    rclpy.init(args=args)
    node = LocalMapBuilder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
