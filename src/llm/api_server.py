"""
REST API Server for LLM Search Result Evaluation System.

Provides HTTP endpoints for evaluation services, health checks, metrics,
and system management.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import asdict
import traceback
import os

# FastAPI imports
try:
    from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request, Response
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.gzip import GZipMiddleware
    from fastapi.responses import JSONResponse, PlainTextResponse
    from pydantic import BaseModel, Field, ConfigDict
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    # Fallback to basic HTTP server
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import urllib.parse

from config import LLMConfig
from evaluation_engine import SearchEvaluationEngine, EvaluationRequest, EvaluationResult
from search_classifier import SearchType
from metrics import get_metrics_manager, get_system_health, MetricsContext
from cache import get_evaluation_cache, get_cache_manager, cache_enabled
from logging_config import get_logger, LoggerMixin
from exceptions import LLMEvaluatorError, ServiceUnavailableError, ValidationError


# Pydantic models for API
if FASTAPI_AVAILABLE:
    class EvaluationRequestModel(BaseModel):
        """API model for evaluation requests."""
        model_config = ConfigDict(use_enum_values=True)
        
        query: str = Field(..., description="Search query to evaluate", min_length=1, max_length=500)
        results: List[Dict[str, Any]] = Field(..., description="Search results to evaluate", min_items=1, max_items=100)
        search_type: Optional[str] = Field(None, description="Force specific search type")
        model: Optional[str] = Field(None, description="LLM model to use")
        include_executive_summary: bool = Field(True, description="Include executive summary")
        apply_inventory_ranking: bool = Field(True, description="Apply inventory-aware ranking")
        cache_ttl: Optional[int] = Field(None, description="Cache TTL in seconds")
    
    class EvaluationResponseModel(BaseModel):
        """API model for evaluation responses."""
        query: str
        search_type: str
        model_used: str
        evaluations: List[Dict[str, Any]]
        ranking_summary: str
        inventory_summary: Dict[str, Any]
        executive_summary: Optional[Dict[str, Any]] = None
        status: str
        error: Optional[str] = None
        cached: bool = False
        processing_time_ms: float
        timestamp: str
    
    class HealthResponseModel(BaseModel):
        """API model for health responses."""
        status: str
        timestamp: str
        version: str
        uptime_seconds: float
        metrics: Dict[str, Any]
        cache_stats: Optional[Dict[str, Any]] = None
    
    class MetricsResponseModel(BaseModel):
        """API model for metrics responses."""
        performance_stats: Dict[str, Any]
        counters: Dict[str, int]
        gauges: Dict[str, float]
        cache_stats: Dict[str, Any]
        system_health: Dict[str, Any]


class APIServer(LoggerMixin):
    """Main API server class."""
    
    def __init__(self, config: LLMConfig = None):
        self.config = config or LLMConfig.from_environment()
        self.engine = SearchEvaluationEngine(self.config)
        self.start_time = time.time()
        
        # Initialize FastAPI app if available
        if FASTAPI_AVAILABLE:
            self.app = self._create_fastapi_app()
        else:
            self.app = None
            self.logger.warning("FastAPI not available, using basic HTTP server")
    
    def _create_fastapi_app(self) -> FastAPI:
        """Create and configure FastAPI application."""
        from llm import __version__
        
        app = FastAPI(
            title="LLM Search Result Evaluation API",
            description="Advanced LLM-based search result evaluation with inventory awareness",
            version=__version__,
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # Add middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        app.add_middleware(GZipMiddleware, minimum_size=1000)
        
        # Add custom middleware
        @app.middleware("http")
        async def add_process_time_header(request: Request, call_next):
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            return response
        
        @app.middleware("http")
        async def log_requests(request: Request, call_next):
            self.logger.info(f"{request.method} {request.url}")
            response = await call_next(request)
            self.logger.info(f"Response: {response.status_code}")
            return response
        
        # Exception handlers
        @app.exception_handler(LLMEvaluatorError)
        async def llm_evaluator_exception_handler(request: Request, exc: LLMEvaluatorError):
            self.logger.error(f"LLM Evaluator error: {exc}")
            return JSONResponse(
                status_code=400,
                content={
                    "error": exc.message,
                    "details": exc.details,
                    "type": type(exc).__name__
                }
            )
        
        @app.exception_handler(ValidationError)
        async def validation_exception_handler(request: Request, exc: ValidationError):
            return JSONResponse(
                status_code=422,
                content={
                    "error": "Validation failed",
                    "details": exc.details,
                    "type": "ValidationError"
                }
            )
        
        @app.exception_handler(ServiceUnavailableError)
        async def service_unavailable_handler(request: Request, exc: ServiceUnavailableError):
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Service unavailable",
                    "details": exc.details,
                    "type": "ServiceUnavailableError"
                }
            )
        
        # Routes
        self._add_routes(app)
        
        return app
    
    def _add_routes(self, app: FastAPI) -> None:
        """Add API routes to FastAPI app."""
        
        @app.get("/", response_class=PlainTextResponse)
        async def root():
            """Root endpoint."""
            return "LLM Search Result Evaluation API - See /docs for documentation"
        
        @app.post("/evaluate", response_model=EvaluationResponseModel)
        async def evaluate_results(
            request: EvaluationRequestModel,
            background_tasks: BackgroundTasks
        ):
            """Evaluate search results."""
            start_time = time.time()
            cached = False
            
            try:
                # Check cache if enabled
                evaluation_result = None
                if cache_enabled():
                    cache = get_evaluation_cache()
                    search_type = request.search_type or "auto"
                    model = request.model or self.config.default_model
                    
                    evaluation_result = cache.get_evaluation(
                        request.query, request.results, search_type, model
                    )
                    if evaluation_result:
                        cached = True
                
                # Perform evaluation if not cached
                if evaluation_result is None:
                    # Convert to internal request format
                    eval_request = EvaluationRequest(
                        query=request.query,
                        results=request.results,
                        search_type=SearchType(request.search_type) if request.search_type else None,
                        model=request.model,
                        include_executive_summary=request.include_executive_summary,
                        apply_inventory_ranking=request.apply_inventory_ranking
                    )
                    
                    # Perform evaluation with metrics tracking
                    with MetricsContext("api_evaluation"):
                        evaluation_result = self.engine.evaluate(eval_request)
                    
                    # Cache result if enabled
                    if cache_enabled() and evaluation_result.status == "success":
                        cache = get_evaluation_cache()
                        result_dict = asdict(evaluation_result)
                        cache.cache_evaluation(
                            request.query, request.results,
                            evaluation_result.search_type.value,
                            evaluation_result.model_used,
                            result_dict
                        )
                
                # Record metrics in background
                processing_time = (time.time() - start_time) * 1000
                background_tasks.add_task(
                    self._record_api_metrics,
                    request.query,
                    len(request.results),
                    processing_time,
                    evaluation_result.status == "success",
                    cached
                )
                
                # Convert result to response model
                if isinstance(evaluation_result, dict):
                    # Cached result
                    response_data = evaluation_result.copy()
                    response_data.update({
                        "cached": cached,
                        "processing_time_ms": processing_time,
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    # Fresh result
                    response_data = {
                        "query": evaluation_result.query,
                        "search_type": evaluation_result.search_type.value,
                        "model_used": evaluation_result.model_used,
                        "evaluations": evaluation_result.evaluations,
                        "ranking_summary": evaluation_result.ranking_summary,
                        "inventory_summary": evaluation_result.inventory_summary,
                        "executive_summary": evaluation_result.executive_summary,
                        "status": evaluation_result.status,
                        "error": evaluation_result.error,
                        "cached": cached,
                        "processing_time_ms": processing_time,
                        "timestamp": datetime.now().isoformat()
                    }
                
                return EvaluationResponseModel(**response_data)
                
            except Exception as e:
                self.logger.error(f"Evaluation error: {e}")
                self.logger.error(traceback.format_exc())
                
                processing_time = (time.time() - start_time) * 1000
                background_tasks.add_task(
                    self._record_api_metrics,
                    request.query,
                    len(request.results),
                    processing_time,
                    False,
                    False
                )
                
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/health", response_model=HealthResponseModel)
        async def health_check():
            """Health check endpoint."""
            try:
                from llm import __version__
                
                # Get system health
                health_data = get_system_health()
                
                # Get cache stats if available
                cache_stats = None
                if cache_enabled():
                    cache_manager = get_cache_manager()
                    cache_stats = cache_manager.get_stats()
                
                uptime = time.time() - self.start_time
                
                return HealthResponseModel(
                    status=health_data["status"],
                    timestamp=datetime.now().isoformat(),
                    version=__version__,
                    uptime_seconds=uptime,
                    metrics=health_data["metrics"],
                    cache_stats=cache_stats
                )
                
            except Exception as e:
                self.logger.error(f"Health check error: {e}")
                raise HTTPException(status_code=500, detail="Health check failed")
        
        @app.get("/metrics", response_model=MetricsResponseModel)
        async def get_metrics():
            """Get system metrics."""
            try:
                metrics_manager = get_metrics_manager()
                
                return MetricsResponseModel(
                    performance_stats=metrics_manager.get_performance_stats(),
                    counters=metrics_manager.get_counter_values(),
                    gauges=metrics_manager.get_gauge_values(),
                    cache_stats=get_cache_manager().get_stats() if cache_enabled() else {},
                    system_health=get_system_health()
                )
                
            except Exception as e:
                self.logger.error(f"Metrics error: {e}")
                raise HTTPException(status_code=500, detail="Failed to get metrics")
        
        @app.get("/metrics/prometheus", response_class=PlainTextResponse)
        async def prometheus_metrics():
            """Prometheus-compatible metrics endpoint."""
            try:
                # This would integrate with prometheus_client if available
                metrics_manager = get_metrics_manager()
                
                # Simple text format for now
                lines = []
                
                # Performance stats
                perf_stats = metrics_manager.get_performance_stats()
                for operation, stats in perf_stats.items():
                    lines.append(f'# HELP {operation}_duration_seconds Operation duration')
                    lines.append(f'# TYPE {operation}_duration_seconds histogram')
                    lines.append(f'{operation}_duration_seconds {{}} {stats.avg_duration}')
                    
                    lines.append(f'# HELP {operation}_total Total operations')
                    lines.append(f'# TYPE {operation}_total counter')
                    lines.append(f'{operation}_total {{}} {stats.count}')
                
                # Counters
                counters = metrics_manager.get_counter_values()
                for name, value in counters.items():
                    lines.append(f'# HELP {name} Counter metric')
                    lines.append(f'# TYPE {name} counter')
                    lines.append(f'{name} {value}')
                
                # Gauges
                gauges = metrics_manager.get_gauge_values()
                for name, value in gauges.items():
                    lines.append(f'# HELP {name} Gauge metric')
                    lines.append(f'# TYPE {name} gauge')
                    lines.append(f'{name} {value}')
                
                return '\n'.join(lines)
                
            except Exception as e:
                self.logger.error(f"Prometheus metrics error: {e}")
                raise HTTPException(status_code=500, detail="Failed to generate metrics")
        
        @app.post("/cache/clear")
        async def clear_cache():
            """Clear the cache."""
            try:
                if not cache_enabled():
                    raise HTTPException(status_code=400, detail="Cache is disabled")
                
                cache_manager = get_cache_manager()
                cache_manager.clear()
                
                return {"message": "Cache cleared successfully"}
                
            except Exception as e:
                self.logger.error(f"Cache clear error: {e}")
                raise HTTPException(status_code=500, detail="Failed to clear cache")
        
        @app.get("/cache/stats")
        async def cache_stats():
            """Get cache statistics."""
            try:
                if not cache_enabled():
                    return {"message": "Cache is disabled", "stats": {}}
                
                cache_manager = get_cache_manager()
                return {"stats": cache_manager.get_stats()}
                
            except Exception as e:
                self.logger.error(f"Cache stats error: {e}")
                raise HTTPException(status_code=500, detail="Failed to get cache stats")
        
        @app.get("/status")
        async def service_status():
            """Get detailed service status."""
            try:
                # Check LLM service availability
                llm_available = self.engine.is_service_available()
                
                # Get available models
                models = []
                try:
                    models = self.engine.get_available_models()
                except:
                    pass
                
                return {
                    "llm_service": {
                        "available": llm_available,
                        "endpoint": self.config.ollama_api_endpoint,
                        "models": models,
                        "default_model": self.config.default_model
                    },
                    "cache": {
                        "enabled": cache_enabled(),
                        "stats": get_cache_manager().get_stats() if cache_enabled() else None
                    },
                    "configuration": {
                        "timeout": self.config.timeout,
                        "max_retries": self.config.max_retries,
                        "debug_dir": self.config.debug_dir
                    }
                }
                
            except Exception as e:
                self.logger.error(f"Status check error: {e}")
                raise HTTPException(status_code=500, detail="Failed to get status")
    
    def _record_api_metrics(self, query: str, results_count: int, processing_time_ms: float,
                           success: bool, cached: bool) -> None:
        """Record API metrics in background."""
        try:
            from metrics import record_evaluation_metrics
            
            # Record evaluation metrics
            record_evaluation_metrics(
                query=query,
                results_count=results_count,
                duration=processing_time_ms / 1000,  # Convert to seconds
                success=success,
                model=self.config.default_model,
                search_type="api"
            )
            
            # Record API-specific metrics
            metrics_manager = get_metrics_manager()
            
            tags = {
                "cached": str(cached),
                "success": str(success)
            }
            
            metrics_manager.record_counter("api_requests_total", 1, tags)
            metrics_manager.record_histogram("api_response_time_ms", processing_time_ms, tags)
            metrics_manager.record_gauge("api_results_count", results_count, tags)
            
        except Exception as e:
            self.logger.error(f"Failed to record API metrics: {e}")
    
    def run(self, host: str = "0.0.0.0", port: int = 8000, 
           log_level: str = "info", reload: bool = False) -> None:
        """Run the API server."""
        if not FASTAPI_AVAILABLE:
            self.logger.error("FastAPI is not available. Please install with: pip install fastapi uvicorn")
            return
        
        self.logger.info(f"Starting API server on {host}:{port}")
        
        # Configure uvicorn
        config = uvicorn.Config(
            app=self.app,
            host=host,
            port=port,
            log_level=log_level,
            reload=reload,
            access_log=True
        )
        
        server = uvicorn.Server(config)
        
        try:
            server.run()
        except KeyboardInterrupt:
            self.logger.info("API server stopped by user")
        except Exception as e:
            self.logger.error(f"API server error: {e}")


# Simple HTTP server fallback
class SimpleAPIHandler(BaseHTTPRequestHandler, LoggerMixin):
    """Simple HTTP handler for basic API functionality."""
    
    def __init__(self, *args, engine: SearchEvaluationEngine = None, **kwargs):
        self.engine = engine
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/health':
            self._handle_health()
        elif self.path == '/metrics':
            self._handle_metrics()
        elif self.path == '/status':
            self._handle_status()
        else:
            self._send_response(404, {"error": "Not found"})
    
    def do_POST(self):
        """Handle POST requests."""
        if self.path == '/evaluate':
            self._handle_evaluate()
        else:
            self._send_response(404, {"error": "Not found"})
    
    def _handle_health(self):
        """Handle health check."""
        try:
            health_data = get_system_health()
            self._send_response(200, health_data)
        except Exception as e:
            self._send_response(500, {"error": str(e)})
    
    def _handle_metrics(self):
        """Handle metrics request."""
        try:
            metrics_manager = get_metrics_manager()
            metrics_data = {
                "performance_stats": metrics_manager.get_performance_stats(),
                "counters": metrics_manager.get_counter_values(),
                "gauges": metrics_manager.get_gauge_values()
            }
            self._send_response(200, metrics_data)
        except Exception as e:
            self._send_response(500, {"error": str(e)})
    
    def _handle_status(self):
        """Handle status request."""
        try:
            status_data = {
                "llm_service": {
                    "available": self.engine.is_service_available() if self.engine else False
                },
                "timestamp": datetime.now().isoformat()
            }
            self._send_response(200, status_data)
        except Exception as e:
            self._send_response(500, {"error": str(e)})
    
    def _handle_evaluate(self):
        """Handle evaluation request."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            request_data = json.loads(post_data.decode('utf-8'))
            
            # Basic validation
            if 'query' not in request_data or 'results' not in request_data:
                self._send_response(400, {"error": "Missing required fields: query, results"})
                return
            
            # Create evaluation request
            eval_request = EvaluationRequest(
                query=request_data['query'],
                results=request_data['results'],
                search_type=SearchType(request_data.get('search_type')) if request_data.get('search_type') else None,
                model=request_data.get('model'),
                include_executive_summary=request_data.get('include_executive_summary', True),
                apply_inventory_ranking=request_data.get('apply_inventory_ranking', True)
            )
            
            # Perform evaluation
            start_time = time.time()
            result = self.engine.evaluate(eval_request)
            processing_time = (time.time() - start_time) * 1000
            
            # Convert to response
            response_data = {
                "query": result.query,
                "search_type": result.search_type.value,
                "model_used": result.model_used,
                "evaluations": result.evaluations,
                "ranking_summary": result.ranking_summary,
                "inventory_summary": result.inventory_summary,
                "executive_summary": result.executive_summary,
                "status": result.status,
                "error": result.error,
                "processing_time_ms": processing_time,
                "timestamp": datetime.now().isoformat()
            }
            
            self._send_response(200, response_data)
            
        except Exception as e:
            self._send_response(500, {"error": str(e)})
    
    def _send_response(self, status_code: int, data: Dict[str, Any]):
        """Send JSON response."""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response_json = json.dumps(data, indent=2, default=str)
        self.wfile.write(response_json.encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override to use our logger."""
        self.logger.info(format % args)


def create_api_server(config: LLMConfig = None) -> APIServer:
    """Create API server instance."""
    return APIServer(config)


def run_api_server(host: str = "0.0.0.0", port: int = 8000, 
                  config: LLMConfig = None, **kwargs) -> None:
    """Run API server with given configuration."""
    server = create_api_server(config)
    server.run(host, port, **kwargs)


# CLI command for running the server
def api_server_command():
    """Command-line entry point for API server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="LLM Evaluation API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--log-level", default="info", help="Log level")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--config-file", help="Configuration file path")
    
    args = parser.parse_args()
    
    # Load configuration
    if args.config_file:
        # Load from file (implementation depends on file format)
        config = LLMConfig.from_environment()
    else:
        config = LLMConfig.from_environment()
    
    # Run server
    run_api_server(
        host=args.host,
        port=args.port,
        config=config,
        log_level=args.log_level,
        reload=args.reload
    )


if __name__ == "__main__":
    api_server_command()
