import pathlib
from setuptools import setup, find_packages

HERE = pathlib.Path(__file__).parent
REQUIREMENTS = (HERE / "requirements.txt").read_text()
requirements = REQUIREMENTS.splitlines()

setup(
    name="aibs_xenium_qc",
    version="0.0.1",
    description="Tools for QC on Xenium datasets using AIBS file storage structures",
    author="Paul Olsen",
    author_email="paul.olsen@alleninstitute.org",
    url="https://github.com/AllenInstitute/aibs_xenium_qc",
    license="LICENSE",
    packages=find_packages(where="."),
    include_package_data=True,
    package_data={
        'aibs_xenium_qc': ['metadata/*'],
    },
    install_requires=requirements + ['xenquaco @ git+https://github.com/polsen99/xenquaco.git#egg=xenquaco'],
)
