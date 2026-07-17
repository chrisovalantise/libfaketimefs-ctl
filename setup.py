#!/usr/bin/env python3

from setuptools import setup

setup(
    name='libfaketimefs-ctl',
    version='0.0.9',
    description='libfaketimefs controller',
    author='Raymond Butcher',
    author_email='ray.butcher@claranet.uk',
    url='https://github.com/chrisovalantise/libfaketimefs-ctl',
    license='MIT License',
    python_requires='>=3.8',
    packages=(
        'libfaketimefs_ctl',
    ),
    scripts=(
        'bin/libfaketimefs-ctl',
    ),
    install_requires=(
        'boto3==1.17.112',
        'libfaketimefs-botocore>=0.0.2',
        'python-dateutil',
    ),
)
