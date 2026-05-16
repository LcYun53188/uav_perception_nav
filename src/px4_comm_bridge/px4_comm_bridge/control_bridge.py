from geometry_msgs.msg import PoseStamped, TwistStamped
from std_msgs.msg import Bool, Int8

from .converters import (
    fill_offboard_control_mode,
    fill_trajectory_setpoint,
    planner_twist_to_ned_velocity,
)


class Px4ControlBridge:
    def __init__(
        self,
        node,
        px4_available,
        offboard_control_mode_type,
        trajectory_setpoint_type,
        vehicle_command_type,
    ):
        self.node = node
        self.px4_available = px4_available
        self.offboard_control_mode_type = offboard_control_mode_type
        self.trajectory_setpoint_type = trajectory_setpoint_type
        self.vehicle_command_type = vehicle_command_type

        self.latest_cmd = None
        self.last_cmd_time = self.node.get_clock().now()
        self.emergency_active = False
        self.safety_level = 0
        self.offboard_engaged = False
        self.armed = False
        self.emergency_sent = False

        self.offboard_mode_pub = None
        self.setpoint_pub = None
        self.vehicle_command_pub = None

    def start(self):
        if not self.px4_available:
            self.node.get_logger().warn('px4_msgs not available; ROS->PX4 control disabled')
            return

        self.offboard_mode_pub = self.node.create_publisher(
            self.offboard_control_mode_type,
            self.node.get_parameter('fmu_offboard_mode_topic').value,
            10,
        )
        self.setpoint_pub = self.node.create_publisher(
            self.trajectory_setpoint_type,
            self.node.get_parameter('fmu_trajectory_topic').value,
            10,
        )
        self.vehicle_command_pub = self.node.create_publisher(
            self.vehicle_command_type,
            self.node.get_parameter('fmu_command_topic').value,
            10,
        )

        self.node.create_subscription(
            TwistStamped,
            self.node.get_parameter('planner_cmd_topic').value,
            self.cmd_cb,
            10,
        )
        self.node.create_subscription(
            PoseStamped,
            self.node.get_parameter('planner_pose_topic').value,
            self.pose_cb,
            10,
        )
        self.node.create_subscription(
            Bool,
            self.node.get_parameter('planner_emergency_topic').value,
            self.em_cb,
            10,
        )
        self.node.create_subscription(
            Int8,
            self.node.get_parameter('planner_safety_topic').value,
            self.safety_cb,
            10,
        )

        rate = float(self.node.get_parameter('control_rate_hz').value)
        self.node.create_timer(max(0.01, 1.0 / rate), self.publish_control)
        self.node.get_logger().info('PX4 control bridge enabled')

    def now_us(self):
        return int(self.node.get_clock().now().nanoseconds / 1000)

    def cmd_cb(self, msg: TwistStamped):
        self.latest_cmd = msg
        self.last_cmd_time = self.node.get_clock().now()
        if not self.offboard_engaged:
            self.node.get_logger().info('Received first nav command, enabling offboard streaming')
            self.offboard_engaged = True

        if bool(self.node.get_parameter('auto_arm').value) and not self.armed:
            self.send_vehicle_command(self.vehicle_command_type.VEHICLE_CMD_COMPONENT_ARM_DISARM, param1=1.0)
            self.armed = True

    def pose_cb(self, _msg: PoseStamped):
        # Reserved for future pose-based command mapping.
        return

    def em_cb(self, msg: Bool):
        if msg.data and not self.emergency_active:
            self.node.get_logger().warn('Emergency signal (Bool) received')
        self.emergency_active = bool(msg.data)
        self._check_and_trigger_emergency()

    def safety_cb(self, msg: Int8):
        self.safety_level = int(msg.data)
        if self.safety_level >= 2:
            self.emergency_active = True
        self._check_and_trigger_emergency()

    def _check_and_trigger_emergency(self):
        if self.emergency_active and not self.emergency_sent:
            self.node.get_logger().error('Safety action triggered!')
            self._send_emergency_action()
            self.emergency_sent = True
        elif not self.emergency_active:
            self.emergency_sent = False

    def publish_control(self):
        if self.offboard_engaged:
            cmd_timeout = float(self.node.get_parameter('cmd_timeout_sec').value)
            now = self.node.get_clock().now()
            if (now - self.last_cmd_time).nanoseconds / 1e9 > cmd_timeout:
                if not self.emergency_active:
                    self.node.get_logger().error(f'Command timeout detected! (>{cmd_timeout}s)')
                    self.emergency_active = True
                    self._check_and_trigger_emergency()

        if self.emergency_active:
            self.publish_halt_setpoint()
            self.publish_offboard_mode()
            return

        if self.latest_cmd is None:
            return

        self.publish_offboard_mode()
        self.publish_setpoint(self.latest_cmd)

    def publish_offboard_mode(self):
        msg = self.offboard_control_mode_type()
        fill_offboard_control_mode(msg, self.now_us())
        self.offboard_mode_pub.publish(msg)

    def publish_setpoint(self, cmd_msg: TwistStamped):
        vx, vy, vz = planner_twist_to_ned_velocity(
            cmd_msg,
            str(self.node.get_parameter('input_velocity_frame').value),
        )
        msg = self.trajectory_setpoint_type()
        fill_trajectory_setpoint(msg, self.now_us(), vx, vy, vz)
        self.setpoint_pub.publish(msg)

    def publish_halt_setpoint(self):
        msg = self.trajectory_setpoint_type()
        fill_trajectory_setpoint(msg, self.now_us(), 0.0, 0.0, 0.0)
        self.setpoint_pub.publish(msg)

    def _send_emergency_action(self):
        action = str(self.node.get_parameter('emergency_action').value).lower()
        if action == 'rtl':
            self.node.get_logger().info('Sending RTL command')
            self.send_vehicle_command(self.vehicle_command_type.VEHICLE_CMD_NAV_RETURN_TO_LAUNCH)
        elif action == 'disarm':
            self.node.get_logger().info('Sending DISARM command')
            self.send_vehicle_command(self.vehicle_command_type.VEHICLE_CMD_COMPONENT_ARM_DISARM, param1=0.0)
        else:
            self.node.get_logger().info('Sending LAND command')
            self.send_vehicle_command(self.vehicle_command_type.VEHICLE_CMD_NAV_LAND)

    def send_vehicle_command(
        self,
        command,
        param1=0.0,
        param2=0.0,
        param3=0.0,
        param4=0.0,
        param5=0.0,
        param6=0.0,
        param7=0.0,
    ):
        msg = self.vehicle_command_type()
        msg.timestamp = self.now_us()
        msg.param1 = float(param1)
        msg.param2 = float(param2)
        msg.param3 = float(param3)
        msg.param4 = float(param4)
        msg.param5 = float(param5)
        msg.param6 = float(param6)
        msg.param7 = float(param7)
        msg.command = int(command)
        msg.target_system = int(self.node.get_parameter('target_system').value)
        msg.target_component = int(self.node.get_parameter('target_component').value)
        msg.source_system = 1
        msg.source_component = 1
        msg.confirmation = 0
        msg.from_external = True
        self.vehicle_command_pub.publish(msg)
