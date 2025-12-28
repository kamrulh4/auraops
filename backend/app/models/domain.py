from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base
from datetime import datetime

class Domain(Base):
    """Domain model for custom domains and SSL management"""
    __tablename__ = "domains"

    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, unique=True, index=True, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    
    # SSL Configuration
    ssl_enabled = Column(Boolean, default=False)
    ssl_provider = Column(String, default="letsencrypt")  # letsencrypt, custom
    ssl_issued_at = Column(DateTime, nullable=True)
    ssl_expires_at = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    dns_verified = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    project = relationship("Project", back_populates="domains")
    
    @property
    def ssl_valid(self):
        """Check if SSL certificate is valid"""
        if not self.ssl_enabled or not self.ssl_expires_at:
            return False
        return datetime.utcnow() < self.ssl_expires_at
    
    @property
    def needs_renewal(self):
        """Check if SSL certificate needs renewal (30 days before expiry)"""
        if not self.ssl_expires_at:
            return False
        days_until_expiry = (self.ssl_expires_at - datetime.utcnow()).days
        return days_until_expiry <= 30
