#!/usr/bin/env python3
"""
Multi-Site Deployment Manager for E-commerce Search Evaluation System.

This module provides a comprehensive deployment management system with proper
error handling, validation, reporting, and monitoring capabilities.

Usage:
    python deploy.py --site truckpro
    python deploy.py --site tundrafmp --model llama3
    python deploy.py --list-sites
    python deploy.py --validate-all
    python deploy.py --deploy-all
"""

import os
import sys
import argparse
import subprocess
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Protocol
from pathlib import Path

from config.config_loader import ConfigurationLoader, ConfigurationError


# ========================
# Custom Exceptions
# ========================

class DeploymentError(Exception):
    """Base exception for deployment-related errors."""
    pass


class DependencyError(DeploymentError):
    """Raised when required dependencies are missing."""
    pass


class ServiceError(DeploymentError):
    """Raised when required services are not available."""
    pass


class ValidationError(DeploymentError):
    """Raised when configuration validation fails."""
    pass


class ExecutionError(DeploymentError):
    """Raised when deployment execution fails."""
    pass


# ========================
# Data Models
# ========================

@dataclass
class DependencyStatus:
    """Status of system dependencies."""
    missing_packages: List[str] = field(default_factory=list)
    all_satisfied: bool = True
    
    def __post_init__(self):
        self.all_satisfied = len(self.missing_packages) == 0


@dataclass
class ServiceStatus:
    """Status of external services."""
    name: str
    running: bool
    available_resources: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    site_key: str
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class DeploymentResult:
    """Result of a deployment operation."""
    site_key: str
    success: bool
    execution_time: float
    stdout: str = ""
    stderr: str = ""
    error_message: Optional[str] = None
    
    @property
    def summary(self) -> str:
        """Get a summary of the deployment result."""
        status = "✓ SUCCESS" if self.success else "✗ FAILED"
        return f"{status} - {self.site_key} ({self.execution_time:.2f}s)"


@dataclass
class DeploymentReport:
    """Comprehensive deployment report."""
    timestamp: str
    total_sites: int
    successful_deployments: int
    failed_deployments: int
    site_results: Dict[str, Dict[str, Any]]
    recommendations: List[str]
    execution_summary: Dict[str, float]
    
    @property
    def success_rate(self) -> float:
        """Calculate deployment success rate."""
        if self.total_sites == 0:
            return 0.0
        return (self.successful_deployments / self.total_sites) * 100


# ========================
# Service Interfaces
# ========================

class DependencyChecker(Protocol):
    """Protocol for dependency checking."""
    
    def check_dependencies(self) -> DependencyStatus:
        """Check system dependencies."""
        ...


class ServiceChecker(Protocol):
    """Protocol for service status checking."""
    
    def check_service(self) -> ServiceStatus:
        """Check service status."""
        ...


class ConfigurationValidator(Protocol):
    """Protocol for configuration validation."""
    
    def validate_all(self) -> Dict[str, ValidationResult]:
        """Validate all configurations."""
        ...
    
    def validate_site(self, site_key: str) -> ValidationResult:
        """Validate specific site configuration."""
        ...


class DeploymentExecutor(Protocol):
    """Protocol for deployment execution."""
    
    def deploy_site(self, site_key: str, overrides: Dict[str, Any]) -> DeploymentResult:
        """Deploy a specific site."""
        ...


# ========================
# Dependency Management
# ========================

class PythonDependencyChecker:
    """Checks Python package dependencies."""
    
    REQUIRED_PACKAGES = [
        'selenium',
        'requests',
        'webdriver-manager'
    ]
    
    def check_dependencies(self) -> DependencyStatus:
        """Check if all required Python packages are installed."""
        missing_packages = []
        
        for package in self.REQUIRED_PACKAGES:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        return DependencyStatus(missing_packages=missing_packages)
    
    def get_installation_command(self, missing_packages: List[str]) -> str:
        """Get pip installation command for missing packages."""
        return f"pip install {' '.join(missing_packages)}"


# ========================
# Service Checkers
# ========================

class OllamaServiceChecker:
    """Checks Ollama service status and available models."""
    
    def __init__(self, api_endpoint: str = "http://localhost:11434"):
        self.api_endpoint = api_endpoint
    
    def check_service(self) -> ServiceStatus:
        """Check if Ollama is running and get available models."""
        try:
            import requests
            
            response = requests.get(f"{self.api_endpoint}/api/tags", timeout=5)
            
            if response.status_code == 200:
                models = [model["name"] for model in response.json().get("models", [])]
                return ServiceStatus(
                    name="Ollama",
                    running=True,
                    available_resources=models
                )
            else:
                return ServiceStatus(
                    name="Ollama",
                    running=False,
                    error_message=f"API returned status {response.status_code}"
                )
                
        except Exception as e:
            return ServiceStatus(
                name="Ollama",
                running=False,
                error_message=str(e)
            )


# ========================
# Configuration Validation
# ========================

class ComprehensiveConfigurationValidator:
    """Comprehensive configuration validator."""
    
    def __init__(self, config_loader: ConfigurationLoader):
        self.config_loader = config_loader
    
    def validate_all(self) -> Dict[str, ValidationResult]:
        """Validate all site configurations."""
        validation_results = {}
        sites = self.config_loader.get_available_sites()
        
        for site in sites:
            validation_results[site] = self.validate_site(site)
        
        return validation_results
    
    def validate_site(self, site_key: str) -> ValidationResult:
        """Validate specific site configuration."""
        errors = self.config_loader.validate_site_config(site_key)
        
        # Additional validation logic can be added here
        warnings = self._check_warnings(site_key)
        
        return ValidationResult(
            site_key=site_key,
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _check_warnings(self, site_key: str) -> List[str]:
        """Check for configuration warnings."""
        warnings = []
        
        try:
            config = self.config_loader.get_site_config(site_key)
            
            # Check for potential performance issues
            if config.site_config.scraping_config.max_results_per_query > 20:
                warnings.append("High max_results_per_query may impact performance")
            
            if config.chrome_config.window_size["width"] > 3840:
                warnings.append("Very large window size may consume excessive memory")
            
            if not config.chrome_config.headless:
                warnings.append("Non-headless mode may impact performance in production")
            
        except Exception:
            # If we can't load config, errors will be caught in main validation
            pass
        
        return warnings


# ========================
# Deployment Execution
# ========================

class SubprocessDeploymentExecutor:
    """Executes deployments using subprocess calls."""
    
    def __init__(self, main_script: str = "main.py"):
        self.main_script = main_script
    
    def deploy_site(self, site_key: str, config_path: str = "config.json", 
                   overrides: Optional[Dict[str, Any]] = None) -> DeploymentResult:
        """Deploy a specific site using subprocess execution."""
        start_time = time.time()
        
        try:
            cmd = self._build_command(site_key, config_path, overrides or {})
            
            print(f"Executing: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            execution_time = time.time() - start_time
            
            return DeploymentResult(
                site_key=site_key,
                success=result.returncode == 0,
                execution_time=execution_time,
                stdout=result.stdout,
                stderr=result.stderr,
                error_message=None if result.returncode == 0 else f"Process exited with code {result.returncode}"
            )
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            return DeploymentResult(
                site_key=site_key,
                success=False,
                execution_time=execution_time,
                error_message="Deployment timed out after 1 hour"
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return DeploymentResult(
                site_key=site_key,
                success=False,
                execution_time=execution_time,
                error_message=f"Execution error: {e}"
            )
    
    def _build_command(self, site_key: str, config_path: str, 
                      overrides: Dict[str, Any]) -> List[str]:
        """Build the command line arguments for deployment."""
        cmd = [sys.executable, self.main_script, "--site", site_key, "--config", config_path]
        
        # Add override arguments
        override_mappings = {
            "model": "--model",
            "max_results": "--max-results",
            "headless": "--headless",
            "output_file": "--output-file"
        }
        
        for key, value in overrides.items():
            if key in override_mappings:
                cmd.extend([override_mappings[key], str(value)])
        
        return cmd


# ========================
# Report Generation
# ========================

class DeploymentReportGenerator:
    """Generates comprehensive deployment reports."""
    
    def __init__(self, config_loader: ConfigurationLoader):
        self.config_loader = config_loader
    
    def generate_report(self, results: Dict[str, DeploymentResult], 
                       config_path: str = "config.json") -> DeploymentReport:
        """Generate a comprehensive deployment report."""
        successful_deployments = sum(1 for result in results.values() if result.success)
        failed_deployments = len(results) - successful_deployments
        
        site_results = {}
        total_execution_time = 0.0
        
        for site_key, result in results.items():
            total_execution_time += result.execution_time
            
            try:
                config = self.config_loader.get_site_config(site_key)
                site_results[site_key] = {
                    "success": result.success,
                    "execution_time": result.execution_time,
                    "site_name": config.site_config.site_name,
                    "target_url": config.site_config.target_url,
                    "output_file": config.site_config.output_config.output_file,
                    "error_message": result.error_message
                }
            except Exception as e:
                site_results[site_key] = {
                    "success": False,
                    "execution_time": result.execution_time,
                    "error": str(e),
                    "error_message": result.error_message
                }
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            successful_deployments, failed_deployments, len(results)
        )
        
        # Calculate execution summary
        execution_summary = {
            "total_time": total_execution_time,
            "average_time": total_execution_time / len(results) if results else 0.0,
            "fastest": min((r.execution_time for r in results.values()), default=0.0),
            "slowest": max((r.execution_time for r in results.values()), default=0.0)
        }
        
        return DeploymentReport(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_sites=len(results),
            successful_deployments=successful_deployments,
            failed_deployments=failed_deployments,
            site_results=site_results,
            recommendations=recommendations,
            execution_summary=execution_summary
        )
    
    def save_report(self, report: DeploymentReport, filename: str = "deployment_report.json") -> None:
        """Save deployment report to file."""
        report_data = {
            "timestamp": report.timestamp,
            "summary": {
                "total_sites": report.total_sites,
                "successful_deployments": report.successful_deployments,
                "failed_deployments": report.failed_deployments,
                "success_rate": f"{report.success_rate:.1f}%"
            },
            "execution_summary": report.execution_summary,
            "site_results": report.site_results,
            "recommendations": report.recommendations
        }
        
        try:
            with open(filename, "w") as f:
                json.dump(report_data, f, indent=4)
            print(f"📊 Deployment report saved to {filename}")
        except Exception as e:
            print(f"❌ Failed to save report: {e}")
    
    def _generate_recommendations(self, successful: int, failed: int, total: int) -> List[str]:
        """Generate recommendations based on deployment results."""
        recommendations = []
        
        if failed > 0:
            recommendations.append(
                f"Review {failed} failed deployment(s) and check configuration/dependencies"
            )
        
        if successful == total and total > 0:
            recommendations.append("All deployments successful - ready for production")
        elif successful > 0:
            recommendations.append("Consider investigating failed deployments before production")
        
        if total > 5:
            recommendations.append("Consider implementing parallel deployments for better performance")
        
        return recommendations


# ========================
# Main Deployment Manager
# ========================

class DeploymentManager:
    """Main deployment manager that orchestrates all deployment operations."""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config_loader = ConfigurationLoader.from_file(config_path)
        
        # Initialize components
        self.dependency_checker = PythonDependencyChecker()
        self.ollama_checker = OllamaServiceChecker()
        self.config_validator = ComprehensiveConfigurationValidator(self.config_loader)
        self.deployment_executor = SubprocessDeploymentExecutor()
        self.report_generator = DeploymentReportGenerator(self.config_loader)
    
    def check_system_readiness(self) -> bool:
        """Check if system is ready for deployment."""
        print("🔍 Checking system readiness...")
        
        # Check dependencies
        dep_status = self.dependency_checker.check_dependencies()
        if not dep_status.all_satisfied:
            print(f"❌ Missing dependencies: {dep_status.missing_packages}")
            print(f"Install with: {self.dependency_checker.get_installation_command(dep_status.missing_packages)}")
            return False
        print("✅ All dependencies satisfied")
        
        # Check Ollama service
        ollama_status = self.ollama_checker.check_service()
        if not ollama_status.running:
            print(f"❌ Ollama service not running: {ollama_status.error_message}")
            print("Start Ollama with: ollama serve")
            return False
        print(f"✅ Ollama running with {len(ollama_status.available_resources)} models")
        
        return True
    
    def list_available_sites(self) -> None:
        """List all available site configurations."""
        print("📋 Available site configurations:")
        
        sites = self.config_loader.get_available_sites()
        if not sites:
            print("  No sites configured")
            return
        
        for site in sites:
            try:
                config = self.config_loader.get_site_config(site)
                print(f"  📍 {site}: {config.site_config.site_name}")
                print(f"     URL: {config.site_config.target_url}")
                print(f"     Tasks: {len(config.site_config.search_tasks)} search queries")
            except Exception as e:
                print(f"  ❌ {site}: Error loading config - {e}")
    
    def validate_all_configurations(self) -> bool:
        """Validate all site configurations."""
        print("🔍 Validating all site configurations...")
        
        validation_results = self.config_validator.validate_all()
        
        all_valid = True
        for site, result in validation_results.items():
            if result.is_valid:
                print(f"✅ {site}: Valid")
                if result.warnings:
                    for warning in result.warnings:
                        print(f"   ⚠️  {warning}")
            else:
                print(f"❌ {site}: {len(result.errors)} error(s)")
                for error in result.errors:
                    print(f"     • {error}")
                all_valid = False
        
        if all_valid:
            print("\n✅ All configurations are valid")
        else:
            print("\n❌ Some configurations have errors")
        
        return all_valid
    
    def deploy_site(self, site_key: str, overrides: Optional[Dict[str, Any]] = None) -> bool:
        """Deploy a specific site."""
        print(f"🚀 Deploying {site_key}...")
        
        # Validate site configuration
        validation_result = self.config_validator.validate_site(site_key)
        if not validation_result.is_valid:
            print(f"❌ Configuration validation failed for {site_key}:")
            for error in validation_result.errors:
                print(f"   • {error}")
            return False
        
        # Check system readiness
        if not self.check_system_readiness():
            return False
        
        # Execute deployment
        if overrides:
            print(f"📝 Using overrides: {overrides}")
        
        result = self.deployment_executor.deploy_site(site_key, self.config_path, overrides)
        
        # Display results
        print(result.summary)
        
        if result.success:
            print("📊 Deployment completed successfully")
            if result.stdout:
                # Show last 500 characters of stdout
                stdout_preview = result.stdout[-500:] if len(result.stdout) > 500 else result.stdout
                print(f"Output preview: ...{stdout_preview}")
        else:
            print("❌ Deployment failed")
            if result.stderr:
                print(f"Error: {result.stderr}")
            if result.error_message:
                print(f"Message: {result.error_message}")
        
        return result.success
    
    def deploy_all_sites(self, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, DeploymentResult]:
        """Deploy all configured sites."""
        sites = self.config_loader.get_available_sites()
        
        if not sites:
            raise DeploymentError("No sites found in configuration")
        
        print(f"🚀 Deploying all sites ({len(sites)} total)...")
        
        # Check system readiness once
        if not self.check_system_readiness():
            raise DeploymentError("System not ready for deployment")
        
        if overrides:
            print(f"📝 Using overrides: {overrides}")
        
        results = {}
        
        for i, site in enumerate(sites, 1):
            print(f"\n{'='*60}")
            print(f"🏗️  Deploying {site} ({i}/{len(sites)})")
            print(f"{'='*60}")
            
            result = self.deployment_executor.deploy_site(site, self.config_path, overrides)
            results[site] = result
            
            print(result.summary)
            
            if not result.success and result.error_message:
                print(f"   Error: {result.error_message}")
        
        # Generate and save report
        report = self.report_generator.generate_report(results, self.config_path)
        self.report_generator.save_report(report)
        
        # Display summary
        print(f"\n📊 Deployment Summary:")
        print(f"   Total sites: {report.total_sites}")
        print(f"   Successful: {report.successful_deployments}")
        print(f"   Failed: {report.failed_deployments}")
        print(f"   Success rate: {report.success_rate:.1f}%")
        print(f"   Total time: {report.execution_summary['total_time']:.1f}s")
        
        return results


# ========================
# Command Line Interface
# ========================

class DeploymentCLI:
    """Command line interface for deployment operations."""
    
    def __init__(self):
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create command line argument parser."""
        parser = argparse.ArgumentParser(
            description="Multi-Site Deployment Manager for E-commerce Search Evaluation",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s --site truckpro                    # Deploy single site
  %(prog)s --site truckpro --model llama3     # Deploy with model override
  %(prog)s --deploy-all                       # Deploy all sites
  %(prog)s --list-sites                       # List available sites
  %(prog)s --validate-all                     # Validate all configurations
  %(prog)s --check-deps                       # Check dependencies
  %(prog)s --check-ollama                     # Check Ollama status
            """
        )
        
        # Main actions
        parser.add_argument("--site", type=str, 
                          help="Deploy specific site")
        parser.add_argument("--deploy-all", action="store_true", 
                          help="Deploy all configured sites")
        
        # Information commands
        parser.add_argument("--list-sites", action="store_true", 
                          help="List available site configurations")
        parser.add_argument("--validate-all", action="store_true", 
                          help="Validate all site configurations")
        parser.add_argument("--check-deps", action="store_true", 
                          help="Check system dependencies")
        parser.add_argument("--check-ollama", action="store_true", 
                          help="Check Ollama service status")
        
        # Configuration
        parser.add_argument("--config", type=str, default="config.json", 
                          help="Path to configuration file (default: config.json)")
        
        # Override options
        parser.add_argument("--model", type=str, 
                          help="Override LLM model")
        parser.add_argument("--max-results", type=int, 
                          help="Override maximum results per query")
        parser.add_argument("--headless", type=bool, 
                          help="Override headless browser setting")
        parser.add_argument("--output-file", type=str, 
                          help="Override output file path")
        
        return parser
    
    def run(self, args: Optional[List[str]] = None) -> int:
        """Run the CLI with given arguments."""
        try:
            parsed_args = self.parser.parse_args(args)
            return self._execute_command(parsed_args)
        except KeyboardInterrupt:
            print("\n\n🛑 Deployment interrupted by user")
            return 1
        except Exception as e:
            print(f"❌ Deployment error: {e}")
            return 1
    
    def _execute_command(self, args: argparse.Namespace) -> int:
        """Execute the parsed command."""
        # Check if configuration file exists
        if not os.path.exists(args.config):
            print(f"❌ Configuration file '{args.config}' not found")
            return 1
        
        try:
            deployment_manager = DeploymentManager(args.config)
        except ConfigurationError as e:
            print(f"❌ Configuration error: {e}")
            return 1
        
        # Handle information commands
        if args.check_deps:
            return self._handle_check_deps(deployment_manager)
        
        if args.check_ollama:
            return self._handle_check_ollama(deployment_manager)
        
        if args.list_sites:
            deployment_manager.list_available_sites()
            return 0
        
        if args.validate_all:
            success = deployment_manager.validate_all_configurations()
            return 0 if success else 1
        
        # Prepare overrides
        overrides = self._build_overrides(args)
        
        # Handle deployment commands
        if args.deploy_all:
            return self._handle_deploy_all(deployment_manager, overrides)
        
        if args.site:
            return self._handle_deploy_site(deployment_manager, args.site, overrides)
        
        # If no command specified, show help
        self.parser.print_help()
        return 0
    
    def _handle_check_deps(self, manager: DeploymentManager) -> int:
        """Handle dependency check command."""
        print("🔍 Checking dependencies...")
        dep_status = manager.dependency_checker.check_dependencies()
        
        if dep_status.all_satisfied:
            print("✅ All dependencies are installed")
            return 0
        else:
            print(f"❌ Missing dependencies: {dep_status.missing_packages}")
            print(f"Install with: {manager.dependency_checker.get_installation_command(dep_status.missing_packages)}")
            return 1
    
    def _handle_check_ollama(self, manager: DeploymentManager) -> int:
        """Handle Ollama status check command."""
        print("🔍 Checking Ollama status...")
        ollama_status = manager.ollama_checker.check_service()
        
        if ollama_status.running:
            print("✅ Ollama is running")
            print(f"📦 Available models: {ollama_status.available_resources}")
            return 0
        else:
            print("❌ Ollama is not running or not accessible")
            print(f"Error: {ollama_status.error_message}")
            print("Start Ollama with: ollama serve")
            return 1
    
    def _handle_deploy_all(self, manager: DeploymentManager, 
                          overrides: Dict[str, Any]) -> int:
        """Handle deploy all command."""
        try:
            results = manager.deploy_all_sites(overrides)
            success_count = sum(1 for result in results.values() if result.success)
            return 0 if success_count == len(results) else 1
        except DeploymentError as e:
            print(f"❌ Deployment failed: {e}")
            return 1
    
    def _handle_deploy_site(self, manager: DeploymentManager, site_key: str, 
                           overrides: Dict[str, Any]) -> int:
        """Handle single site deployment command."""
        try:
            success = manager.deploy_site(site_key, overrides)
            return 0 if success else 1
        except DeploymentError as e:
            print(f"❌ Deployment failed: {e}")
            return 1
    
    def _build_overrides(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Build configuration overrides from command line arguments."""
        overrides = {}
        
        if args.model:
            overrides["model"] = args.model
        if args.max_results:
            overrides["max_results"] = args.max_results
        if args.headless is not None:
            overrides["headless"] = args.headless
        if args.output_file:
            overrides["output_file"] = args.output_file
        
        return overrides


# ========================
# Main Entry Point
# ========================

def main() -> int:
    """Main entry point for the deployment script."""
    cli = DeploymentCLI()
    return cli.run()


if __name__ == "__main__":
    sys.exit(main())