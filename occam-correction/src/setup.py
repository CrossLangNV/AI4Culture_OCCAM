from setuptools import setup, find_packages


with open("requirements.txt") as f:
    requirements = f.read().splitlines()


setup(
    name="ocr_correction",
    version="0.1",
    packages=find_packages(exclude=["tests"]),
    install_requires=requirements,
    author="Laurens Meeus",
    # description='Description of your package',
    # url='https://github.com/your_username/your_package',
    classifiers=[
        # Include any classifiers relevant to your package
        # For example: 'Development Status :: 3 - Alpha',
        #              'License :: OSI Approved :: MIT License',
        #              'Programming Language :: Python :: 3',
        "License :: OSI Approved :: Apache License 2.0",
    ],
)
