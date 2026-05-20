from setuptools import find_packages, setup

package_name = "ground_serial_bridge"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/config", ["config/ground_serial_bridge.yaml"]),
    ],
    install_requires=["setuptools"],
    tests_require=["pytest"],
    zip_safe=True,
    maintainer="root",
    maintainer_email="root@todo.todo",
    description="Serial command bridge for a ground omni-wheel base",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "ground_serial_bridge_node = ground_serial_bridge.ground_serial_bridge_node:main",
        ],
    },
)
