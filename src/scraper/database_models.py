"""Database models for the Enterprise Web Scraper."""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy import (
    create_engine, Column, String, Integer, Float, DateTime, Boolean, 
    Text, JSON, ForeignKey, Index, Enum as SQLEnum, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import enum

from utilities import LoggingUtils


logger = LoggingUtils.create_logger("database")

Base = declarative_base()


class TaskStatus(enum.Enum):
    """Enumeration for task statuses."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScraperTypeEnum(enum.Enum):
    """Enumeration for scraper types."""
    BASIC = "basic"
    ADVANCED = "advanced"
    MONITORED = "monitored"
    BATCH = "batch"
    TESTING = "testing"


class MetricType(enum.Enum):
    """Enumeration for metric types."""
    SEARCH = "search"
    EXTRACT = "extract"
    NAVIGATE = "navigate"
    PROCESS = "process"
    OVERALL = "overall"


class AlertSeverity(enum.Enum):
    """Enumeration for alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Site(Base):
    """Database model for scraped sites."""
    
    __tablename__ = "sites"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    target_url = Column(String(500), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    configuration = Column(JSON, nullable=True)
    
    # Rate limiting configuration
    rate_limit_requests_per_second = Column(Float, default=1.0, nullable=False)
    rate_limit_burst_allowance = Column(Integer, default=5, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_scraped_at = Column(DateTime, nullable=True)
    
    # Statistics
    total_scrapes = Column(Integer, default=0, nullable=False)
    successful_scrapes = Column(Integer, default=0, nullable=False)
    average_response_time = Column(Float, nullable=True)
    
    # Relationships
    scraping_tasks = relationship("ScrapingTask", back_populates="site", cascade="all, delete-orphan")
    site_metrics = relationship("SiteMetric", back_populates="site", cascade="all, delete-orphan")
    scraping_results = relationship("ScrapingResult", back_populates="site", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Site(name='{self.name}', display_name='{self.display_name}')>"
    
    @property
    def success_rate(self) -> Optional[float]:
        """Calculate success rate percentage."""
        if self.total_scrapes == 0:
            return None
        return (self.successful_scrapes / self.total_scrapes) * 100


class ScrapingTask(Base):
    """Database model for scraping tasks."""
    
    __tablename__ = "scraping_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    
    # Task details
    search_terms = Column(JSON, nullable=False)  # List of search terms
    scraper_type = Column(SQLEnum(ScraperTypeEnum), nullable=False, default=ScraperTypeEnum.BASIC)
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING, index=True)
    
    # Configuration
    max_results = Column(Integer, default=10, nullable=False)
    enable_processing = Column(Boolean, default=True, nullable=False)
    config_overrides = Column(JSON, nullable=True)
    
    # Execution details
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Progress and results
    progress = Column(Float, default=0.0, nullable=False)
    message = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)
    
    # Performance metrics
    duration_seconds = Column(Float, nullable=True)
    total_results_found = Column(Integer, default=0, nullable=False)
    results_processed = Column(Integer, default=0, nullable=False)
    
    # User context (optional)
    created_by = Column(String(100), nullable=True)
    
    # Relationships
    site = relationship("Site", back_populates="scraping_tasks")
    scraping_results = relationship("ScrapingResult", back_populates="task", cascade="all, delete-orphan")
    task_metrics = relationship("TaskMetric", back_populates="task", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ScrapingTask(id='{self.id}', site='{self.site.name if self.site else 'None'}', status='{self.status.value}')>"
    
    @property
    def processing_rate(self) -> Optional[float]:
        """Calculate processing rate percentage."""
        if self.total_results_found == 0:
            return None
        return (self.results_processed / self.total_results_found) * 100


class ScrapingResult(Base):
    """Database model for individual scraping results."""
    
    __tablename__ = "scraping_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("scraping_tasks.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    
    # Search context
    search_term = Column(String(200), nullable=False, index=True)
    result_index = Column(Integer, nullable=False)  # Order in search results
    
    # Product information
    title = Column(Text, nullable=True)
    part_number = Column(String(100), nullable=True, index=True)
    vendor_part_number = Column(String(100), nullable=True)
    url = Column(Text, nullable=True)
    price = Column(String(50), nullable=True)
    quantity = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    
    # Match information
    partial_match = Column(Boolean, default=False, nullable=False)
    cross_ref_match = Column(Boolean, default=False, nullable=False)
    exact_match = Column(Boolean, default=False, nullable=False)
    
    # Quality metrics
    completeness_score = Column(Float, nullable=True)
    relevance_score = Column(Float, nullable=True)
    quality_score = Column(Float, nullable=True)
    
    # Processing metadata
    raw_data = Column(JSON, nullable=True)  # Original scraped data
    processed_data = Column(JSON, nullable=True)  # After processing pipeline
    validation_issues = Column(JSON, nullable=True)  # List of validation issues
    
    # Timestamps
    scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    task = relationship("ScrapingTask", back_populates="scraping_results")
    site = relationship("Site", back_populates="scraping_results")
    
    # Constraints
    __table_args__ = (
        Index('idx_search_term_site', 'search_term', 'site_id'),
        Index('idx_part_number_site', 'part_number', 'site_id'),
        Index('idx_scraped_at_site', 'scraped_at', 'site_id'),
    )
    
    def __repr__(self):
        return f"<ScrapingResult(id='{self.id}', title='{self.title[:50] if self.title else 'None'}', search_term='{self.search_term}')>"


class SiteMetric(Base):
    """Database model for site-level performance metrics."""
    
    __tablename__ = "site_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    
    # Time period
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Performance metrics
    total_requests = Column(Integer, default=0, nullable=False)
    successful_requests = Column(Integer, default=0, nullable=False)
    failed_requests = Column(Integer, default=0, nullable=False)
    average_response_time = Column(Float, nullable=True)
    min_response_time = Column(Float, nullable=True)
    max_response_time = Column(Float, nullable=True)
    
    # Business metrics
    total_results_scraped = Column(Integer, default=0, nullable=False)
    unique_products_found = Column(Integer, default=0, nullable=False)
    average_results_per_search = Column(Float, nullable=True)
    
    # Quality metrics
    average_completeness_score = Column(Float, nullable=True)
    average_relevance_score = Column(Float, nullable=True)
    average_quality_score = Column(Float, nullable=True)
    
    # Error analysis
    error_breakdown = Column(JSON, nullable=True)  # Error types and counts
    rate_limit_hits = Column(Integer, default=0, nullable=False)
    timeout_errors = Column(Integer, default=0, nullable=False)
    
    # Relationships
    site = relationship("Site", back_populates="site_metrics")
    
    # Constraints
    __table_args__ = (
        Index('idx_site_timestamp', 'site_id', 'timestamp'),
        UniqueConstraint('site_id', 'period_start', 'period_end', name='uq_site_period'),
    )
    
    def __repr__(self):
        return f"<SiteMetric(site_id='{self.site_id}', timestamp='{self.timestamp}', success_rate='{self.success_rate:.1f}%')>"
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100


class TaskMetric(Base):
    """Database model for task-level performance metrics."""
    
    __tablename__ = "task_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("scraping_tasks.id"), nullable=False)
    
    # Metric details
    metric_type = Column(SQLEnum(MetricType), nullable=False)
    operation_name = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Performance data
    duration_seconds = Column(Float, nullable=False)
    success = Column(Boolean, nullable=False)
    results_count = Column(Integer, default=0, nullable=False)
    
    # Additional context
    search_term = Column(String(200), nullable=True)
    error_type = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)
    
    # Relationships
    task = relationship("ScrapingTask", back_populates="task_metrics")
    
    # Constraints
    __table_args__ = (
        Index('idx_task_timestamp', 'task_id', 'timestamp'),
        Index('idx_metric_type_timestamp', 'metric_type', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<TaskMetric(task_id='{self.task_id}', operation='{self.operation_name}', duration='{self.duration_seconds:.3f}s')>"


class PerformanceAlert(Base):
    """Database model for performance alerts."""
    
    __tablename__ = "performance_alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Alert details
    alert_type = Column(String(100), nullable=False, index=True)
    severity = Column(SQLEnum(AlertSeverity), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    context = Column(String(200), nullable=True)
    
    # Threshold information
    threshold_value = Column(Float, nullable=True)
    actual_value = Column(Float, nullable=True)
    
    # Time information
    triggered_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True)
    is_resolved = Column(Boolean, default=False, nullable=False, index=True)
    
    # Context
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("scraping_tasks.id"), nullable=True)
    
    # Additional data
    metadata = Column(JSON, nullable=True)
    
    # Relationships
    site = relationship("Site")
    task = relationship("ScrapingTask")
    
    # Constraints
    __table_args__ = (
        Index('idx_alert_type_triggered', 'alert_type', 'triggered_at'),
        Index('idx_severity_triggered', 'severity', 'triggered_at'),
        Index('idx_resolved_triggered', 'is_resolved', 'triggered_at'),
    )
    
    def __repr__(self):
        return f"<PerformanceAlert(type='{self.alert_type}', severity='{self.severity.value}', resolved='{self.is_resolved}')>"


class Configuration(Base):
    """Database model for storing configurations."""
    
    __tablename__ = "configurations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Configuration identity
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    environment = Column(String(50), nullable=False, default="production", index=True)
    
    # Configuration data
    config_data = Column(JSON, nullable=False)
    schema_version = Column(String(20), nullable=False, default="1.0")
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(100), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    
    # Validation
    is_valid = Column(Boolean, default=True, nullable=False)
    validation_errors = Column(JSON, nullable=True)
    last_validated_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Configuration(name='{self.name}', environment='{self.environment}', active='{self.is_active}')>"


class AuditLog(Base):
    """Database model for audit logging."""
    
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Event details
    event_type = Column(String(100), nullable=False, index=True)
    event_action = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # User context
    user_id = Column(String(100), nullable=True, index=True)
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    
    # Resource context
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(100), nullable=True)
    
    # Event data
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    additional_data = Column(JSON, nullable=True)
    
    # Status
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Constraints
    __table_args__ = (
        Index('idx_event_type_timestamp', 'event_type', 'timestamp'),
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_resource_type_id', 'resource_type', 'resource_id'),
    )
    
    def __repr__(self):
        return f"<AuditLog(event='{self.event_type}.{self.event_action}', user='{self.user_id}', timestamp='{self.timestamp}')>"


# Database management class
class DatabaseManager:
    """Database connection and session management."""
    
    def __init__(self, database_url: str):
        """Initialize database manager.
        
        Args:
            database_url: Database connection URL
        """
        self.database_url = database_url
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")
    
    def drop_tables(self):
        """Drop all database tables."""
        Base.metadata.drop_all(bind=self.engine)
        logger.info("Database tables dropped successfully")
    
    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()
    
    def close(self):
        """Close database connection."""
        self.engine.dispose()


# Database utility functions
def create_site(session: Session, name: str, display_name: str, target_url: str, **kwargs) -> Site:
    """Create a new site record.
    
    Args:
        session: Database session
        name: Site name
        display_name: Display name
        target_url: Target URL
        **kwargs: Additional site attributes
        
    Returns:
        Created Site instance
    """
    site = Site(
        name=name,
        display_name=display_name,
        target_url=target_url,
        **kwargs
    )
    session.add(site)
    session.commit()
    session.refresh(site)
    logger.info(f"Created site: {name}")
    return site


def create_scraping_task(session: Session, site_id: str, search_terms: List[str], **kwargs) -> ScrapingTask:
    """Create a new scraping task.
    
    Args:
        session: Database session
        site_id: Site UUID
        search_terms: List of search terms
        **kwargs: Additional task attributes
        
    Returns:
        Created ScrapingTask instance
    """
    task = ScrapingTask(
        site_id=site_id,
        search_terms=search_terms,
        **kwargs
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    logger.info(f"Created scraping task: {task.id}")
    return task


def update_task_status(session: Session, task_id: str, status: TaskStatus, **kwargs) -> ScrapingTask:
    """Update task status and related fields.
    
    Args:
        session: Database session
        task_id: Task UUID
        status: New status
        **kwargs: Additional fields to update
        
    Returns:
        Updated ScrapingTask instance
    """
    task = session.query(ScrapingTask).filter(ScrapingTask.id == task_id).first()
    if not task:
        raise ValueError(f"Task not found: {task_id}")
    
    task.status = status
    if status == TaskStatus.RUNNING and not task.started_at:
        task.started_at = datetime.utcnow()
    elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
        task.completed_at = datetime.utcnow()
        if task.started_at:
            task.duration_seconds = (task.completed_at - task.started_at).total_seconds()
    
    # Update additional fields
    for key, value in kwargs.items():
        if hasattr(task, key):
            setattr(task, key, value)
    
    session.commit()
    session.refresh(task)
    return task


def store_scraping_results(session: Session, task_id: str, site_id: str, results: Dict[str, List[Dict[str, Any]]]) -> List[ScrapingResult]:
    """Store scraping results in the database.
    
    Args:
        session: Database session
        task_id: Task UUID
        site_id: Site UUID
        results: Dictionary of search results
        
    Returns:
        List of created ScrapingResult instances
    """
    result_objects = []
    
    for search_term, items in results.items():
        for index, item in enumerate(items):
            result = ScrapingResult(
                task_id=task_id,
                site_id=site_id,
                search_term=search_term,
                result_index=index,
                title=item.get('title'),
                part_number=item.get('part_number'),
                vendor_part_number=item.get('vendor_part_number'),
                url=item.get('url'),
                price=item.get('price'),
                quantity=item.get('quantity'),
                description=item.get('description'),
                partial_match=item.get('partial_match', False),
                cross_ref_match=item.get('cross_ref_match', False),
                exact_match=item.get('exact_match', False),
                completeness_score=item.get('_scores', {}).get('completeness_score'),
                relevance_score=item.get('_scores', {}).get('relevance_score'),
                quality_score=item.get('_scores', {}).get('quality_score'),
                raw_data=item,
                validation_issues=item.get('_validation', {}).get('issues')
            )
            session.add(result)
            result_objects.append(result)
    
    session.commit()
    logger.info(f"Stored {len(result_objects)} scraping results for task {task_id}")
    return result_objects


def create_performance_alert(session: Session, alert_type: str, severity: AlertSeverity, 
                           title: str, message: str, **kwargs) -> PerformanceAlert:
    """Create a performance alert.
    
    Args:
        session: Database session
        alert_type: Type of alert
        severity: Alert severity
        title: Alert title
        message: Alert message
        **kwargs: Additional alert attributes
        
    Returns:
        Created PerformanceAlert instance
    """
    alert = PerformanceAlert(
        alert_type=alert_type,
        severity=severity,
        title=title,
        message=message,
        **kwargs
    )
    session.add(alert)
    session.commit()
    session.refresh(alert)
    logger.info(f"Created performance alert: {alert_type} ({severity.value})")
    return alert


def log_audit_event(session: Session, event_type: str, event_action: str, 
                   success: bool = True, **kwargs) -> AuditLog:
    """Log an audit event.
    
    Args:
        session: Database session
        event_type: Type of event
        event_action: Action performed
        success: Whether the action was successful
        **kwargs: Additional audit data
        
    Returns:
        Created AuditLog instance
    """
    audit_log = AuditLog(
        event_type=event_type,
        event_action=event_action,
        success=success,
        **kwargs
    )
    session.add(audit_log)
    session.commit()
    logger.debug(f"Logged audit event: {event_type}.{event_action}")
    return audit_log


# Example usage and initialization
def initialize_database(database_url: str, create_sample_data: bool = False) -> DatabaseManager:
    """Initialize the database with tables and optional sample data.
    
    Args:
        database_url: Database connection URL
        create_sample_data: Whether to create sample data
        
    Returns:
        DatabaseManager instance
    """
    db_manager = DatabaseManager(database_url)
    db_manager.create_tables()
    
    if create_sample_data:
        with db_manager.get_session() as session:
            # Create sample site
            site = create_site(
                session=session,
                name="truckpro",
                display_name="TruckPro",
                target_url="https://www.truckpro.com/",
                rate_limit_requests_per_second=1.0,
                rate_limit_burst_allowance=5
            )
            
            # Create sample configuration
            config = Configuration(
                name="default_truckpro",
                description="Default configuration for TruckPro",
                environment="production",
                config_data={
                    "scraping": {
                        "max_results_per_query": 10,
                        "wait_timeout": 10
                    }
                },
                is_default=True
            )
            session.add(config)
            session.commit()
            
            logger.info("Sample data created successfully")
    
    return db_manager


if __name__ == "__main__":
    # Example usage
    DATABASE_URL = "postgresql://scraper:password@localhost:5432/scraper_db"
    
    try:
        db_manager = initialize_database(DATABASE_URL, create_sample_data=True)
        
        with db_manager.get_session() as session:
            # Query examples
            sites = session.query(Site).all()
            print(f"Found {len(sites)} sites")
            
            for site in sites:
                print(f"Site: {site.name} - {site.display_name}")
                print(f"  Success rate: {site.success_rate or 0:.1f}%")
                print(f"  Total scrapes: {site.total_scrapes}")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    finally:
        if 'db_manager' in locals():
            db_manager.close()