# FOV过滤规则 - 快速参考卡

## 核心公式

### 固定过滤
```
点被保留 ⟺ (|arctan2(x,z)| ≤ 36° - margin) AND (|arctan2(y,z)| ≤ 26.5° - margin)
```

### 自适应过滤
```
margin_adapt = margin_base + (BD × 3.0 × 0.5) + (DV × 2.0 × 0.3) + (OR × 1.5 × 0.2)
final_margin = clamp(margin_adapt, 0.1°, 10.0°)
```

---

## 一页纸速查表

| 项目 | 说明 | 默认值 | 范围 |
|------|------|--------|------|
| FOV_h | 水平视野 | 72° | 45-95° |
| FOV_v | 竖直视野 | 53° | 30-60° |
| margin | 安全裕度 | 0-2° | 0-5° |
| BD | 边界密度 | - | 0-1 |
| DV | 深度方差 | - | 0-1 |
| OR | 离群点比 | - | 0-1 |

---

## 三个自适应指标快速判断

### 边界密度 (BD)
```
BD = 靠近边界的点数 / 总点数

BD > 0.3? ✓ 说明边界有异常
          调整量: 最多 +3.0 × 0.5 = +1.5°
```

### 深度方差 (DV)
```
DV = 标准差(z) / 平均值(z)   # 变异系数

DV > 0.5? ✓ 说明场景深度复杂
          调整量: 最多 +2.0 × 0.3 = +0.6°
```

### 离群点比例 (OR)
```
OR = 异常点数 / 总点数    # 距离>3σ的点

OR > 0.1? ✓ 说明有明显异常（镜面/噪声）
          调整量: 最多 +1.5 × 0.2 = +0.3°
```

---

## 代码快速参考

### 基础过滤
```python
from oakd_perception.fov_boundary_filter import FOVBoundaryFilter, remove_fov_boundary_points

# 方式1: 创建过滤器
filter = FOVBoundaryFilter(fov_h=72, fov_v=53, margin=2.0)
clean = filter.filter_fov_boundary(points)

# 方式2: 一行代码
clean = remove_fov_boundary_points(points, margin=2.0)
```

### 自适应过滤
```python
from oakd_perception.fov_boundary_filter import AdaptiveFOVBoundaryFilter

filter = AdaptiveFOVBoundaryFilter()
clean, stats = filter.filter_adaptive(points)

print(f"自适应裕度: {stats['adaptive_margin']:.2f}°")
print(f"保留点数: {stats['filtered_count']}/{stats['original_count']}")
```

### 获取统计信息
```python
from oakd_perception.fov_boundary_filter import get_fov_statistics

stats = get_fov_statistics(points)
print(f"边界外: {stats['boundary_ratio']:.1%}")
```

---

## 参数选择速查

### 按应用选择

| 应用 | 推荐margin | 推荐方式 | 理由 |
|------|-----------|---------|------|
| 实时避障 | 1-2° | 固定 | 速度快 |
| 建图SLAM | 2-3° | 自适应 | 鲁棒 |
| 物体检测 | 0-1° | 固定 | 精度优先 |
| 深度测量 | 0.5° | 固定 | 高精度 |

### 按距离选择

| 距离 | margin | 原因 |
|------|--------|------|
| <1m | 0-1° | 畸变小，精度优先 |
| 1-3m | 1-2° | 折中方案 |
| >3m | 2-3° | 畸变明显 |

### 按数据质量选择

| 质量 | margin | 原因 |
|------|--------|------|
| 高质量 | 0-1° | 可信度高 |
| 中等 | 1-2° | 标准配置 |
| 低质量 | 2-3° | 容错优先 |

---

## 调试流程

```
1️⃣ 分析原始点云
   stats = get_fov_statistics(points)
   print(f"边界外: {stats['boundary_ratio']:.1%}")

2️⃣ 尝试固定过滤
   clean = remove_fov_boundary_points(points, margin=2.0)
   print(f"保留: {len(clean)}/{len(points)}")

3️⃣ 评估效果
   ✓ 关键目标完整? 
   ✗ 噪声清理干净?

4️⃣ 调整方案
   要保留多点 → 增加margin
   要更干净   → 减小margin
   要自动优化 → 切换自适应
```

---

## 性能指标

### 运行时间 (100K点, Ryzen)

| 操作 | 时间 |
|------|------|
| 固定过滤 | ~5ms |
| 自适应 | ~15ms |
| 统计计算 | ~3ms |

### 内存使用

| 数据 | 大小 |
|------|------|
| 100K点 | ~1.2MB |
| 掩膜(640×400) | ~250KB |

---

## 常见问题速答

**Q: 边界过滤丢失了关键点?**
A: 减小margin或改用自适应过滤

**Q: 还有噪声点没被过滤?**
A: 增大margin或启用自适应

**Q: 速度太慢?**
A: 使用固定过滤代替自适应

**Q: 它何时不工作?**
A: 点云坐标系不是摄像头相对坐标，需要变换

**Q: 能过滤特定形状区域?**
A: 不能，仅支持锥形FOV区域

---

## 配置模板

### 实时系统模板
```python
# 速度第一
fov_filter = FOVBoundaryFilter(
    fov_h=72.0, fov_v=53.0,
    margin=1.5
)
```

### 通用系统模板
```python
# 平衡方案
fov_filter = AdaptiveFOVBoundaryFilter(
    base_fov_h=72.0, base_fov_v=53.0,
    initial_margin=2.0,
    w_density=0.5, w_depth=0.3
)
```

### 精确系统模板
```python
# 最严格
fov_filter = FOVBoundaryFilter(
    fov_h=72.0, fov_v=53.0,
    margin=0.5
)
```

---

## 进阶配置

### 修改自适应权重（高覆盖）
```python
filter = AdaptiveFOVBoundaryFilter(w_density=0.3, w_depth=0.2, w_outlier=0.5)
# 结果: 保留更多点，严格检测离群
```

### 修改自适应权重（高精度）
```python
filter = AdaptiveFOVBoundaryFilter(w_density=0.6, w_depth=0.3, w_outlier=0.1)
# 结果: 积极过滤边界，保守处理深度
```

---

## 输出统计信息参考

```python
filtered, stats = adaptive_filter_fov_boundary(points)

stats = {
    'original_count': 307200,           # 输入点数
    'filtered_count': 300120,           # 输出点数
    'removed_count': 7080,              # 过滤点数
    'adaptive_margin': 2.45,            # 自适应裕度(°)
    'boundary_density': 0.28,           # 边界密度(0-1)
    'depth_variance': 0.52,             # 深度方差(0-1)
    'outlier_ratio': 0.09               # 离群点比(0-1)
}
```

---

💡 **提示：** 建议开始使用自适应过滤，它对大多数场景都有很好的表现。
