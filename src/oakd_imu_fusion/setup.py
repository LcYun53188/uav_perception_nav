from setuptools import find_packages, setup

package_name = 'oakd_imu_fusion'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/oakd_imu_fusion.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='root',
    maintainer_email='root@todo.todo',
    description='IMU fusion and TF broadcasting for OAK-D sensors.',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'oakd_imu_fusion_node = oakd_imu_fusion.oakd_imu_fusion_node:main',
            'oakd_imu_tf_broadcaster = oakd_imu_fusion.oakd_imu_tf_broadcaster:main',
        ],
    },
)