"""FastAPI server for the Enterprise Web Scraper."""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response

from scraper_factory import ScraperFactory, ScraperType
from config.config_loader import ConfigLoader
from result_processor import ResultProcessor
from metrics_monitor import MetricsCollector, PerformanceMonitor
from exceptions import ScrapingError, ConfigurationError
from utilities import LoggingUtils, ValidationUtils


# Configure logging
LoggingUtils.setup_logging(level="INFO")
logger = LoggingUtils.create_logger("api_server")

# Prometheus metrics
REQUEST_COUNT = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('api_request_duration_seconds', 'API request duration')
SCRAPING_TASKS = Counter('scraping_tasks_total', 'Total scraping tasks', ['site', 'status'])

# Global objects
metrics_collector = MetricsCollector(enable_collection=True)
performance_monitor = PerformanceMonitor(metrics_collector)
active_tasks: Dict[str, Dict[str, Any]] = {}

# Security
security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Starting Enterprise Web Scraper API")
    yield
    logger.info("Shutting down Enterprise Web Scraper API")


app = FastAPI(
    title="Enterprise Web Scraper API",
    description="RESTful API for the Enterprise Web Scraper",
    version="2.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class ScrapingRequest(BaseModel):
    """Request model for scraping operations."""
    
    site_name: str = Field(..., description="Name of the site to scrape")
    search_terms: List[str] = Field(..., description="List of search terms")
    scraper_type: str = Field(default="basic", description="Type of scraper to use")
    max_results: Optional[int] = Field(default=10, description="Maximum results per search")
    enable_processing: bool = Field(default=True, description="Enable result processing")
    config_overrides: Optional[Dict[str, Any]] = Field(default=None, description="Configuration overrides")


class ScrapingResponse(BaseModel):
    """Response model for scraping operations."""
    
    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field(..., description="Task status")
    message: str = Field(..., description="Status message")
    created_at: datetime = Field(..., description="Task creation timestamp")


class TaskStatus(BaseModel):
    """Model for task status information."""
    
    task_id: str
    status: str
    progress: Optional[float] = None
    message: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SiteInfo(BaseModel):
    """Model for site information."""
    
    site_name: str
    target_url: str
    status: str
    last_scraped: Optional[datetime] = None
    success_rate: Optional[float] = None
    average_response_time: Optional[float] = None


class PerformanceMetrics(BaseModel):
    """Model for performance metrics."""
    
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_duration: float
    success_rate: float
    alerts: List[Dict[str, Any]]


# Dependency functions
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API token (implement your authentication logic)."""
    # For demo purposes, accept any token
    # In production, implement proper JWT verification or API key validation
    if not credentials.token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return credentials.token


# Health check endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    }


@app.get("/health/detailed", tags=["Health"])
async def detailed_health_check():
    """Detailed health check with component status."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "api_server": "healthy",
            "metrics_collector": "healthy" if metrics_collector.enable_collection else "disabled",
            "active_tasks": len(active_tasks),
            "performance_monitor": "healthy"
        }
    }
    
    # Check if we can create a scraper
    try:
        factory = ScraperFactory()
        health_status["components"]["scraper_factory"] = "healthy"
    except Exception as e:
        health_status["components"]["scraper_factory"] = f"unhealthy: {e}"
        health_status["status"] = "degraded"
    
    return health_status


# Metrics endpoint
@app.get("/metrics", tags=["Monitoring"])
async def get_prometheus_metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type="text/plain")


# Site management endpoints
@app.get("/sites", response_model=List[SiteInfo], tags=["Sites"])
async def list_sites(token: str = Depends(verify_token)):
    """List available sites for scraping."""
    try:
        # This would typically come from a database
        # For now, return example sites
        sites = [
            SiteInfo(
                site_name="truckpro",
                target_url="https://www.truckpro.com/",
                status="active",
                success_rate=95.5,
                average_response_time=2.3
            )
        ]
        return sites
    except Exception as e:
        logger.error(f"Error listing sites: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/sites/{site_name}", response_model=SiteInfo, tags=["Sites"])
async def get_site_info(site_name: str, token: str = Depends(verify_token)):
    """Get information about a specific site."""
    try:
        # Get site performance from metrics
        site_stats = metrics_collector.get_stats(site_name=site_name)
        
        site_info = SiteInfo(
            site_name=site_name,
            target_url=f"https://{site_name}.com/",  # Placeholder
            status="active",
            success_rate=site_stats.success_rate if site_stats.total_operations > 0 else None,
            average_response_time=site_stats.average_duration if site_stats.total_operations > 0 else None
        )
        
        return site_info
    except Exception as e:
        logger.error(f"Error getting site info for {site_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Scraping endpoints
@app.post("/scrape", response_model=ScrapingResponse, tags=["Scraping"])
async def start_scraping(
    request: ScrapingRequest,
    background_tasks: BackgroundTasks,
    token: str = Depends(verify_token)
):
    """Start a scraping operation."""
    task_id = str(uuid.uuid4())
    
    try:
        # Validate request
        if not request.search_terms:
            raise HTTPException(status_code=400, detail="No search terms provided")
        
        # Validate scraper type
        try:
            scraper_type = ScraperType(request.scraper_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid scraper type: {request.scraper_type}")
        
        # Create task entry
        task_info = {
            "task_id": task_id,
            "status": "pending",
            "progress": 0.0,
            "message": "Task created, waiting to start",
            "created_at": datetime.now(),
            "started_at": None,
            "completed_at": None,
            "request": request.dict(),
            "results": None,
            "error": None
        }
        
        active_tasks[task_id] = task_info
        
        # Start background task
        background_tasks.add_task(
            perform_scraping_task,
            task_id,
            request
        )
        
        SCRAPING_TASKS.labels(site=request.site_name, status="started").inc()
        
        return ScrapingResponse(
            task_id=task_id,
            status="pending",
            message="Scraping task started",
            created_at=task_info["created_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting scraping task: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/scrape/{task_id}", response_model=TaskStatus, tags=["Scraping"])
async def get_task_status(task_id: str, token: str = Depends(verify_token)):
    """Get the status of a scraping task."""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_info = active_tasks[task_id]
    
    return TaskStatus(
        task_id=task_id,
        status=task_info["status"],
        progress=task_info["progress"],
        message=task_info["message"],
        created_at=task_info["created_at"],
        started_at=task_info["started_at"],
        completed_at=task_info["completed_at"],
        results=task_info["results"],
        error=task_info["error"]
    )


@app.delete("/scrape/{task_id}", tags=["Scraping"])
async def cancel_task(task_id: str, token: str = Depends(verify_token)):
    """Cancel a scraping task."""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_info = active_tasks[task_id]
    
    if task_info["status"] in ["completed", "failed", "cancelled"]:
        raise HTTPException(status_code=400, detail="Task cannot be cancelled")
    
    task_info["status"] = "cancelled"
    task_info["message"] = "Task cancelled by user"
    task_info["completed_at"] = datetime.now()
    
    return {"message": "Task cancelled successfully"}


# Task management endpoints
@app.get("/tasks", tags=["Tasks"])
async def list_tasks(
    status: Optional[str] = None,
    limit: int = 50,
    token: str = Depends(verify_token)
):
    """List scraping tasks."""
    tasks = []
    
    for task_id, task_info in active_tasks.items():
        if status and task_info["status"] != status:
            continue
        
        tasks.append({
            "task_id": task_id,
            "status": task_info["status"],
            "site_name": task_info["request"]["site_name"],
            "search_terms": task_info["request"]["search_terms"],
            "created_at": task_info["created_at"],
            "completed_at": task_info["completed_at"]
        })
    
    # Sort by creation time, most recent first
    tasks.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {"tasks": tasks[:limit], "total": len(tasks)}


# Performance and monitoring endpoints
@app.get("/performance", response_model=PerformanceMetrics, tags=["Monitoring"])
async def get_performance_metrics(
    hours: int = 24,
    token: str = Depends(verify_token)
):
    """Get performance metrics."""
    try:
        stats = metrics_collector.get_stats()
        alerts = performance_monitor.check_performance_alerts(hours=hours)
        
        return PerformanceMetrics(
            total_requests=stats.total_operations,
            successful_requests=stats.successful_operations,
            failed_requests=stats.failed_operations,
            average_duration=stats.average_duration,
            success_rate=stats.success_rate,
            alerts=alerts
        )
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/performance/report", tags=["Monitoring"])
async def get_performance_report(
    hours: int = 24,
    format: str = "json",
    token: str = Depends(verify_token)
):
    """Get detailed performance report."""
    try:
        report = performance_monitor.generate_performance_report(hours=hours)
        
        if format == "json":
            return report
        else:
            raise HTTPException(status_code=400, detail="Only JSON format supported")
            
    except Exception as e:
        logger.error(f"Error generating performance report: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Configuration endpoints
@app.get("/config/sites", tags=["Configuration"])
async def get_site_configurations(token: str = Depends(verify_token)):
    """Get available site configurations."""
    try:
        # This would typically load from configuration files
        # For now, return example configuration
        return {
            "sites": {
                "truckpro": {
                    "site_name": "TruckPro",
                    "target_url": "https://www.truckpro.com/",
                    "status": "active"
                }
            }
        }
    except Exception as e:
        logger.error(f"Error getting site configurations: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/config/validate", tags=["Configuration"])
async def validate_configuration(
    config: Dict[str, Any],
    token: str = Depends(verify_token)
):
    """Validate a configuration."""
    try:
        # Implement configuration validation logic
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Basic validation
        if "sites" not in config:
            validation_results["valid"] = False
            validation_results["errors"].append("Missing 'sites' section")
        
        return validation_results
        
    except Exception as e:
        logger.error(f"Error validating configuration: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Background task function
async def perform_scraping_task(task_id: str, request: ScrapingRequest):
    """Perform the actual scraping task in the background."""
    task_info = active_tasks[task_id]
    
    try:
        task_info["status"] = "running"
        task_info["started_at"] = datetime.now()
        task_info["message"] = "Scraping in progress"
        task_info["progress"] = 0.1
        
        # Create scraper
        factory = ScraperFactory()
        scraper_type = ScraperType(request.scraper_type)
        scraper = factory.create_scraper(scraper_type, request.site_name)
        
        task_info["progress"] = 0.3
        task_info["message"] = "Scraper created, starting scraping"
        
        # Load configuration
        config = ConfigLoader.load_config_for_site(request.site_name)
        
        # Apply overrides if provided
        if request.config_overrides:
            if request.max_results:
                config.site_config.scraping_config.max_results_per_query = request.max_results
        
        task_info["progress"] = 0.5
        task_info["message"] = f"Scraping {len(request.search_terms)} search terms"
        
        # Perform scraping
        results = scraper.scrape_with_config(
            search_terms=request.search_terms,
            site_config=config.site_config,
            debug_mode=False
        )
        
        task_info["progress"] = 0.8
        task_info["message"] = "Processing results"
        
        # Process results if enabled
        if request.enable_processing:
            processor = ResultProcessor()
            processor.create_standard_pipeline()
            results = processor.process_results(results)
        
        # Complete task
        task_info["status"] = "completed"
        task_info["progress"] = 1.0
        task_info["message"] = "Scraping completed successfully"
        task_info["completed_at"] = datetime.now()
        task_info["results"] = {
            "search_results": results,
            "summary": {
                "total_searches": len(request.search_terms),
                "total_results": sum(len(items) for items in results.values()),
                "success_rate": 100.0  # Calculate actual success rate
            }
        }
        
        SCRAPING_TASKS.labels(site=request.site_name, status="completed").inc()
        
    except Exception as e:
        task_info["status"] = "failed"
        task_info["message"] = f"Scraping failed: {str(e)}"
        task_info["completed_at"] = datetime.now()
        task_info["error"] = str(e)
        
        SCRAPING_TASKS.labels(site=request.site_name, status="failed").inc()
        logger.error(f"Scraping task {task_id} failed: {e}")


# Middleware for metrics collection
@app.middleware("http")
async def metrics_middleware(request, call_next):
    """Middleware to collect request metrics."""
    start_time = datetime.now()
    
    response = await call_next(request)
    
    duration = (datetime.now() - start_time).total_seconds()
    
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.observe(duration)
    
    return response


def create_app() -> FastAPI:
    """Factory function to create the FastAPI app."""
    return app


if __name__ == "__main__":
    import os
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "false").lower() == "true"
    
    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )