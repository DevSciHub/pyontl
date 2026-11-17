from setuptools import setup, find_packages

setup(
    name="pyontl",
    version="1.1.0",
    author="DevSci",
    author_email="dev.sci.space@gmail.com",
    maintainer="Bruno Oliveira",
    maintainer_email="brunoalvesdeoliveira96@gamil.com",
    description="Biblioteca para acesso a dados da ONTL.",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.0",
        "pandas>=1.1.0",
        "urllib3>=1.26,<3",
    ],
    python_requires=">=3.8",
)
