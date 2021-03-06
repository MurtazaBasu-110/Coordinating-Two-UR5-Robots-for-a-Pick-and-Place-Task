#!/usr/bin/env python2

import rospy, sys, numpy as np
import moveit_commander
from copy import deepcopy
from geometry_msgs.msg import Twist
import moveit_msgs.msg
from sensor_msgs.msg import Image
from ur5_notebook.msg import Tracker2_second
from std_msgs.msg import Header
from trajectory_msgs.msg import JointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint

from time import sleep
tracker = Tracker2_second()

class ur5_mp_slave:
    def __init__(self):
        rospy.init_node("motion_planning_slave", anonymous=False)
        self.cxy_sub = rospy.Subscriber('slave/cxy', Tracker2_second, self.tracking_callback, queue_size=1)
        self.cxy_pub = rospy.Publisher('slave/cxy1', Tracker2_second, queue_size=1)
        self.phase = 1
        self.object_cnt = 0
        self.track_flag = False
        self.default_pose_flag = True
        self.cx = 400.0
        self.cy = 400.0
        self.points=[]
        self.state_change_time = rospy.Time.now()

        rospy.loginfo("Starting node moveit_cartesian_path")

        rospy.on_shutdown(self.cleanup)

        # Initialize the move_group API
        moveit_commander.roscpp_initialize(sys.argv)

        group_name = "manipulator"
        # Initialize the move group for the ur5_arm
        self.arm = moveit_commander.MoveGroupCommander(group_name, "slave/robot_description", ns= "slave")

        # Get the name of the end-effector link
        self.end_effector_link = self.arm.get_end_effector_link()

        # Set the reference frame for pose targets
        reference_frame = "world"

        # Set the ur5_arm reference frame accordingly
        self.arm.set_pose_reference_frame(reference_frame)

        # Allow replanning to increase the odds of a solution
        self.arm.allow_replanning(True)

        # Allow some leeway in position (meters) and orientation (radians)
        self.arm.set_goal_position_tolerance(0.01)
        self.arm.set_goal_orientation_tolerance(0.1)
        self.arm.set_planning_time(0.1)
        self.arm.set_max_acceleration_scaling_factor(0.9999)
        self.arm.set_max_velocity_scaling_factor(0.9999)

        # Get the current pose so we can add it as a waypoint
        start_pose = self.arm.get_current_pose(self.end_effector_link).pose
        # print("start_pose", start_pose)

        # Initialize the waypoints list
        self.waypoints= []
        self.pointx = []
        self.pointy = []
        # Set the first waypoint to be the starting pose
        # Append the pose to the waypoints list
        wpose = deepcopy(start_pose)

        # Set the next waypoint to the right 0.5 meters

        wpose.position.x = 0.2
        wpose.position.y = -0.2
        #wpose.position.z = 0.3
        self.waypoints.append(deepcopy(wpose))

        # wpose.position.x = 0.1052
        # wpose.position.y = -0.4271
        # wpose.position.z = 0.4005
        #
        # wpose.orientation.x = 0.4811
        # wpose.orientation.y = 0.5070
        # wpose.orientation.z = -0.5047
        # wpose.orientation.w = 0.5000

        # self.waypoints.append(deepcopy(wpose))


        if np.sqrt((wpose.position.x-start_pose.position.x)**2+(wpose.position.x-start_pose.position.x)**2 \
            +(wpose.position.x-start_pose.position.x)**2)<0.1:
            rospy.loginfo("Warnig: target position overlaps with the initial position!")

        # self.arm.set_pose_target(wpose)

        # Specify default (idle) joint states
        self.default_joint_states = self.arm.get_current_joint_values()
        self.default_joint_states[1] = -1.41667 #-1.71667
        self.default_joint_states[0] = -1.50 #3.14159
        self.default_joint_states[2] = 1.48266 # 1.79266
        self.default_joint_states[3] = -3.14159 #-1.67721
        self.default_joint_states[4] = -2.0
        self.default_joint_states[5] = 1.5708

        self.arm.set_joint_value_target(self.default_joint_states)

        # Set the internal state to the current state
        self.arm.set_start_state_to_current_state()
        plan = self.arm.plan()

        self.arm.execute(plan)

        # Specify end states (drop object)
        #self.end_joint_states = deepcopy(self.default_joint_states)
        #self.end_joint_states[0] = -1.57691
        #self.end_joint_states[1] = -1.2166
        #self.end_joint_states[2] = 1.309
        # print ("End Joint", self.end_joint_states[2])

        #self.end_joint_states[1] = -1.3705

        self.transition_pose = deepcopy(self.default_joint_states)
        #self.transition_pose[0] = 1.57691
        #self.transition_pose[4] = -1.95
        # print ("Trans Joint", self.transition_pose[4])


    def cleanup(self):
        rospy.loginfo("Stopping the slave robot")

        # Stop any current arm movement
        self.arm.stop()

        #Shut down MoveIt! cleanly
        rospy.loginfo("Shutting down Moveit!")
        moveit_commander.roscpp_shutdown()
        moveit_commander.os._exit(0)

    def tracking_callback(self, msg):

        self.track_flag = msg.flag1
        self.cx = msg.x
        self.cy = msg.y
        self.error_x = msg.error_x
        self.error_y = msg.error_y

        if len(self.pointx)>9:
            self.track_flag = True

        if self.phase == 2:
            self.track_flag = False
            self.phase = 1


        if (self.track_flag and -0.6 < self.waypoints[0].position.x and self.waypoints[0].position.x < 0.6):
            self.default_pose_flag = False
            self.track_flag == True
            self.execute()

        else:
            if not self.default_pose_flag:
                self.track_flag = False
                self.execute()
                self.default_pose_flag = True

    def execute(self):
        if self.track_flag:


            # Get the current pose so we can add it as a waypoint
            start_pose = self.arm.get_current_pose(self.end_effector_link).pose

            # Initialize the waypoints list
            self.waypoints= []

            # Set the first waypoint to be the starting pose
            # Append the pose to the waypoints list
            wpose = deepcopy(start_pose)

            # wpose.position.x = -0.5215
            # wpose.position.y = 0.2014
            # wpose.position.z = 0.4102


            if len(self.pointx)>8:
                # print("SELF.POINTX > 8")
                if len(self.pointx)==9:
                    x_speed = np.mean(np.asarray(self.pointx[4:8]) - np.asarray(self.pointx[3:7]))
                    wpose.position.x += 3 * x_speed
                    wpose.position.z = 0.64
                    wpose.position.y+=0.001
                   
                    # print("SELF.POINTX == 9")

                else:
                    if len(self.pointx)==11:
                        tracker.flag2 = 1
                        self.cxy_pub.publish(tracker)

                    if len(self.pointx)<12:
                        x_speed = np.mean(np.asarray(self.pointx[4:8])-np.asarray(self.pointx[3:7]))
                        wpose.position.x += (x_speed-self.error_x*0.015/105)

                    else:
                        if tracker.flag2:
                            self.track_flag=False
                            rospy.sleep (5)
                        transition_pose = deepcopy(start_pose)
                        transition_pose.position.z = 0.635
                        

                        self.waypoints.append(deepcopy(transition_pose))

                        self.arm.set_start_state_to_current_state()
                        plan, fraction = self.arm.compute_cartesian_path(self.waypoints, 0.02, 0.0, True)
                        self.arm.execute(plan)

                        self.arm.set_max_acceleration_scaling_factor(.05)
                        self.arm.set_max_velocity_scaling_factor(.05)



                        self.arm.set_joint_value_target(self.transition_pose)
                        self.arm.set_start_state_to_current_state()
                        plan = self.arm.plan() 
                        self.arm.execute(plan)

                        # self.arm.set_joint_value_target(self.end_joint_states)
                        # self.arm.set_start_state_to_current_state()
                        # plan = self.arm.plan()
                        # self.arm.execute(plan)

                        if -0.1+0.02*self.object_cnt<0.2:
                            self.object_cnt += 1

                        self.waypoints = []
                        start_pose_now = self.arm.get_current_pose(self.end_effector_link).pose
                        transition_pose_now = deepcopy(start_pose_now)
                        transition_pose_now.position.x = -0.564525943734
                        transition_pose_now.position.y =  0.610876101125
                        transition_pose_now.position.z =  0.228989655849
                        transition_pose_now.orientation.x = 0.368618603851
                        transition_pose_now.orientation.y = -9.60225743174e-05
                        transition_pose_now.orientation.z = -0.929580715615
                        transition_pose_now.orientation.w =  9.39709916325e-05

                        #transition_pose.position.z = 0.2 + self.object_cnt*0.025
                        self.waypoints.append(deepcopy(transition_pose_now))

                        self.arm.set_start_state_to_current_state()
                        plan, fraction = self.arm.compute_cartesian_path(self.waypoints, 0.02, 0.0, True)
                    
                        self.arm.execute(plan)

                        rospy.sleep(10) #for the second robot to come and catch the object
                        tracker.flag2 = 0
                        self.cxy_pub.publish(tracker)
                        rospy.sleep(5) #for the first robot to open the gripper fingers
                        self.phase = 2
                    

            # Set the next waypoint to the right 0.5 meters
            else:
                wpose.position.z = 0.64
                wpose.position.x-=0.0055
                #wpose.position.y -= 0.15
                wpose.position.y += self.error_y*0.015/105
                wpose.position.x += self.error_x*0.0055/105 
                #wpose.position.z += 0.02
                print("WPOSE", wpose.position.y)
                
            if self.phase == 1:

                self.waypoints.append(deepcopy(wpose))
                self.pointx.append(wpose.position.x)
                self.pointy.append(wpose.position.y)

                # Set the internal state to the current state
                # self.arm.set_pose_target(wpose)

                self.arm.set_start_state_to_current_state()

                # Plan the Cartesian path connecting the waypoints
                plan, fraction = self.arm.compute_cartesian_path(self.waypoints, 0.01, 0.0, True)

                print("if statement for self.phase == 1")

                # plan = self.arm.plan()

                # If we have a complete plan, execute the trajectory
                if 1-fraction < 0.2:
                    rospy.loginfo("Path computed successfully. Moving the slave arm.")
                    num_pts = len(plan.joint_trajectory.points)
                    rospy.loginfo("\n intermediate waypoints = "+str(num_pts))
                    self.arm.execute(plan)
                    rospy.loginfo("Path execution complete.")
                else:
                    rospy.loginfo("Path planning failed")

        else:
            # Get the current pose so we can add it as a waypoint
            start_pose = self.arm.get_current_pose(self.end_effector_link).pose

            # Initialize the waypoints list
            self.waypoints= []
            self.pointx = []
            self.pointy = []
            # Set the first waypoint to be the starting pose
            # Append the pose to the waypoints list
            wpose = deepcopy(start_pose)

            # Set the next waypoint to the right 0.5 meters

            wpose.position.x = 0.112760302785
            wpose.position.y = 0.189094675467
            wpose.position.z = 0.572799109964

            wpose.orientation.x =  0.414550772152
            wpose.orientation.y = -0.560730842471
            wpose.orientation.z = -0.600814126041
            wpose.orientation.w =  0.390833680174
            self.pointx.append(wpose.position.x)
            self.pointy.append(wpose.position.y)
            self.waypoints.append(deepcopy(wpose))


            self.arm.set_start_state_to_current_state()

            # Plan the Cartesian path connecting the waypoints

            plan, fraction = self.arm.compute_cartesian_path(self.waypoints, 0.01, 0.0, True)

            # plan = self.arm.plan()

            # If we have a complete plan, execute the trajectory
            if 1-fraction < 0.2:
                rospy.loginfo("Path computed successfully. Moving the arm.")
                num_pts = len(plan.joint_trajectory.points)
                rospy.loginfo("\nintermediate waypoints = "+str(num_pts))
                self.arm.execute(plan)
                rospy.loginfo("Path execution complete.")
            else:
                rospy.loginfo("Path planning failed")

mp=ur5_mp_slave()

rospy.spin()