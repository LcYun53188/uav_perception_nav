from setuptools import find_packages, setup

package_name = 'nav_mapping'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='root',
    maintainer_email='root@todo.todo',
    description='Point cloud processing and local occupancy grid generation',
    license='Apache-2.0',
    entry_points={'console_scripts': [
        'local_map_builder = nav_mapping.local_map_builder:main',
        'livox_custom_to_pointcloud2 = nav_mapping.livox_custom_to_pointcloud2:main',
        'pointcloud_combiner = nav_mapping.pointcloud_combiner:main',
        'occupancy_grid_fusion = nav_mapping.occupancy_grid_fusion:main',
    ]},
)
