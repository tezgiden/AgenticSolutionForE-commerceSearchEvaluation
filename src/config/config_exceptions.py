class ConfigurationError(Exception):
    """Base exception for configuration-related errors."""
    pass


class ConfigurationFileError(ConfigurationError):
    """Raised when configuration file cannot be found or read."""
    pass


class ConfigurationValidationError(ConfigurationError):
    """Raised when configuration validation fails."""
    pass


class ConfigurationParsingError(ConfigurationError):
    """Raised when configuration cannot be parsed."""
    pass