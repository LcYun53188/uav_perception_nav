import math
from typing import Optional

import rclpy
from nav_msgs.msg import OccupancyGrid
from rclpy.node import Node


class OccupancyGridFusion(Node):
    def __init__(self):
        super().__init__('occupancy_grid_fusion')

        self.declare_parameter('dynamic_map_topic', '/local_map/sensor_occupancy')
        self.declare_parameter('static_map_topic', '/static_map/occupancy')
        self.declare_parameter('output_map_topic', '/local_map/occupancy')
        self.declare_parameter('publish_rate', 5.0)
        self.declare_parameter('dynamic_timeout_sec', 1.0)
        self.declare_parameter('occupied_threshold', 50)

        dynamic_topic = self.get_parameter('dynamic_map_topic').value
        static_topic = self.get_parameter('static_map_topic').value
        output_topic = self.get_parameter('output_map_topic').value

        self.dynamic_map: Optional[OccupancyGrid] = None
        self.static_map: Optional[OccupancyGrid] = None
        self.dynamic_stamp = None

        self.pub = self.create_publisher(OccupancyGrid, output_topic, 10)
        self.dynamic_sub = self.create_subscription(
            OccupancyGrid, dynamic_topic, self.dynamic_cb, 10
        )
        self.static_sub = self.create_subscription(
            OccupancyGrid, static_topic, self.static_cb, 1
        )

        rate = float(self.get_parameter('publish_rate').value)
        self.timer = self.create_timer(max(0.01, 1.0 / rate), self.publish_fused_map)

        self.get_logger().info(
            f'nav_mapping/occupancy_grid_fusion started, dynamic={dynamic_topic}, '
            f'static={static_topic}, output={output_topic}'
        )

    def dynamic_cb(self, msg: OccupancyGrid):
        self.dynamic_map = msg
        self.dynamic_stamp = self.get_clock().now()

    def static_cb(self, msg: OccupancyGrid):
        self.static_map = msg

    def publish_fused_map(self):
        if self.dynamic_map is None or self.dynamic_stamp is None:
            return

        timeout = float(self.get_parameter('dynamic_timeout_sec').value)
        age = (self.get_clock().now() - self.dynamic_stamp).nanoseconds / 1e9
        if age > timeout:
            self.get_logger().warn('Dynamic occupancy grid timeout; skipping fusion')
            return

        fused = OccupancyGrid()
        fused.header = self.dynamic_map.header
        fused.info = self.dynamic_map.info
        fused.data = list(self.dynamic_map.data)

        if self.static_map is not None:
            self.overlay_static_occupancy(fused, self.static_map)

        fused.header.stamp = self.get_clock().now().to_msg()
        self.pub.publish(fused)

    def overlay_static_occupancy(
        self, dynamic_grid: OccupancyGrid, static_grid: OccupancyGrid
    ):
        occupied_threshold = int(self.get_parameter('occupied_threshold').value)
        result = self.apply_static_overlay(
            dynamic_grid, static_grid, occupied_threshold
        )
        if result == 'frame_mismatch':
            self.get_logger().warn(
                'Static and dynamic map frames differ; skipping static overlay'
            )
        elif result == 'invalid_resolution':
            self.get_logger().warn('Invalid map resolution; skipping static overlay')

    @staticmethod
    def apply_static_overlay(
        dynamic_grid: OccupancyGrid,
        static_grid: OccupancyGrid,
        occupied_threshold: int,
    ) -> str:
        if dynamic_grid.header.frame_id != static_grid.header.frame_id:
            return 'frame_mismatch'

        dyn_res = float(dynamic_grid.info.resolution)
        dyn_width = int(dynamic_grid.info.width)
        dyn_height = int(dynamic_grid.info.height)
        dyn_origin_x = dynamic_grid.info.origin.position.x
        dyn_origin_y = dynamic_grid.info.origin.position.y

        static_res = float(static_grid.info.resolution)
        static_width = int(static_grid.info.width)
        static_height = int(static_grid.info.height)
        static_origin_x = static_grid.info.origin.position.x
        static_origin_y = static_grid.info.origin.position.y

        if dyn_res <= 0.0 or static_res <= 0.0:
            return 'invalid_resolution'

        for dyn_y in range(dyn_height):
            world_y = dyn_origin_y + (dyn_y + 0.5) * dyn_res
            static_y = int(math.floor((world_y - static_origin_y) / static_res))
            if static_y < 0 or static_y >= static_height:
                continue

            for dyn_x in range(dyn_width):
                world_x = dyn_origin_x + (dyn_x + 0.5) * dyn_res
                static_x = int(math.floor((world_x - static_origin_x) / static_res))
                if static_x < 0 or static_x >= static_width:
                    continue

                static_value = static_grid.data[static_y * static_width + static_x]
                if static_value >= occupied_threshold:
                    dynamic_grid.data[dyn_y * dyn_width + dyn_x] = 100

        return 'ok'


def main(args=None):
    rclpy.init(args=args)
    node = OccupancyGridFusion()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
