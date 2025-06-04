#!/usr/bin/env python3
"""
Multi-Site Deployment Script for Agentic Search Solution

This script demonstrates how to deploy the same codebase for different sites
using configuration-driven approach.

Usage:
    python deploy.py --site truckpro
    python deploy.py --site tundrafmp --model llama3
    python deploy.py --list-sites
    python deploy.py --validate-all
"""

import os
import sys
import argparse
import subprocess
import json
from typing import List, Dict, Any
from config_loader import ConfigLoader, get_available_sites, validate_site_config

def check_dependencies() -> List[str]:
    """Check if all required dependencies are installed"""
    missing_deps = []
    required_packages = [
        'selenium',
        'requests', 
        'webdriver-manager'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_deps.append(package)
    
    return missing_deps

def check_ollama_status() -> Dict[str, Any]:
    """Check if Ollama is running and what models are available"""
    import requests
    
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = [model["name"] for model in response.json().get("models", [])]
            return {
                "running": True,
                "available_models": models,
                "error": None
            }
        else:
            return {
                "running": False,
                "available_models": [],
                "error": f"Ollama API returned status {response.status_code}"
            }
    except Exception as e:
        return {
            "running": False,
            "available_models": [],
            "error": str(e)
        }

def validate_all_configs(config_path: str = "config.json") -> Dict[str, List[str]]:
    """Validate all site configurations"""
    loader = ConfigLoader(config_path)
    sites = loader.get_available_sites()
    
    validation_results = {}
    for site in sites:
        errors = loader.validate_config(site)
        validation_results[site] = errors
    
    return validation_results

def run_site_deployment(site_key: str, config_path: str = "config.json", 
                       overrides: Dict[str, Any] = None) -> bool:
    """Run deployment for a specific site"""
    try:
        # Build command
        cmd = [sys.executable, "main.py", "--site", site_key, "--config", config_path]
        
        # Add overrides if provided
        if overrides:
            if "model" in overrides:
                cmd.extend(["--model", overrides["model"]])
            if "max_results" in overrides:
                cmd.extend(["--max-results", str(overrides["max_results"])])
            if "headless" in overrides:
                cmd.extend(["--headless", str(overrides["headless"])])
            if "output_file" in overrides:
                cmd.extend(["--output-file", overrides["output_file"]])
        
        print(f"Running command: {' '.join(cmd)}")
        
        # Execute the command
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✓ Successfully completed deployment for {site_key}")
            print("STDOUT:", result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
            return True
        else:
            print(f"✗ Deployment failed for {site_key}")
            print("STDERR:", result.stderr)
            print("STDOUT:", result.stdout)
            return False
            
    except Exception as e:
        print(f"✗ Error running deployment for {site_key}: {e}")
        return False

def generate_deployment_report(results: Dict[str, bool], config_path: str = "config.json") -> None:
    """Generate a deployment report"""
    loader = ConfigLoader(config_path)
    
    report = {
        "deployment_timestamp": __import__('time').strftime("%Y-%m-%d %H:%M:%S"),
        "total_sites": len(results),
        "successful_deployments": sum(results.values()),
        "failed_deployments": len(results) - sum(results.values()),
        "site_results": {},
        "recommendations": []
    }
    
    for site_key, success in results.items():
        try:
            config = loader.get_site_config(site_key)
            report["site_results"][site_key] = {
                "success": success,
                "site_name": config.site_config.site_name,
                "target_url": config.site_config.target_url,
                "output_file": config.site_config.output_config.output_file
            }
        except Exception as e:
            report["site_results"][site_key] = {
                "success": False,
                "error": str(e)
            }
    
    # Generate recommendations
    if report["failed_deployments"] > 0:
        report["recommendations"].append("Review failed deployments and check configuration")
    
    if report["successful_deployments"] == report["total_sites"]:
        report["recommendations"].append("All deployments successful - ready for production")
    
    # Save report
    report_file = "deployment_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=4)
    
    print(f"\nDeployment report saved to {report_file}")
    print(f"Summary: {report['successful_deployments']}/{report['total_sites']} deployments successful")

def main():
    parser = argparse.ArgumentParser(description="Multi-Site Deployment Script")
    parser.add_argument("--site", type=str, help="Deploy specific site")
    parser.add_argument("--config", type=str, default="config.json", help="Configuration file path")
    parser.add_argument("--list-sites", action="store_true", help="List available sites")
    parser.add_argument("--validate-all", action="store_true", help="Validate all configurations")
    parser.add_argument("--check-deps", action="store_true", help="Check dependencies")
    parser.add_argument("--check-ollama", action="store_true", help="Check Ollama status")
    parser.add_argument("--deploy-all", action="store_true", help="Deploy all sites")
    parser.add_argument("--model", type=str, help="Override LLM model")
    parser.add_argument("--max-results", type=int, help="Override max results per query")
    parser.add_argument("--headless", type=bool, help="Override headless browser setting")
    parser.add_argument("--output-file", type=str, help="Override output file")
    
    args = parser.parse_args()
    
    # Check if configuration file exists
    if not os.path.exists(args.config):
        print(f"Error: Configuration file '{args.config}' not found")
        sys.exit(1)
    
    try:
        # Handle dependency check
        if args.check_deps:
            print("Checking dependencies...")
            missing = check_dependencies()
            if missing:
                print(f"Missing dependencies: {missing}")
                print(f"Install with: pip install {' '.join(missing)}")
                sys.exit(1)
            else:
                print("✓ All dependencies are installed")
            return
        
        # Handle Ollama status check
        if args.check_ollama:
            print("Checking Ollama status...")
            status = check_ollama_status()
            if status["running"]:
                print("✓ Ollama is running")
                print(f"Available models: {status['available_models']}")
            else:
                print("✗ Ollama is not running or not accessible")
                print(f"Error: {status['error']}")
                print("Start Ollama with: ollama serve")
                sys.exit(1)
            return
        
        # Handle list sites
        if args.list_sites:
            sites = get_available_sites(args.config)
            print("Available site configurations:")
            loader = ConfigLoader(args.config)
            for site in sites:
                try:
                    config = loader.get_site_config(site)
                    print(f"  - {site}: {config.site_config.site_name} ({config.site_config.target_url})")
                except Exception as e:
                    print(f"  - {site}: Error loading config - {e}")
            return
        
        # Handle validate all
        if args.validate_all:
            print("Validating all site configurations...")
            validation_results = validate_all_configs(args.config)
            
            all_valid = True
            for site, errors in validation_results.items():
                if errors:
                    print(f"✗ {site}: {len(errors)} errors")
                    for error in errors:
                        print(f"    - {error}")
                    all_valid = False
                else:
                    print(f"✓ {site}: Valid")
            
            if all_valid:
                print("\n✓ All configurations are valid")
            else:
                print("\n✗ Some configurations have errors")
                sys.exit(1)
            return
        
        # Prepare overrides
        overrides = {}
        if args.model:
            overrides["model"] = args.model
        if args.max_results:
            overrides["max_results"] = args.max_results
        if args.headless is not None:
            overrides["headless"] = args.headless
        if args.output_file:
            overrides["output_file"] = args.output_file
        
        # Handle deploy all
        if args.deploy_all:
            print("Deploying all sites...")
            sites = get_available_sites(args.config)
            
            if not sites:
                print("No sites found in configuration")
                sys.exit(1)
            
            # Check dependencies first
            missing = check_dependencies()
            if missing:
                print(f"Missing dependencies: {missing}")
                print(f"Install with: pip install {' '.join(missing)}")
                sys.exit(1)
            
            # Check Ollama status
            ollama_status = check_ollama_status()
            if not ollama_status["running"]:
                print("Ollama is not running. Start it with: ollama serve")
                sys.exit(1)
            
            print(f"Found {len(sites)} sites to deploy")
            if overrides:
                print(f"Using overrides: {overrides}")
            
            results = {}
            for site in sites:
                print(f"\n{'='*50}")
                print(f"Deploying {site}...")
                print(f"{'='*50}")
                
                success = run_site_deployment(site, args.config, overrides)
                results[site] = success
                
                if not success:
                    print(f"Failed to deploy {site}")
            
            # Generate deployment report
            generate_deployment_report(results, args.config)
            return
        
        # Handle single site deployment
        if args.site:
            # Validate the specific site first
            errors = validate_site_config(args.site, args.config)
            if errors:
                print(f"Configuration errors for {args.site}:")
                for error in errors:
                    print(f"  - {error}")
                sys.exit(1)
            
            # Check dependencies
            missing = check_dependencies()
            if missing:
                print(f"Missing dependencies: {missing}")
                print(f"Install with: pip install {' '.join(missing)}")
                sys.exit(1)
            
            # Check Ollama status
            ollama_status = check_ollama_status()
            if not ollama_status["running"]:
                print("Ollama is not running. Start it with: ollama serve")
                sys.exit(1)
            
            print(f"Deploying {args.site}...")
            if overrides:
                print(f"Using overrides: {overrides}")
            
            success = run_site_deployment(args.site, args.config, overrides)
            
            if success:
                print(f"\n✓ Successfully deployed {args.site}")
            else:
                print(f"\n✗ Failed to deploy {args.site}")
                sys.exit(1)
            return
        
        # If no specific action is provided, show help
        parser.print_help()
        
    except KeyboardInterrupt:
        print("\n\nDeployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Deployment error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()