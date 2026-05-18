import math

import rclpy
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.time import Time
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import Header
from tf2_ros import Buffer, TransformException, TransformListener

try:
    from sensor_msgs_py import point_cloud2 as pc2
except Exception:
    pc2 = None


class PointCloudCombiner(Node):
    def __init__(self):
        super().__init__('obstacle_pointcloud_combiner')
        self.declare_parameter('primary_topic', '/oakd/points_filtered')
        self.declare_parameter('secondary_topic', '/mid360/points')
        self.declare_parameter('output_topic', '/perception/obstacle_points')
        self.declare_parameter('output_frame', 'base_link')
        self.declare_parameter('publish_rate', 10.0)
        self.declare_parameter('max_source_age_sec', 0.5)
        self.declare_parameter('transform_timeout_sec', 0.05)
        self.declare_parameter('max_points_per_cloud', 20000)

        self.latest_primary = None
        self.latest_secondary = None

        primary_topic = self.get_parameter('primary_topic').value
        secondary_topic = self.get_parameter('secondary_topic').value
        output_topic = self.get_parameter('output_topic').value

        self.pub = self.create_publisher(PointCloud2, output_topic, 10)
        self.primary_sub = self.create_subscription(
            PointCloud2, primary_topic, self.primary_callback, 10
        )
        self.secondary_sub = self.create_subscription(
            PointCloud2, secondary_topic, self.secondary_callback, 10
        )

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        publish_rate = float(self.get_parameter('publish_rate').value)
        self.timer = self.create_timer(
            max(0.01, 1.0 / publish_rate), self.publish_combined_cloud
        )

        self.get_logger().info(
            'pointcloud_combiner started: '
            f'{primary_topic} + {secondary_topic} -> {output_topic}'
        )

    def primary_callback(self, msg: PointCloud2):
        self.latest_primary = msg

    def secondary_callback(self, msg: PointCloud2):
        self.latest_secondary = msg

    def publish_combined_cloud(self):
        if pc2 is None:
            self.get_logger().error('sensor_msgs_py.point_cloud2 is unavailable')
            return

        output_frame = self.get_parameter('output_frame').value
        transform_timeout_sec = float(
            self.get_parameter('transform_timeout_sec').value
        )
        max_source_age_sec = float(self.get_parameter('max_source_age_sec').value)
        max_points_per_cloud = int(self.get_parameter('max_points_per_cloud').value)

        now = self.get_clock().now()
        points = []
        for msg in (self.latest_primary, self.latest_secondary):
            if msg is None:
                continue
            if self._message_age_sec(now, msg) > max_source_age_sec:
                continue
            points.extend(
                self._read_transformed_points(
                    msg,
                    output_frame,
                    transform_timeout_sec,
                    max_points_per_cloud,
                )
            )

        if not points:
            return

        header = Header()
        header.stamp = now.to_msg()
        header.frame_id = output_frame
        self.pub.publish(pc2.create_cloud_xyz32(header, points))

    def _read_transformed_points(
        self, msg, output_frame, transform_timeout_sec, max_points
    ):
        source_frame = msg.header.frame_id
        if not source_frame:
            self.get_logger().warning('PointCloud2 frame_id is empty; skipping cloud')
            return []

        transform = None
        if source_frame != output_frame:
            try:
                transform = self.tf_buffer.lookup_transform(
                    output_frame,
                    source_frame,
                    Time(),
                    timeout=Duration(seconds=transform_timeout_sec),
                )
            except TransformException as exc:
                self.get_logger().warning(
                    f'No TF available from {source_frame} to {output_frame}: {exc}'
                )
                return []

        try:
            source_points = pc2.read_points(
                msg, field_names=('x', 'y', 'z'), skip_nans=True
            )
        except Exception as exc:
            self.get_logger().error(f'Failed to read PointCloud2: {exc}')
            return []

        approx_count = (msg.width * msg.height) if msg.width and msg.height else 0
        stride = max(1, int(math.ceil(approx_count / max(1, max_points))))

        transformed_points = []
        for index, point in enumerate(source_points):
            if index % stride != 0:
                continue
            try:
                x = float(point[0])
                y = float(point[1])
                z = float(point[2])
            except Exception:
                continue
            if not self._is_finite_point(x, y, z):
                continue
            if transform is not None:
                x, y, z = self._apply_transform(x, y, z, transform)
                if not self._is_finite_point(x, y, z):
                    continue
            transformed_points.append((x, y, z))

        return transformed_points

    def _message_age_sec(self, now, msg):
        stamp = Time.from_msg(msg.header.stamp)
        if stamp.nanoseconds == 0:
            return 0.0
        return max(0.0, (now - stamp).nanoseconds / 1e9)

    @staticmethod
    def _is_finite_point(x, y, z):
        return not (
            math.isnan(x)
            or math.isnan(y)
            or math.isnan(z)
            or math.isinf(x)
            or math.isinf(y)
            or math.isinf(z)
        )

    @staticmethod
    def _apply_transform(x, y, z, transform):
        translation = transform.transform.translation
        rotation = transform.transform.rotation

        qw = rotation.w
        qx = rotation.x
        qy = rotation.y
        qz = rotation.z

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
    node = PointCloudCombiner()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
