"""Setup script for the Enterprise Web Scraper package."""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    """Read README.md for long description."""
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Enterprise Web Scraper - A modular, scalable web scraping framework"

# Read requirements
def read_requirements():
    """Read requirements.txt for dependencies."""
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r', encoding='utf-8') as f:
            # Filter out comments and optional dependencies
            requirements = []
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-'):
                    requirements.append(line)
            return requirements
    return [
        'selenium>=4.15.0',
        'webdriver-manager>=4.0.0',
        'pandas>=2.0.0',
        'openpyxl>=3.1.0',
    ]

setup(
    name="enterprise-web-scraper",
    version="2.0.0",
    author="Your Organization",
    author_email="dev@yourorganization.com",
    description="A modular, enterprise-grade web scraping framework",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourorg/enterprise-web-scraper",
    packages=find_packages(exclude=['tests*', 'examples*', 'docs*']),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
        "Topic :: Software Development :: Testing",
        "Topic :: System :: Monitoring",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'pytest-mock>=3.10.0',
            'black>=23.0.0',
            'isort>=5.12.0',
            'flake8>=6.0.0',
            'mypy>=1.5.0',
            'pre-commit>=3.3.0',
        ],
        'monitoring': [
            'prometheus-client>=0.17.0',
            'structlog>=23.0.0',
        ],
        'cloud': [
            'boto3>=1.28.0',
            'google-cloud-storage>=2.10.0',
            'azure-storage-blob>=12.17.0',
        ],
        'api': [
            'fastapi>=0.100.0',
            'uvicorn>=0.23.0',
        ],
        'ml': [
            'scikit-learn>=1.3.0',
            'numpy>=1.24.0',
            'scipy>=1.10.0',
        ],
        'distributed': [
            'celery>=5.3.0',
            'redis>=4.5.0',
            'dramatiq>=1.14.0',
        ],
        'advanced': [
            'beautifulsoup4>=4.12.0',
            'lxml>=4.9.0',
            'fake-useragent>=1.4.0',
            'Pillow>=10.0.0',
        ],
        'database': [
            'sqlalchemy>=2.0.0',
            'psycopg2-binary>=2.9.0',
            'pymongo>=4.0.0',
        ],
        'docs': [
            'sphinx>=7.0.0',
            'sphinx-rtd-theme>=1.3.0',
        ],
        'all': [
            # Includes all optional dependencies
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'pytest-mock>=3.10.0',
            'black>=23.0.0',
            'isort>=5.12.0',
            'flake8>=6.0.0',
            'mypy>=1.5.0',
            'pre-commit>=3.3.0',
            'prometheus-client>=0.17.0',
            'structlog>=23.0.0',
            'boto3>=1.28.0',
            'fastapi>=0.100.0',
            'uvicorn>=0.23.0',
            'scikit-learn>=1.3.0',
            'numpy>=1.24.0',
            'celery>=5.3.0',
            'redis>=4.5.0',
            'beautifulsoup4>=4.12.0',
            'lxml>=4.9.0',
            'sqlalchemy>=2.0.0',
            'sphinx>=7.0.0',
        ]
    },
    entry_points={
        'console_scripts': [
            'web-scraper=cli_interface:main',
            'scraper-cli=cli_interface:main',
        ],
    },
    include_package_data=True,
    package_data={
        'enterprise_web_scraper': [
            'config/*.json',
            'templates/*.html',
            'static/*',
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/yourorg/enterprise-web-scraper/issues",
        "Source": "https://github.com/yourorg/enterprise-web-scraper",
        "Documentation": "https://enterprise-web-scraper.readthedocs.io/",
    },
    keywords=[
        "web scraping",
        "selenium",
        "automation",
        "data extraction",
        "enterprise",
        "modular",
        "scalable",
        "monitoring",
        "rate limiting",
        "testing"
    ],
    zip_safe=False,
)

# Additional setup for development
if __name__ == "__main__":
    import subprocess
    import sys
    
    # Check if this is a development installation
    if len(sys.argv) > 1 and sys.argv[1] == "develop":
        print("Setting up development environment...")
        
        # Install pre-commit hooks
        try:
            subprocess.run(["pre-commit", "install"], check=True)
            print("✅ Pre-commit hooks installed")
        except subprocess.CalledProcessError:
            print("⚠️  Failed to install pre-commit hooks")
        except FileNotFoundError:
            print("⚠️  pre-commit not found. Install with: pip install pre-commit")
        
        print("Development setup complete!")
        print("\nNext steps:")
        print("1. Run tests: pytest")
        print("2. Check code style: black . && isort . && flake8")
        print("3. Type checking: mypy .")
        print("4. Run example: python example_usage.py")
        print("5. CLI help: web-scraper --help")