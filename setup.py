import sys
from setuptools import setup, find_packages

pyversion = sys.version_info
if pyversion[0] == 2 and pyversion[1] >= 6:
    python_req = ">=2.6"
elif pyversion >= (3, 6):
    python_req = ">=3.6"
else:
    # python_requires is only availabe since setuptools 24.2.0 and pip 9.0.0
    sys.exit("Python 2.6 (or newer) or 3.6 (or newer) is required to use this package.")

# muninn would also be required for running the muninn-startapp command,
# but is not included here as a mandatory dependency.
requirements = [
    "django",
    "djangorestframework",
    "djangorestframework-gis",
]


setup(
    name="muninn_django",
    version="1.2",
    description="Django and REST interface for the muninn product archive",
    url="http://stcorp.nl/",
    author="S[&]T",
    author_email="info@stcorp.nl",
    license="All rights reserved",
    packages=find_packages(),
    python_requires=python_req,
    install_requires=requirements,
)
