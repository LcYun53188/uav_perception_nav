from nav_msgs.msg import OccupancyGrid

from nav_mapping.occupancy_grid_fusion import OccupancyGridFusion


def make_grid(width, height, resolution, origin_x, origin_y, data):
    grid = OccupancyGrid()
    grid.header.frame_id = 'map'
    grid.info.width = width
    grid.info.height = height
    grid.info.resolution = resolution
    grid.info.origin.position.x = origin_x
    grid.info.origin.position.y = origin_y
    grid.info.origin.orientation.w = 1.0
    grid.data = data
    return grid


def test_static_occupancy_overlays_matching_world_cell():
    dynamic = make_grid(
        width=2,
        height=2,
        resolution=1.0,
        origin_x=0.0,
        origin_y=0.0,
        data=[0, 0, 0, 0],
    )
    static = make_grid(
        width=4,
        height=4,
        resolution=0.5,
        origin_x=0.0,
        origin_y=0.0,
        data=[
            0, 0, 0, 0,
            0, 100, 0, 0,
            0, 0, 0, 0,
            0, 0, 0, 0,
        ],
    )

    result = OccupancyGridFusion.apply_static_overlay(dynamic, static, 50)

    assert result == 'ok'
    assert list(dynamic.data) == [100, 0, 0, 0]


def test_static_overlay_skips_frame_mismatch():
    dynamic = make_grid(1, 1, 1.0, 0.0, 0.0, [0])
    static = make_grid(1, 1, 1.0, 0.0, 0.0, [100])
    static.header.frame_id = 'odom'

    result = OccupancyGridFusion.apply_static_overlay(dynamic, static, 50)

    assert result == 'frame_mismatch'
    assert list(dynamic.data) == [0]
