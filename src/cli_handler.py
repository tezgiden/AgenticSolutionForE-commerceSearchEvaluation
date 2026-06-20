"""Command line interface handler and argument parsing."""

import sys
import argparse
import logging
from typing import Dict, Any, List, Optional

from config.config_loader import ConfigLoader, AppConfig


logger = logging.getLogger(__name__)


class CLIHandler:
    """Handles command line interface operations and argument parsing."""
    
    def __init__(self):
        """Initialize the CLI handler."""
        self.config_loader = ConfigLoader()
    
    def parse_arguments(self) -> argparse.Namespace:
        """Parse command line arguments.
        
        Returns:
            Parsed arguments namespace
        """
        parser = self._create_argument_parser()
        return parser.parse_args()
    
    def handle_special_commands(self, args: argparse.Namespace) -> bool:
        """Handle special commands that don't require full execution.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            True if a special command was handled, False otherwise
        """
        # Handle list sites command
        if args.list_sites:
            self._handle_list_sites(args.config)
            return True
        
        # Handle validation command
        if args.validate:
            self._handle_validate_config(args.validate, args.config)
            return True
        
        return False
    
    def load_and_validate_config(self, args: argparse.Namespace) -> AppConfig:
        """Load and validate configuration based on arguments.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            Validated application configuration
            
        Raises:
            SystemExit: If configuration is invalid or site not specified
        """
        # Require site parameter for running
        if not args.site:
            available_sites = self._get_available_sites(args.config)
            self._print_error("--site parameter is required")
            print(f"Available sites: {available_sites}")
            sys.exit(1)
        
        # Load configuration with overrides
        try:
            config = self._load_config_with_overrides(args)
            self._validate_configuration(args.site, args.config)
            
            logger.info(f"Configuration loaded successfully for site: {args.site}")
            return config
            
        except Exception as e:
            self._print_error(f"Configuration error: {e}")
            sys.exit(1)
    
    def _create_argument_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser with all supported options.
        
        Returns:
            Configured argument parser
        """
        parser = argparse.ArgumentParser(
            description="Configurable Agentic Search Solution",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s --site truckpro                    # Run search for TruckPro site
  %(prog)s --list-sites                       # List available sites
  %(prog)s --validate truckpro               # Validate TruckPro configuration
  %(prog)s --site truckpro --model llama3    # Override default model
  %(prog)s --site truckpro --headless false  # Run with browser visible
            """
        )
        
        # Primary options
        parser.add_argument(
            "--site", 
            type=str, 
            help="Site configuration key (e.g., truckpro, tundrafmp)"
        )
        
        parser.add_argument(
            "--config", 
            type=str, 
            default="config.json", 
            help="Path to configuration file (default: config.json)"
        )
        
        # Information commands
        parser.add_argument(
            "--list-sites", 
            action="store_true", 
            help="List available site configurations and exit"
        )
        
        parser.add_argument(
            "--validate", 
            type=str, 
            help="Validate configuration for a specific site and exit"
        )
        
        # Configuration overrides
        parser.add_argument(
            "--model", 
            type=str, 
            help="Override the default LLM model"
        )
        
        parser.add_argument(
            "--max-results", 
            type=int, 
            help="Override max results per query"
        )
        
        parser.add_argument(
            "--headless", 
            type=self._str_to_bool, 
            help="Override headless browser setting (true/false)"
        )
        
        parser.add_argument(
            "--output-file", 
            type=str, 
            help="Override output file path"
        )
        
        parser.add_argument(
            "--debug", 
            action="store_true", 
            help="Enable debug mode with verbose logging"
        )
        
        parser.add_argument(
            "--environment", 
            type=str, 
            choices=["development", "production"], 
            help="Override deployment environment"
        )
        
        return parser
    
    def _handle_list_sites(self, config_path: str) -> None:
        """Handle the list sites command.
        
        Args:
            config_path: Path to configuration file
        """
        try:
            sites = self._get_available_sites(config_path)
            print("Available site configurations:")
            for site in sorted(sites):
                print(f"  - {site}")
        except Exception as e:
            self._print_error(f"Error listing sites: {e}")
            sys.exit(1)
    
    def _handle_validate_config(self, site_name: str, config_path: str) -> None:
        """Handle the validate configuration command.
        
        Args:
            site_name: Site to validate
            config_path: Path to configuration file
        """
        try:
            errors = self._validate_site_config(site_name, config_path)
            if errors:
                print(f"Configuration errors for {site_name}:")
                for error in errors:
                    print(f"  - {error}")
                sys.exit(1)
            else:
                print(f"✓ Configuration for {site_name} is valid!")
        except Exception as e:
            self._print_error(f"Error validating configuration: {e}")
            sys.exit(1)
    
    def _load_config_with_overrides(self, args: argparse.Namespace) -> AppConfig:
        """Load configuration and apply command line overrides.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            Configuration with overrides applied
        """
        # Create override dictionary
        overrides = self._build_overrides_dict(args)
        
        # Load configuration
        if overrides:
            config = self.config_loader.override_config(args.site, overrides)
            logger.info(f"Applied configuration overrides: {list(overrides.keys())}")
        else:
            config = self.config_loader.get_site_config(args.site)
        
        # Apply debug mode if specified
        if args.debug:
            config.deployment_config.log_level = "DEBUG"
            config.deployment_config.environment = "development"
            logger.info("Debug mode enabled")
        
        return config
    
    def _build_overrides_dict(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Build dictionary of configuration overrides from arguments.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            Dictionary of override values
        """
        overrides = {}
        
        if args.model:
            overrides["model"] = args.model
        
        if args.max_results:
            overrides["max_results"] = args.max_results
        
        if args.headless is not None:
            overrides["headless"] = args.headless
        
        if args.output_file:
            overrides["output_file"] = args.output_file
        
        if args.environment:
            overrides["environment"] = args.environment
        
        return overrides
    
    def _validate_configuration(self, site_name: str, config_path: str) -> None:
        """Validate configuration and exit if invalid.
        
        Args:
            site_name: Site to validate
            config_path: Path to configuration file
            
        Raises:
            SystemExit: If configuration is invalid
        """
        errors = self._validate_site_config(site_name, config_path)
        if errors:
            print("Configuration validation failed:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
    
    def _get_available_sites(self, config_path: str) -> List[str]:
        """Get list of available site configurations.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            List of available site names
        """
        try:
            # This would use the config_loader to get available sites
            # For now, implement a basic version
            return self.config_loader.get_available_sites(config_path)
        except AttributeError:
            # Fallback if method doesn't exist
            logger.warning("get_available_sites method not available, using fallback")
            return ["truckpro", "tundrafmp"]  # Default sites
    
    def _validate_site_config(self, site_name: str, config_path: str) -> List[str]:
        """Validate site configuration.
        
        Args:
            site_name: Site to validate
            config_path: Path to configuration file
            
        Returns:
            List of validation errors (empty if valid)
        """
        try:
            # This would use the config_loader to validate site config
            return self.config_loader.validate_config(site_name, config_path)
        except AttributeError:
            # Fallback if method doesn't exist
            logger.warning("validate_config method not available, using basic validation")
            try:
                self.config_loader.get_site_config(site_name)
                return []  # No errors if we can load the config
            except Exception as e:
                return [str(e)]
    
    @staticmethod
    def _str_to_bool(value: str) -> bool:
        """Convert string to boolean for argument parsing.
        
        Args:
            value: String value to convert
            
        Returns:
            Boolean value
            
        Raises:
            argparse.ArgumentTypeError: If value cannot be converted
        """
        if value.lower() in ('yes', 'true', 't', 'y', '1'):
            return True
        elif value.lower() in ('no', 'false', 'f', 'n', '0'):
            return False
        else:
            raise argparse.ArgumentTypeError(f"Boolean value expected, got: {value}")
    
    @staticmethod
    def _print_error(message: str) -> None:
        """Print error message to stderr.
        
        Args:
            message: Error message to print
        """
        print(f"Error: {message}", file=sys.stderr)


class ConfigurationValidator:
    """Validates configuration files and settings."""
    
    @staticmethod
    def validate_site_exists(site_name: str, available_sites: List[str]) -> bool:
        """Validate that a site exists in available configurations.
        
        Args:
            site_name: Site name to check
            available_sites: List of available sites
            
        Returns:
            True if site exists, False otherwise
        """
        return site_name in available_sites
    
    @staticmethod
    def validate_model_name(model_name: str) -> bool:
        """Validate LLM model name format.
        
        Args:
            model_name: Model name to validate
            
        Returns:
            True if valid format, False otherwise
        """
        # Basic validation - model names should be non-empty strings
        return isinstance(model_name, str) and len(model_name.strip()) > 0
    
    @staticmethod
    def validate_max_results(max_results: int) -> bool:
        """Validate max results parameter.
        
        Args:
            max_results: Maximum results value
            
        Returns:
            True if valid, False otherwise
        """
        return isinstance(max_results, int) and 1 <= max_results <= 100


class CLIHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Custom help formatter for better CLI help display."""
    
    def _format_action(self, action):
        """Format individual action help text."""
        # Get the default help text
        parts = super()._format_action(action)
        
        # Add additional formatting for specific actions
        if action.dest in ['site', 'config']:
            parts += "\n"
        
        return parts