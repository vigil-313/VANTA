#!/usr/bin/env python3
"""
VANTA - Voice-based Ambient Neural Thought Assistant
Setup script for installation
"""

from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as f:
    requirements = f.read().splitlines()

setup(
    name="vanta",
    version="0.1.0",
    author="VANTA Team",
    author_email="your.email@example.com",
    description="Voice-based Ambient Neural Thought Assistant",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/vanta",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "vanta=vanta.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "vanta": ["config/*.yaml", "config/personality_profiles/*.yaml"],
    },
)