# nav_mapping

点云到局部占据栅格的处理包。

## local_map_builder

- 订阅: `/oakd/points_filtered`（默认，可通过参数 `pointcloud_topic` 覆盖）
- 发布: `/local_map/occupancy`（默认，可通过参数 `output_topic` 覆盖）

参数:

- `frame_id`
- `resolution`
- `width`
- `height`
- `min_z`
- `max_z`
- `inflation_radius`
- `publish_rate`
- `transform_timeout_sec`
- `output_topic`

当前实现会先从 `PointCloud2.header.frame_id` 变换到 `frame_id`，再进行投影。

## occupancy_grid_fusion

离线静态地图接入导航时使用。

- 订阅实时局部图：`/local_map/sensor_occupancy`
- 订阅离线静态图：`/static_map/occupancy`
- 发布融合图：`/local_map/occupancy`

融合规则是保守叠加：以实时局部图为底图，把离线地图中占用概率达到
`occupied_threshold` 的格子投影到实时局部图并标记为占用。动态障碍仍由实时点云负责。

参数:

- `dynamic_map_topic`
- `static_map_topic`
- `output_map_topic`
- `publish_rate`
- `dynamic_timeout_sec`
- `occupied_threshold`
