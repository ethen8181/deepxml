import os
import re
from setuptools import setup, find_packages


# top-level information
NAME = 'deepxml'
SRC_ROOT = 'deepxml'
DESCRIPTION = 'DeepXML'
KEYWORDS = 'DeepXML'


def get_version(src_root):
    """
    Look for version, __version__, under
    the __init__.py file of the package.
    """
    file = os.path.join(src_root, '__init__.py')
    with open(file) as f:
        matched = re.findall("__version__ = '([\d.\w]+)'", f.read())
        version = matched[0]

    return version


with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name=NAME,
    version=get_version(SRC_ROOT),
    description=DESCRIPTION,
    keywords=KEYWORDS,
    license='MIT',
    author='Ethen',
    author_email='ethen8181@gmail.com',
    classifiers=[
        'Natural Language :: English',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'License :: OSI Approved :: MIT License'],
    install_requires=required,
    packages=find_packages()
)
