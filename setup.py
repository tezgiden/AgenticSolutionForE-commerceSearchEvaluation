"""
Setup script for the LLM Search Result Evaluation System.

This script configures the package for installation and distribution.
"""

from setuptools import setup, find_packages
import os
import re

# Read the README file for long description
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read the requirements file
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

# Get version from __init__.py
def get_version():
    with open("llm_evaluator/__init__.py", "r", encoding="utf-8") as fh:
        content = fh.read()
        version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", content, re.M)
        if version_match:
            return version_match.group(1)
        raise RuntimeError("Unable to find version string.")

# Package metadata
setup(
    name="llm-search-evaluator",
    version=get_version(),
    author="Tekin Tezgiden",
    author_email="team@example.com",
    description="Advanced LLM-based search result evaluation with inventory awareness",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/tezgiden/AgenticSolutionForE-commerceSearchEvaluation",
    project_urls={
        "Bug Tracker": "https://github.com/tezgiden/AgenticSolutionForE-commerceSearchEvaluation/issues",
        "Documentation": "https://github.com/tezgiden/AgenticSolutionForE-commerceSearchEvaluation/docs",
        "Source Code": "https://github.com/tezgiden/AgenticSolutionForE-commerceSearchEvaluation",
    },
    packages=find_packages(exclude=["tests*", "examples*", "docs*"]),
    classifiers=[
        # Development Status
        "Development Status :: 4 - Beta",
        
        # Intended Audience
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Information Technology",
        
        # Topic
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Topic :: Office/Business :: Financial :: Point-Of-Sale",
        
        # License
        "License :: OSI Approved :: MIT License",
        
        # Programming Language
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        
        # Operating System
        "Operating System :: OS Independent",
        
        # Environment
        "Environment :: Console",
        "Environment :: Web Environment",
        
        # Natural Language
        "Natural Language :: English",
    ],
    keywords=[
        "llm", "evaluation", "search", "e-commerce", "artificial-intelligence",
        "inventory", "ranking", "ollama", "natural-language-processing",
        "business-intelligence", "product-search", "relevance-scoring"
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "isort>=5.12.0",
            "pre-commit>=3.0.0",
        ],
        "docs": [
            "sphinx>=7.0.0",
            "sphinx-rtd-theme>=1.3.0",
            "sphinx-autodoc-typehints>=1.24.0",
        ],
        "enhanced": [
            "pydantic>=2.0.0",
            "click>=8.0.0", 
            "rich>=13.0.0",
            "tenacity>=8.0.0",
        ],
        "testing": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0",
            "responses>=0.23.0",
        ]
    },
    package_data={
        "llm_evaluator": [
            "py.typed",  # PEP 561 - typed package marker
        ],
    },
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "llm-evaluate=llm_evaluator.cli:main",
        ],
    },
    zip_safe=False,
    test_suite="tests",
)

# Additional setup configuration for development
if __name__ == "__main__":
    print("🚀 Setting up LLM Search Result Evaluation System...")
    print("📦 Package: llm-search-evaluator")
    print(f"📋 Version: {get_version()}")
    print("🔧 Installation complete!")
    print("\nNext steps:")
    print("1. Install Ollama: https://ollama.ai/")
    print("2. Pull a model: ollama pull gemma3")
    print("3. Start Ollama: ollama serve")
    print("4. Test the system: python -c 'from llm_evaluator import run_quick_test; run_quick_test()'")
