#!/bin/bash
# 完整的OAK-D IMU + 深度 + RViz可视化启动脚本
# 使用统一节点解决设备并发访问问题

set -e

WORKSPACE="/home/nuc/Program/uav_vision_ws"
SOURCE_SETUP="${WORKSPACE}/install/setup.bash"

if [ ! -f "$SOURCE_SETUP" ]; then
    echo "❌ 错误：找不到setup.bash"
    exit 1
fi

# 清理旧进程
echo "🧹 清理旧进程..."
pkill -9 -f "oakd_.*node" || true
pkill -9 -f "imu_fusion" || true  
pkill -9 -f "rviz2" || true
sleep 2

source "$SOURCE_SETUP"

# 显示架构信息
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "📡 OAK-D 统一节点架构 (单设备连接，多频率数据)"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "🔷 硬件层 (单一OAK-D设备连接):"
echo "   └─ oakd_unified_node"
echo "      ├─ IMU Interface: 400Hz"
echo "      │  └─ /oakd/imu/raw (sensor_msgs/Imu)"
echo "      │"
echo "      └─ Depth Camera: 30fps"
echo "         └─ /oakd/points (sensor_msgs/PointCloud2)"
echo ""
echo "🔷 融合层 (IMU数据处理):"
echo "   └─ imu_fusion_node"
echo "      ├─ Input: /oakd/imu/raw"
echo "      └─ Output: /imu (fused orientation + velocities)"
echo ""
echo "🔷 TF链:"
echo "   map → imu_link (由imu_tf_broadcaster发布)"
echo ""
echo "🔷 可视化:"
echo "   rviz2: 查看点云 + IMU坐标系"
echo ""
echo "📊 主题发布统计:"
echo "   • /oakd/imu/raw    : 400Hz  (IMU原始数据)"
echo "   • /oakd/points     :  20Hz  (点云降采样数据)"  
echo "   • /imu             : 100Hz  (融合后的orientation)"
echo "   • /tf              :   动态  (IMU → map的变换)"
echo ""
echo "═══════════════════════════════════════════════════════════════"
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
        echo "📍 【终端1】启动OAK-D统一节点..."
        gnome-terminal --tab -- bash -c "
            source ${SOURCE_SETUP}
            echo '╔════════════════════════════════════════╗'
            echo '║  OAK-D 统一节点 (IMU + 深度)         ║'
            echo '╚════════════════════════════════════════╝'
            echo ''
            echo '集成拓扑:'
            echo '  • DAI Pipeline (单一device连接)'
            echo '  • IMU采样器: 400Hz'
            echo '  • 深度处理: 20Hz (点云)'
            echo ''
            ros2 launch oakd_perception oakd_unified.launch.py \
                imu_frequency:=400 \
                pointcloud_frequency:=20 \
                enable_passive_stereo:=true \
                enable_active_stereo:=false
        " 2>/dev/null || ros2 launch oakd_perception oakd_unified.launch.py &
        
        sleep 3
        
        # Terminal 2: IMU融合 + TF广播
        echo "📍 【终端2】启动IMU融合节点..."
        gnome-terminal --tab -- bash -c "
            source ${SOURCE_SETUP}
            echo '╔════════════════════════════════════════╗'
            echo '║  IMU融合与TF广播                      ║'
            echo '╚════════════════════════════════════════╝'
            echo ''
            echo '处理流程:'
            echo '  /oakd/imu/raw (400Hz)'
            echo '      ↓'
            echo '  imu_fusion_node (补充滤波器)'
            echo '      ↓'
            echo '  /imu (100Hz fused) + TF(map→imu_link)'
            echo ''
            ros2 launch imu_fusion imu_fusion.launch.py \
                raw_topic_0:=/oakd/imu/raw \
                fused_topic_0:=/imu \
                frame_id_0:=imu_link \
                parent_frame:=map
        " 2>/dev/null || ros2 launch imu_fusion imu_fusion.launch.py &
        
        sleep 2
        
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
        echo "      • 查看map → imu_link变换"
        echo "   4. (可选) 添加IMU显示"
        echo "      • Topic: /imu"
        echo ""
        echo "📊 监控主题流:"
        echo "   ros2 topic list"
        echo "   ros2 topic hz /oakd/points"
        echo "   ros2 topic hz /oakd/imu/raw"
        echo ""
        ;;
        
    2)
        echo ""
        echo "🚀 启动OAK-D统一节点..."
        echo ""
        echo "硬件拓扑:"
        echo "  🔌 OAK-D设备（单连接）"
        echo "     ├─ IMU采样器 (400Hz) → /oakd/imu/raw"
        echo "     └─ 深度处理 (20Hz)  → /oakd/points"
        echo ""
        ros2 launch oakd_perception oakd_unified.launch.py
        ;;
        
    3)
        echo ""
        echo "🚀 启动IMU融合 + RViz..."
        echo ""
        echo "⚠️  请先在另一个终端运行:"
        echo "   ros2 launch oakd_perception oakd_unified.launch.py"
        echo ""
        sleep 2
        
        # IMU融合
        echo "📍 启动IMU融合节点..."
        ros2 launch imu_fusion imu_fusion.launch.py &
        sleep 2
        
        # RViz
        echo "📍 启动RViz..."
        rviz2 -d \$(ros2 pkg prefix imu_fusion)/share/imu_fusion/rviz/imu_fusion.rviz 2>/dev/null || rviz2
        ;;
        
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

# 保持脚本运行
wait
