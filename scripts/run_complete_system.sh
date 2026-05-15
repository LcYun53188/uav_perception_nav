#!/bin/bash
# 完整的OAK-D IMU + 深度 + RViz可视化启动脚本
# 统一入口：OAK-D 设备、IMU 融合、RViz 编排

set -e

WORKSPACE="/home/nuc/Program/uav_vision_ws"
SOURCE_SETUP="${WORKSPACE}/install/setup.bash"
IMU_RAW_TOPIC="/oakd/imu/raw"
IMU_FUSED_TOPIC="/imu"
IMU_FRAME_ID="oakd_imu_link"
IMU_PARENT_FRAME="map"

if [ ! -f "$SOURCE_SETUP" ]; then
    echo "❌ 错误：找不到setup.bash"
    exit 1
fi

cleanup_processes() {
    echo "🧹 清理旧进程..."
    pkill -9 -f "oakd_.*node" || true
    pkill -9 -f "imu_fusion" || true
    pkill -9 -f "rviz2" || true
    sleep 2
}

print_banner() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "$1"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
}

wait_for_tf_ready() {
    local target_frame="${1}"
    local source_frame="${2}"
    local timeout_sec="${3:-20}"
    local elapsed=0

    echo "⏳ 等待 TF 就绪: ${target_frame} -> ${source_frame} (超时 ${timeout_sec}s)"
    while [ "$elapsed" -lt "$timeout_sec" ]; do
        if timeout 2 ros2 run tf2_ros tf2_echo "${target_frame}" "${source_frame}" >/tmp/tf_wait.log 2>&1; then
            if grep -q "At time" /tmp/tf_wait.log; then
                echo "✅ TF 已就绪: ${target_frame} -> ${source_frame}"
                return 0
            fi
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done

    echo "⚠️  TF 在 ${timeout_sec}s 内未确认就绪，继续启动 RViz（可能短暂提示 frame 不存在）"
    return 1
}

cleanup_processes
source "$SOURCE_SETUP"

print_banner "📡 OAK-D 统一启动编排"
echo "启动模式:"
echo "  1) 完整模式 (OAK-D + IMU 融合 + RViz)"
echo "  2) 仅设备模式 (只启动 OAK-D 统一节点)"
echo "  3) 融合 + 可视化 (假设 OAK-D 已在另一个终端运行)"
echo ""
echo "当前配置:"
echo "  • IMU 原始话题 : ${IMU_RAW_TOPIC}"
echo "  • IMU 融合话题 : ${IMU_FUSED_TOPIC}"
echo "  • TF 子坐标系  : ${IMU_FRAME_ID}"
echo "  • TF 父坐标系  : ${IMU_PARENT_FRAME}"
echo ""

# 启动选择菜单
echo "选择启动模式:"
echo "  1) 完整模式 (OAK-D联合节点 + IMU融合 + RViz)"
echo "  2) 仅设备模式 (只启动OAK-D联合节点)"
echo "  3) 融合+可视化 (假设OAK-D已在另一个终端运行)"
echo ""
read -p "请选择 [1/2/3] (默认1): " MODE
MODE=${MODE:-1}

case $MODE in
    1)
        echo ""
        echo "🚀 启动完整系统..."
        echo ""

        # Terminal 1: OAK-D 统一节点
        echo "📍 【终端1】启动 OAK-D 统一节点"
        gnome-terminal --tab -- bash -c "
            cd ${WORKSPACE}
            ./scripts/run_oakd_unified.sh
        " 2>/dev/null &
        
        sleep 3
        
        # Terminal 2: IMU融合 + TF广播
        echo "📍 【终端2】启动 IMU 融合 + TF 广播"
        gnome-terminal --tab -- bash -c "
            cd ${WORKSPACE}
            bash ./scripts/run_imu_fusion_tf.sh
        " 2>/dev/null &

        wait_for_tf_ready "${IMU_PARENT_FRAME}" "${IMU_FRAME_ID}" 20 || true
        
        # Terminal 3: RViz可视化
        echo "📍 【终端3】启动RViz可视化..."
        gnome-terminal --tab -- bash -c "
            source ${SOURCE_SETUP}
            sleep 1
            rviz2 -d \$(ros2 pkg prefix imu_fusion)/share/imu_fusion/rviz/imu_fusion.rviz 2>/dev/null || rviz2
        " 2>/dev/null || rviz2 &
        
        echo ""
        echo "✅ 完整系统已启动！"
        echo ""
        echo "🎯 RViz配置步骤:"
        echo "   1. Fixed Frame 设置为: map"
        echo "   2. 添加 PointCloud2 显示"
        echo "      • Topic: /oakd/points"
        echo "      • Color: Z"
        echo "   3. 添加 TF 显示"
        echo "      • 查看 map → ${IMU_FRAME_ID} 变换"
        echo "   4. (可选) 添加IMU显示"
        echo "      • Topic: ${IMU_FUSED_TOPIC}"
        echo ""
        echo "📊 监控主题流:"
        echo "   ros2 topic list"
        echo "   ros2 topic hz /oakd/points"
        echo "   ros2 topic hz /oakd/imu/raw"
        echo ""
        ;;
        
    2)
        echo ""
        echo "🚀 启动 OAK-D 统一节点..."
        echo ""
        echo "硬件拓扑:"
        echo "  🔌 OAK-D设备（单连接）"
        echo "     ├─ IMU采样器 (400Hz) → /oakd/imu/raw"
        echo "     └─ 深度处理 (20Hz)  → /oakd/points"
        echo ""
        ./scripts/run_oakd_unified.sh
        ;;
        
    3)
        echo ""
        echo "🚀 启动 IMU 融合 + RViz..."
        echo ""
        echo "⚠️  请先在另一个终端运行:"
        echo "   ./scripts/run_oakd_unified.sh"
        echo ""
        sleep 2
        
        # IMU融合
        echo "📍 启动 IMU 融合 + TF 广播"
        bash ./scripts/run_imu_fusion_tf.sh &

        wait_for_tf_ready "${IMU_PARENT_FRAME}" "${IMU_FRAME_ID}" 20 || true
        
        # RViz
        echo "📍 启动 RViz..."
        rviz2 -d $(ros2 pkg prefix imu_fusion)/share/imu_fusion/rviz/imu_fusion.rviz 2>/dev/null || rviz2
        ;;
        
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

# 保持脚本运行
wait
