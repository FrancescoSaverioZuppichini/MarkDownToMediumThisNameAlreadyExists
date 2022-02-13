from setuptools import setup, find_packages

setup(
    name='markdowntomedium',
    version='0.1.0',
    packages=find_packages(include=['src', 'src.*']),
    install_requires=[
        'requests',
    ],
     entry_points = {
        'console_scripts': ['markdowntomedium=src.main:main'],
    }

)