# nav_mapping

点云到局部占据栅格的处理包。

- 订阅: `/oakd/points`
- 发布: `/local_map/occupancy`

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

当前实现会先从 `PointCloud2.header.frame_id` 变换到 `frame_id`，再进行投影。