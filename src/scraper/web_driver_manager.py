"""Web driver management module."""

import logging
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from config.config_models import ChromeConfig


logger = logging.getLogger(__name__)


class WebDriverManager:
    """Manages Selenium WebDriver setup and configuration."""
    
    def __init__(self, chrome_config: ChromeConfig):
        """Initialize with Chrome configuration.
        
        Args:
            chrome_config: Chrome browser configuration
        """
        self.chrome_config = chrome_config
        self._driver: Optional[webdriver.Chrome] = None
    
    def create_driver(self) -> Optional[webdriver.Chrome]:
        """Create and configure a Chrome WebDriver instance.
        
        Returns:
            Configured Chrome WebDriver instance or None if creation fails
        """
        try:
            options = self._create_chrome_options()
            service = self._create_service()
            
            self._driver = webdriver.Chrome(service=service, options=options)
            self._configure_driver()
            
            logger.info("WebDriver setup successful")
            return self._driver
            
        except Exception as e:
            logger.error(f"Error setting up WebDriver: {e}")
            return None
    
    def quit_driver(self) -> None:
        """Safely quit the WebDriver."""
        if self._driver:
            try:
                self._driver.quit()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")
            finally:
                self._driver = None
    
    def _create_chrome_options(self) -> Options:
        """Create Chrome options with optimized settings.
        
        Returns:
            Configured Chrome options
        """
        options = Options()
        
        # Basic configuration
        if self.chrome_config.headless:
            options.add_argument("--headless=new")
        
        # Security and stability arguments
        security_args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-gpu-sandbox",
            "--disable-software-rasterizer",
            "--disable-3d-apis",
            "--ignore-certificate-errors",
            "--ignore-ssl-errors",
            "--allow-running-insecure-content",
            "--ignore-certificate-errors-spki-list",
            "--ignore-urlfetcher-cert-requests",
            "--disable-web-security",
        ]
        
        # Performance optimization arguments
        performance_args = [
            "--disable-extensions",
            "--disable-plugins", 
            "--disable-images",
            "--disable-setuid-sandbox",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-default-apps",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-features=TranslateUI",
            "--disable-features=VizDisplayCompositor",
            "--disable-features=VizServiceDisplayCompositor",
            "--disable-features=NetworkService",
            "--use-gl=disabled",
            "--disable-gl-drawing-for-tests",
            "--no-proxy-server",
            "--memory-pressure-off",
            "--max_old_space_size=4096",
        ]
        
        for arg in security_args + performance_args:
            options.add_argument(arg)
        
        # User agent
        options.add_argument(f"user-agent={self.chrome_config.user_agent}")
        
        # Experimental options
        options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Preferences
        prefs = {
            'profile.default_content_setting_values.notifications': 2,
            'profile.default_content_settings.popups': 0,
            'profile.managed_default_content_settings.images': 2
        }
        options.add_experimental_option('prefs', prefs)
        
        return options
    
    def _create_service(self) -> Service:
        """Create Chrome service.
        
        Returns:
            Chrome service instance
            
        Raises:
            ImportError: If webdriver-manager is needed but not installed
        """
        if self.chrome_config.chrome_driver_path is None:
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                logger.info("Using webdriver-manager to install Chrome driver")
            except ImportError:
                raise ImportError(
                    "webdriver-manager not installed. Please install it "
                    "(`pip install webdriver-manager`) or specify chrome_driver_path in config."
                )
        else:
            service = Service(self.chrome_config.chrome_driver_path)
        
        # Reduce logging noise
        service.creation_flags = 0x08000000  # CREATE_NO_WINDOW flag for Windows
        return service
    
    def _configure_driver(self) -> None:
        """Configure the driver after creation."""
        if not self._driver:
            return
            
        window_size = self.chrome_config.window_size
        self._driver.set_window_size(window_size["width"], window_size["height"])
        self._driver.implicitly_wait(self.chrome_config.implicit_wait)
    
    def __enter__(self):
        """Context manager entry."""
        return self.create_driver()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.quit_driver()