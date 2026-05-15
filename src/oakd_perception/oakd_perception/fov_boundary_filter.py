"""FOV boundary point cloud processing utilities."""

from typing import Tuple

import numpy as np


class FOVBoundaryFilter:
    """Filter point clouds by a fixed field of view."""

    def __init__(self, fov_h: float = 72.0, fov_v: float = 53.0, margin: float = 0.0):
        """Initialize the fixed FOV filter."""
        self.fov_h = fov_h
        self.fov_v = fov_v
        self.margin = margin

        self.half_fov_h_rad = np.radians(fov_h / 2.0)
        self.half_fov_v_rad = np.radians(fov_v / 2.0)
        self.margin_rad = np.radians(margin)

    def points_in_fov(self, points: np.ndarray) -> np.ndarray:
        """Return a boolean mask for points inside the FOV."""
        if points.shape[0] == 0:
            return np.array([], dtype=bool)

        x = points[:, 0]
        y = points[:, 1]
        z = points[:, 2]

        horizontal_angle = np.arctan2(x, z)
        vertical_angle = np.arctan2(y, z)

        fov_h_limit = self.half_fov_h_rad - self.margin_rad
        fov_v_limit = self.half_fov_v_rad - self.margin_rad

        return (np.abs(horizontal_angle) <= fov_h_limit) & (
            np.abs(vertical_angle) <= fov_v_limit
        )

    def filter_fov_boundary(self, points: np.ndarray) -> np.ndarray:
        """Return only points that fall inside the FOV."""
        in_fov = self.points_in_fov(points)
        return points[in_fov]

    def _frustum_plane_distances(self, points: np.ndarray) -> np.ndarray:
        """Return signed distances to the four frustum side planes.

        The camera frame is assumed to use +z forward, +x to the right, and
        +y upward. Distances are positive outside the frustum, negative inside.
        """
        if points.shape[0] == 0:
            return np.empty((0, 4), dtype=float)

        x = points[:, 0]
        y = points[:, 1]
        z = points[:, 2]

        tan_h = np.tan(self.half_fov_h_rad)
        tan_v = np.tan(self.half_fov_v_rad)
        cos_h = np.cos(self.half_fov_h_rad)
        cos_v = np.cos(self.half_fov_v_rad)

        # Four side planes of the pyramid frustum.
        # Right:  x - z*tan(h) <= 0
        # Left:  -x - z*tan(h) <= 0
        # Top:    y - z*tan(v) <= 0
        # Bottom: -y - z*tan(v) <= 0
        d_right = (x - z * tan_h) * cos_h
        d_left = (-x - z * tan_h) * cos_h
        d_top = (y - z * tan_v) * cos_v
        d_bottom = (-y - z * tan_v) * cos_v

        return np.stack((d_right, d_left, d_top, d_bottom), axis=1)

    def points_in_frustum(self, points: np.ndarray, margin: float = 0.0) -> np.ndarray:
        """Return a boolean mask for points inside the frustum core.

        `margin` is the safety band width in meters measured along each side
        plane normal. Points closer than `margin` to any frustum side are
        rejected.
        """
        if points.shape[0] == 0:
            return np.array([], dtype=bool)

        finite_mask = np.isfinite(points).all(axis=1)
        forward_mask = points[:, 2] > 1e-6
        valid_mask = finite_mask & forward_mask
        if not np.any(valid_mask):
            return np.zeros(len(points), dtype=bool)

        safe_margin = max(float(margin), 0.0)
        distances = self._frustum_plane_distances(points[valid_mask])

        # Keep only points that are at least `safe_margin` away from every side.
        in_core = np.all(distances <= -safe_margin, axis=1)

        mask = np.zeros(len(points), dtype=bool)
        mask[np.where(valid_mask)[0]] = in_core
        return mask

    def filter_frustum_boundary(
        self, points: np.ndarray, margin: float | None = None
    ) -> np.ndarray:
        """Return only points that stay inside the frustum core.

        This is the precise pyramid-frustum version of boundary filtering.
        `margin` overrides `self.margin` when provided and is interpreted in
        meters.
        """
        effective_margin = self.margin if margin is None else margin
        in_frustum = self.points_in_frustum(points, margin=effective_margin)
        return points[in_frustum]

    def get_fov_boundary_mask(
        self, height: int, width: int, fx: float, fy: float, cx: float, cy: float
    ) -> np.ndarray:
        """Build an image-space mask for pixels inside the FOV."""
        # 创建像素坐标网格
        v_coords = np.arange(height)
        u_coords = np.arange(width)
        vv, uu = np.meshgrid(v_coords, u_coords, indexing="ij")

        # 归一化坐标(相对于主点)
        x_norm = (uu - cx) / fx
        y_norm = (vv - cy) / fy

        # 计算角度(假设z=1的单位距离)
        horizontal_angle = np.arctan(x_norm)
        vertical_angle = np.arctan(y_norm)

        # 应用安全裕度
        fov_h_limit = self.half_fov_h_rad - self.margin_rad
        fov_v_limit = self.half_fov_v_rad - self.margin_rad

        # 生成掩膜
        mask = (np.abs(horizontal_angle) <= fov_h_limit) & (
            np.abs(vertical_angle) <= fov_v_limit
        )

        return mask

    def get_boundary_pixels(
        self,
        height: int,
        width: int,
        fx: float,
        fy: float,
        cx: float,
        cy: float,
        threshold: float = 0.95,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Return pixel coordinates near the FOV boundary."""
        mask = self.get_fov_boundary_mask(height, width, fx, fy, cx, cy)

        boundary_in = np.where(mask)
        boundary_out = np.where(~mask)

        return boundary_in, boundary_out

    def count_fov_boundary_points(self, points: np.ndarray) -> Tuple[int, int, float]:
        """Count points inside and outside the FOV."""
        if points.shape[0] == 0:
            return 0, 0, 0.0

        in_fov = self.points_in_fov(points)
        count_in = np.sum(in_fov)
        count_out = np.sum(~in_fov)
        ratio = count_out / len(points) if len(points) > 0 else 0.0

        return int(count_in), int(count_out), float(ratio)


def create_fov_filter() -> FOVBoundaryFilter:
    """Create a default fixed FOV filter."""
    return FOVBoundaryFilter(fov_h=72.0, fov_v=53.0, margin=0.0)


def estimate_fov_from_intrinsics(
    fx: float, fy: float, width: int, height: int
) -> Tuple[float, float]:
    """Estimate horizontal and vertical FOV from camera intrinsics."""
    fov_h = 2 * np.degrees(np.arctan(width / (2 * fx)))
    fov_v = 2 * np.degrees(np.arctan(height / (2 * fy)))
    return fov_h, fov_v


def estimate_fov_from_points(
    points: np.ndarray, percentile: float = 98.0
) -> Tuple[float, float]:
    """Estimate horizontal and vertical FOV from a point cloud.

    This computes the angular extent of points in the camera frame by
    calculating horizontal and vertical angles (atan2) and using the
    specified percentile to ignore extreme outliers. Returns (fov_h, fov_v)
    in degrees.
    """
    if points is None or points.shape[0] == 0:
        return 0.0, 0.0

    x = points[:, 0]
    y = points[:, 1]
    z = points[:, 2]

    # 防止除以零或深度为负的异常点影响角度计算
    valid = z > 1e-6
    if not np.any(valid):
        return 0.0, 0.0

    horiz = np.arctan2(x[valid], z[valid])
    vert = np.arctan2(y[valid], z[valid])

    pct = float(np.clip(percentile, 50.0, 99.9))
    lowp = (100.0 - pct) / 2.0
    highp = 100.0 - lowp

    h_min = np.percentile(horiz, lowp)
    h_max = np.percentile(horiz, highp)
    v_min = np.percentile(vert, lowp)
    v_max = np.percentile(vert, highp)

    fov_h = np.degrees(h_max - h_min)
    fov_v = np.degrees(v_max - v_min)

    return float(fov_h), float(fov_v)


def auto_filter_by_estimated_fov(
    points: np.ndarray, percentile: float = 98.0, margin: float = 0.5
) -> Tuple[np.ndarray, dict]:
    """Estimate FOV from points and filter out boundary points.

    Returns filtered points and a dict with estimated FOV and parameters.
    """
    fov_h, fov_v = estimate_fov_from_points(points, percentile=percentile)

    # 如果估计失败，返回原始点云
    if fov_h == 0.0 or fov_v == 0.0:
        stats = {
            "estimated_fov_h": fov_h,
            "estimated_fov_v": fov_v,
            "percentile": percentile,
            "margin": margin,
            "filtered_count": 0,
            "original_count": len(points),
        }
        return points, stats

    fov_filter = FOVBoundaryFilter(fov_h=fov_h, fov_v=fov_v, margin=margin)
    filtered = fov_filter.filter_fov_boundary(points)

    stats = {
        "estimated_fov_h": fov_h,
        "estimated_fov_v": fov_v,
        "percentile": percentile,
        "margin": margin,
        "filtered_count": len(filtered),
        "original_count": len(points),
    }
    return filtered, stats


def remove_fov_boundary_points(
    points: np.ndarray, fov_h: float = 72.0, fov_v: float = 53.0, margin: float = 2.0
) -> np.ndarray:
    """Remove points that fall outside the FOV."""
    fov_filter = FOVBoundaryFilter(fov_h=fov_h, fov_v=fov_v, margin=margin)
    return fov_filter.filter_fov_boundary(points)


def remove_frustum_boundary_points(
    points: np.ndarray,
    fov_h: float = 72.0,
    fov_v: float = 53.0,
    margin: float = 0.15,
) -> np.ndarray:
    """Remove points near the pyramid frustum boundary.

    `margin` is measured in meters along the side-plane normals.
    """
    fov_filter = FOVBoundaryFilter(fov_h=fov_h, fov_v=fov_v, margin=margin)
    return fov_filter.filter_frustum_boundary(points)


def get_fov_statistics(
    points: np.ndarray, fov_h: float = 72.0, fov_v: float = 53.0
) -> dict:
    """Return basic FOV statistics for a point cloud."""
    fov_filter = FOVBoundaryFilter(fov_h=fov_h, fov_v=fov_v)
    in_count, out_count, ratio = fov_filter.count_fov_boundary_points(points)

    return {
        "total_points": len(points),
        "points_in_fov": in_count,
        "points_out_fov": out_count,
        "boundary_ratio": ratio,
        "fov_h_degree": fov_h,
        "fov_v_degree": fov_v,
    }


class AdaptiveFOVBoundaryFilter:
    """Adapt the FOV margin based on point cloud characteristics."""

    def __init__(
        self,
        base_fov_h: float = 72.0,
        base_fov_v: float = 53.0,
        initial_margin: float = 2.0,
        density_weight: float = 0.5,
        depth_weight: float = 0.3,
    ):
        """Initialize the adaptive FOV filter."""
        self.base_fov_h = base_fov_h
        self.base_fov_v = base_fov_v
        self.initial_margin = initial_margin
        self.density_weight = density_weight
        self.depth_weight = depth_weight

        self.filter = FOVBoundaryFilter(base_fov_h, base_fov_v, initial_margin)
        self.adaptive_margin = initial_margin

    def _calculate_boundary_density(
        self, points: np.ndarray, margin_range: float = 5.0
    ) -> float:
        """Calculate the density of points near the FOV boundary."""
        if len(points) == 0:
            return 0.0

        x, y, z = points[:, 0], points[:, 1], points[:, 2]
        horizontal_angle = np.arctan2(x, z)
        vertical_angle = np.arctan2(y, z)

        margin_rad = np.radians(margin_range)
        half_fov_h_rad = np.radians(self.base_fov_h / 2.0)
        half_fov_v_rad = np.radians(self.base_fov_v / 2.0)

        # 在边界范围内的点(FOV内但接近边界)
        near_boundary = (
            (np.abs(horizontal_angle) > half_fov_h_rad - margin_rad)
            & (np.abs(horizontal_angle) <= half_fov_h_rad)
        ) | (
            (np.abs(vertical_angle) > half_fov_v_rad - margin_rad)
            & (np.abs(vertical_angle) <= half_fov_v_rad)
        )

        boundary_density = (
            np.sum(near_boundary) / len(points) if len(points) > 0 else 0.0
        )
        return float(boundary_density)

    def _calculate_depth_variance(self, points: np.ndarray) -> float:
        """Calculate a normalized coefficient of depth variation."""
        if len(points) < 2:
            return 0.0

        z = points[:, 2]
        mean_depth = np.mean(z)

        if mean_depth == 0:
            return 0.0

        # 使用变异系数(标准差/均值)，然后归一化到0-1
        cv = np.std(z) / mean_depth
        return float(np.clip(cv, 0.0, 1.0))

    def _calculate_outlier_ratio(
        self, points: np.ndarray, std_threshold: float = 3.0
    ) -> float:
        """Calculate the outlier ratio using a standard deviation threshold."""
        if len(points) < 2:
            return 0.0

        # 计算每个点的到原点的距离
        distances = np.linalg.norm(points, axis=1)
        mean_dist = np.mean(distances)
        std_dist = np.std(distances)

        if std_dist == 0:
            return 0.0

        # 识别离群点(距离超过mean ± 3*std)
        outliers = np.abs(distances - mean_dist) > std_threshold * std_dist
        ratio = np.sum(outliers) / len(points) if len(points) > 0 else 0.0

        return float(ratio)

    def adapt_margin(self, points: np.ndarray) -> float:
        """Adapt the FOV margin based on point cloud characteristics."""
        if len(points) == 0:
            return self.initial_margin

        # 计算点云特性
        boundary_density = self._calculate_boundary_density(points)
        depth_variance = self._calculate_depth_variance(points)
        outlier_ratio = self._calculate_outlier_ratio(points)

        # 基于边界密度进行调整(高密度→增加裕度)
        density_adjust = boundary_density * 3.0  # 最多增加3度

        # 基于深度方差进行调整(方差大→增加裕度)
        variance_adjust = depth_variance * 2.0  # 最多增加2度

        # 基于离群点比例进行调整(离群点多→增加裕度)
        outlier_adjust = outlier_ratio * 1.5  # 最多增加1.5度

        # 加权融合
        total_adjust = (
            density_adjust * self.density_weight
            + variance_adjust * self.depth_weight
            + outlier_adjust * (1.0 - self.density_weight - self.depth_weight)
        )

        self.adaptive_margin = np.clip(self.initial_margin + total_adjust, 0.1, 10.0)
        return self.adaptive_margin

    def filter_adaptive(
        self, points: np.ndarray, auto_adapt: bool = True
    ) -> Tuple[np.ndarray, dict]:
        """Filter points with adaptive FOV margin and return stats."""
        # 计算自适应参数
        if auto_adapt:
            adaptive_margin = self.adapt_margin(points)
        else:
            adaptive_margin = self.adaptive_margin

        # 更新过滤器
        self.filter.margin = adaptive_margin
        self.filter.margin_rad = np.radians(adaptive_margin)

        # 执行过滤
        filtered_points = self.filter.filter_fov_boundary(points)

        # 生成统计信息
        stats = {
            "original_count": len(points),
            "filtered_count": len(filtered_points),
            "removed_count": len(points) - len(filtered_points),
            "adaptive_margin": adaptive_margin,
            "boundary_density": self._calculate_boundary_density(points),
            "depth_variance": self._calculate_depth_variance(points),
            "outlier_ratio": self._calculate_outlier_ratio(points),
        }

        return filtered_points, stats

    def get_boundary_points(
        self, points: np.ndarray, auto_adapt: bool = True
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Split points into inside-FOV and outside-FOV sets."""
        if auto_adapt:
            self.adapt_margin(points)

        self.filter.margin = self.adaptive_margin
        self.filter.margin_rad = np.radians(self.adaptive_margin)

        in_fov = self.filter.points_in_fov(points)
        return points[in_fov], points[~in_fov]


def adaptive_filter_fov_boundary(
    points: np.ndarray,
    fov_h: float = 72.0,
    fov_v: float = 53.0,
    auto_adapt: bool = True,
) -> Tuple[np.ndarray, dict]:
    """Filter FOV boundary points adaptively."""
    adaptive_filter = AdaptiveFOVBoundaryFilter(
        base_fov_h=fov_h, base_fov_v=fov_v, initial_margin=2.0
    )
    return adaptive_filter.filter_adaptive(points, auto_adapt=auto_adapt)
