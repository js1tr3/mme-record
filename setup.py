#!/usr/bin/env python

"""MME Record setup."""
from pathlib import Path
from setuptools import setup

VERSION = "0.6.3"
URL = "https://github.com/sillygoose/cs_esphome.git"

setup(
    name="Playback",
    version=VERSION,
    description="MME CAN bus module playback",
    long_description=Path("README.md").read_text(),
    long_description_content_type="text/markdown",
    url=URL,
    download_url="{}/tarball/{}".format(URL, VERSION),
    author="Rick Naro",
    author_email="sillygoose@me.com",
    license="MIT",
    install_requires=[
        "python-configuration",
        "pyyaml",
        "python-can",
        "can-isotp",
        "udsoncan",
        "influxdb-client",
    ],
    zip_safe=True,
)
