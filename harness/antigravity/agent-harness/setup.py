from setuptools import find_namespace_packages, setup

setup(
    name="cli-anything-antigravity",
    version="1.0.0",
    description="Stateful CLI-Anything harness for Google Antigravity customizations, SDK runners, and live IDE/agy CLI backend",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    package_data={
        "cli_anything.antigravity": ["skills/*.md"],
    },
    include_package_data=True,
    install_requires=[
        "click>=8.0.0",
        "prompt-toolkit>=3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-anything-antigravity=cli_anything.antigravity.antigravity_cli:main",
        ],
    },
    python_requires=">=3.10",
)
