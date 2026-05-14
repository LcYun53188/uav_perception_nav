from setuptools import find_packages, setup

package_name = 'imu_fusion'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', [
            'launch/imu_fusion.launch.py',
            'launch/oakd_imu_fusion.launch.py',  # backward compatibility
        ]),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='root',
    maintainer_email='root@todo.todo',
    description='IMU fusion and TF broadcasting with multi-IMU support.',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'imu_fusion_node = imu_fusion.imu_fusion_node:main',
            'imu_tf_broadcaster = imu_fusion.imu_tf_broadcaster:main',
            # Backward compatibility - old names
            'oakd_imu_fusion_node = imu_fusion.imu_fusion_node:main',
            'oakd_imu_tf_broadcaster = imu_fusion.imu_tf_broadcaster:main',
        ],
    },
)