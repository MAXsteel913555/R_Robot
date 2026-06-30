from setuptools import find_packages, setup
import os
from glob import glob

package_name = "car_control"

setup(
    name=package_name,
    version="0.0.1",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.py")),
        (os.path.join("share", package_name, "config"), glob("config/*.rviz") + glob("config/*.yaml")),
        (os.path.join("share", package_name, "maps"), glob("maps/*.yaml") + glob("maps/*.pgm")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="sunrise",
    maintainer_email="sunrise@todo.todo",
    description="RDK X5 chassis control and SLAM mapping",
    license="TODO",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "chassis_node = car_control.chassis_node:main",
        ],
    },
)
