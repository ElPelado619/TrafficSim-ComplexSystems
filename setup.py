"""
Setup script para el paquete de simulación de tráfico.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Leer el README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

setup(
    name="traffic-simulation-ns",
    version="1.0.0",
    author="Tu Nombre",
    description="Simulación de tráfico usando el modelo de Nagel-Schreckenberg",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tuusuario/traffic-simulation",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Physics",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "osmnx>=1.9.0",
        "networkx>=3.0",
        "numpy>=1.24.0",
        "matplotlib>=3.7.0",
        "pillow>=10.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=23.0",
            "flake8>=6.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "traffic-sim=run:main",
        ],
    },
)
