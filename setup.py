from setuptools import setup

VERSION = "0.0.1"
NAME = "e3dc-to-mqtt"
 
install_requires = ["pye3dc", "paho-mqtt"]

setup(
    name=NAME,
    version=VERSION,
    description="Mapper for E3/DC data to MQTT",
    long_description=open("README.md").read(),
    long_description_content_type='text/markdown',
    author="Max Dhom",
    author_email="info@mdwd.org",
    license="MIT",
    url="https://github.com/mdhom/e3dc-to-mqtt",
    python_requires='>=3.7',
    install_requires=install_requires,
    packages=['e3dc_to_mqtt'],
    entry_points={
        'console_scripts': [
            'e3dc-to-mqtt = e3dc_to_mqtt.e3dc_to_mqtt_base:main',
        ],
    },
)
