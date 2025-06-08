from setuptools import setup, find_packages

setup(
    name="speech2text",
    version="0.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        # Dependencies will be installed from requirements.txt
    ],
    python_requires='>=3.10',
)
