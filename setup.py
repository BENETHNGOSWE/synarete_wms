from pathlib import Path
from setuptools import find_packages, setup

root = Path(__file__).parent
requirements_file = root / "requirements.txt"
install_requires = []

if requirements_file.exists():
    install_requires = [
        line.strip()
        for line in requirements_file.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

setup(
    name="synarete_wms",
    version="0.1.82",
    description="Warehouse Management System for Synarete Engineering Limited",
    author="Eveneth Beneth",
    author_email="benethemmanueli1701@gmail.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
