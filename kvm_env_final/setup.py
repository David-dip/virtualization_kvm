# setup.py
from setuptools import setup, find_packages

setup(
    name="kvm-env",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "click>=8.1.0",
        "psycopg2-binary>=2.9.0",
        "libvirt-python>=9.0.0",
        "python-dotenv>=1.0.0",
        "PyYAML>=6.0",
    ],
    entry_points={
        "console_scripts": [
            "kvm-env = kvm_env.cli:cli",
        ],
    },
    author="Скрипник Давид Александрович",
    description="Управление воспроизводимой виртуальной экосистемой KVM",
)