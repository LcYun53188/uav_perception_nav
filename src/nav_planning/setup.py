from setuptools import find_packages, setup
import os

package_name = 'nav_planning'

# 构建 data_files
data_files = [
    ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
    ('share/' + package_name, ['package.xml']),
]

# 添加 config 文件
config_dir = os.path.join('share', package_name, 'config')
config_files = [os.path.join('nav_planning', 'config', 'dwb_local_planner.yaml')]
if config_files:
    data_files.append((config_dir, config_files))

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=data_files,
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='root',
    maintainer_email='root@todo.todo',
    description='Local planning and velocity command generation',
    license='Apache-2.0',
    entry_points={'console_scripts': [
        'local_planner = nav_planning.local_planner:main',
        'se2_dwa_local_planner = nav_planning.se2_dwa_local_planner:main',
        'dwb_bridge = nav_planning.dwb_bridge:main',
    ]},
)
