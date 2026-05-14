from setuptools import setup

package_name = 'nav_local'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='root',
    maintainer_email='root@todo.todo',
    description='Local 2D/2.5D navigation prototype',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={'console_scripts': [
        'local_map_builder = nav_local.local_map_builder:main',
        'local_planner = nav_local.local_planner:main',
        'px4_offboard_ctrl = nav_local.px4_offboard_ctrl:main',
        'safety_monitor = nav_local.safety_monitor:main',
    ]},
)
