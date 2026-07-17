上电先机械臂驱动板插线
先从臂左臂
再从臂右臂
再主臂左臂
再主臂右臂

sudo chmod 777 /dev/ttyCH341USB*

再运行命令：
cd ~/lerobot-main
conda activate lerobot

python lerobot/scripts/control_robot.py   --robot.type=so101   --control.type=teleoperate   --robot.cameras='{}'
