# nav_planning

局部规划包。

- 订阅: `/local_map/occupancy`
- 发布: `/nav/cmd_vel`

当前为原型速度策略，后续可替换为 DWA / DWB / 自定义局部规划器。