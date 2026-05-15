import math

import rclpy
from geometry_msgs.msg import TwistStamped
from rclpy.node import Node
from std_msgs.msg import Bool

try:
    from px4_msgs.msg import OffboardControlMode, TrajectorySetpoint, VehicleCommand
    PX4_MSGS_AVAILABLE = True
except Exception:
    OffboardControlMode = None
    TrajectorySetpoint = None
    VehicleCommand = None
    PX4_MSGS_AVAILABLE = False


class Px4OffboardCtrl(Node):
    def __init__(self):
        super().__init__('px4_offboard_ctrl')
        self.declare_parameter('control_rate_hz', 20.0)
        self.declare_parameter('input_velocity_frame', 'enu')
        self.declare_parameter('auto_arm', False)
        self.declare_parameter('emergency_action', 'land')
        self.declare_parameter('target_system', 1)
        self.declare_parameter('target_component', 1)

        self.cmd_sub = self.create_subscription(TwistStamped, '/nav/cmd_vel', self.cmd_cb, 10)
        self.emer_sub = self.create_subscription(Bool, '/nav/emergency', self.em_cb, 10)
        if PX4_MSGS_AVAILABLE:
            self.offboard_mode_pub = self.create_publisher(OffboardControlMode, '/fmu/in/offboard_control_mode', 10)
            self.setpoint_pub = self.create_publisher(TrajectorySetpoint, '/fmu/in/trajectory_setpoint', 10)
            self.vehicle_command_pub = self.create_publisher(VehicleCommand, '/fmu/in/vehicle_command', 10)
        else:
            self.offboard_mode_pub = None
            self.setpoint_pub = None
            self.vehicle_command_pub = None
            self.get_logger().error('px4_msgs is not available; PX4 bridge will stay inactive')

        self.latest_cmd = None
        self.emergency_active = False
        self.offboard_engaged = False
        self.armed = False
        self.emergency_sent = False

        rate = float(self.get_parameter('control_rate_hz').value)
        self.timer = self.create_timer(max(0.02, 1.0 / rate), self.publish_control)
        self.get_logger().info('nav_px4_bridge/px4_offboard_ctrl started')

    def cmd_cb(self, msg: TwistStamped):
        self.latest_cmd = msg
        if not self.offboard_engaged:
            self.get_logger().info('Received first nav command, enabling offboard streaming')
        self.offboard_engaged = True
        if PX4_MSGS_AVAILABLE and bool(self.get_parameter('auto_arm').value) and not self.armed:
            self.send_vehicle_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, param1=1.0)
            self.armed = True

    def em_cb(self, msg: Bool):
        if msg.data and not self.emergency_active:
            self.get_logger().warn('Emergency signal received')
        self.emergency_active = bool(msg.data)
        if self.emergency_active and not self.emergency_sent:
            self._send_emergency_action()
            self.emergency_sent = True
        if not self.emergency_active:
            self.emergency_sent = False

    def publish_control(self):
        if self.emergency_active:
            self.publish_halt_setpoint()
            self.publish_offboard_mode()
            return

        if self.latest_cmd is None:
            return

        self.publish_offboard_mode()
        self.publish_setpoint(self.latest_cmd)

    def publish_offboard_mode(self):
        if not PX4_MSGS_AVAILABLE:
            return
        msg = OffboardControlMode()
        msg.timestamp = self.now_us()
        msg.position = False
        msg.velocity = True
        msg.acceleration = False
        msg.attitude = False
        msg.body_rate = False
        msg.thrust_and_torque = False
        msg.direct_actuator = False
        self.offboard_mode_pub.publish(msg)

    def publish_setpoint(self, cmd: TwistStamped):
        if not PX4_MSGS_AVAILABLE:
            return
        vx, vy, vz = self._convert_velocity(cmd)
        setpoint = TrajectorySetpoint()
        setpoint.timestamp = self.now_us()
        setpoint.position = [math.nan, math.nan, math.nan]
        setpoint.velocity = [vx, vy, vz]
        setpoint.acceleration = [math.nan, math.nan, math.nan]
        setpoint.jerk = [math.nan, math.nan, math.nan]
        setpoint.yaw = math.nan
        setpoint.yawspeed = math.nan
        self.setpoint_pub.publish(setpoint)

    def publish_halt_setpoint(self):
        if not PX4_MSGS_AVAILABLE:
            return
        setpoint = TrajectorySetpoint()
        setpoint.timestamp = self.now_us()
        setpoint.position = [math.nan, math.nan, math.nan]
        setpoint.velocity = [0.0, 0.0, 0.0]
        setpoint.acceleration = [math.nan, math.nan, math.nan]
        setpoint.jerk = [math.nan, math.nan, math.nan]
        setpoint.yaw = math.nan
        setpoint.yawspeed = math.nan
        self.setpoint_pub.publish(setpoint)

    def _send_emergency_action(self):
        action = str(self.get_parameter('emergency_action').value).lower()
        if not PX4_MSGS_AVAILABLE:
            return
        if action == 'rtl':
            self.send_vehicle_command(VehicleCommand.VEHICLE_CMD_NAV_RETURN_TO_LAUNCH)
        elif action == 'disarm':
            self.send_vehicle_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, param1=0.0)
        else:
            self.send_vehicle_command(VehicleCommand.VEHICLE_CMD_NAV_LAND)

    def _convert_velocity(self, cmd: TwistStamped):
        frame = str(self.get_parameter('input_velocity_frame').value).lower()
        vx = float(cmd.twist.linear.x)
        vy = float(cmd.twist.linear.y)
        vz = float(cmd.twist.linear.z)

        if frame == 'ned':
            return vx, vy, vz

        # Default: ROS ENU to PX4 NED.
        return vy, vx, -vz

    def send_vehicle_command(self, command, param1=0.0, param2=0.0, param3=0.0, param4=0.0, param5=0.0, param6=0.0, param7=0.0):
        if not PX4_MSGS_AVAILABLE:
            return
        msg = VehicleCommand()
        msg.timestamp = self.now_us()
        msg.param1 = float(param1)
        msg.param2 = float(param2)
        msg.param3 = float(param3)
        msg.param4 = float(param4)
        msg.param5 = float(param5)
        msg.param6 = float(param6)
        msg.param7 = float(param7)
        msg.command = int(command)
        msg.target_system = int(self.get_parameter('target_system').value)
        msg.target_component = int(self.get_parameter('target_component').value)
        msg.source_system = 1
        msg.source_component = 1
        msg.confirmation = 0
        msg.from_external = True
        self.vehicle_command_pub.publish(msg)

    def now_us(self):
        return int(self.get_clock().now().nanoseconds / 1000)


def main(args=None):
    rclpy.init(args=args)
    node = Px4OffboardCtrl()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()