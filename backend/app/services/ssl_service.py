import subprocess
import logging
import docker
from datetime import datetime, timedelta
from typing import Optional
from app.models.domain import Domain

logger = logging.getLogger(__name__)

class SSLService:
    """Service for managing Let's Encrypt SSL certificates"""
    
    @staticmethod
    def issue_certificate(domain: Domain) -> bool:
        """Issue SSL certificate using Let's Encrypt (certbot)
        
        Uses HTTP-01 challenge for single domains
        For wildcard domains (*.example.com), use DNS-01 challenge with DNS provider API
        """
        
        try:
            # Check if domain is wildcard
            is_wildcard = domain.domain.startswith("*.")
            
            if is_wildcard:
                logger.warning(f"Wildcard domain {domain.domain} requires DNS-01 challenge")
                logger.warning("Manual setup required: Add DNS TXT record or configure DNS provider API")
                return False
            
            # Use HTTP-01 challenge for regular domains
            logger.info(f"Issuing certificate for {domain.domain}")
            
            result = subprocess.run([
                "certbot", "certonly",
                "--webroot",
                "-w", "/var/www/certbot",
                "-d", domain.domain,
                "--non-interactive",
                "--agree-tos",
                "--email", "admin@auraops.com",  # TODO: Make configurable
                "--quiet"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Certificate issued successfully for {domain.domain}")
                
                # Update domain model
                domain.ssl_enabled = True
                domain.ssl_issued_at = datetime.utcnow()
                domain.ssl_expires_at = datetime.utcnow() + timedelta(days=90)  # Let's Encrypt = 90 days
                
                return True
            else:
                logger.error(f"Certbot failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"SSL issuance failed for {domain.domain}: {e}")
            return False
    
    @staticmethod
    def renew_certificate(domain: Domain) -> bool:
        """Renew expiring SSL certificate"""
        
        try:
            logger.info(f"Renewing certificate for {domain.domain}")
            
            result = subprocess.run([
                "certbot", "renew",
                "--cert-name", domain.domain,
                "--quiet"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Certificate renewed for {domain.domain}")
                domain.ssl_expires_at = datetime.utcnow() + timedelta(days=90)
                return True
            else:
                logger.error(f"Certificate renewal failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"SSL renewal failed for {domain.domain}: {e}")
            return False
    
    @staticmethod
    def revoke_certificate(domain: Domain) -> bool:
        """Revoke SSL certificate"""
        
        try:
            result = subprocess.run([
                "certbot", "revoke",
                "--cert-name", domain.domain,
                "--non-interactive"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Certificate revoked for {domain.domain}")
                domain.ssl_enabled = False
                domain.ssl_issued_at = None
                domain.ssl_expires_at = None
                return True
            else:
                logger.error(f"Certificate revocation failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"SSL revocation failed for {domain.domain}: {e}")
            return False
    
    @staticmethod
    def setup_wildcard_ssl(base_domain: str, dns_provider: str = "cloudflare") -> dict:
        """Guide for setting up wildcard SSL certificate
        
        Wildcard SSL requires DNS-01 challenge, which needs DNS provider API access
        """
        
        instructions = {
            "domain": f"*.{base_domain}",
            "challenge_type": "DNS-01",
            "requirements": [
                f"DNS provider API credentials ({dns_provider})",
                "Certbot DNS plugin installed",
                "Automatic DNS record management"
            ],
            "command_example": f"""
# Install DNS plugin (example for Cloudflare)
pip install certbot-dns-cloudflare

# Create credentials file
echo 'dns_cloudflare_api_token = YOUR_API_TOKEN' > /etc/letsencrypt/cloudflare.ini
chmod 600 /etc/letsencrypt/cloudflare.ini

# Issue wildcard certificate
certbot certonly \\
  --dns-cloudflare \\
  --dns-cloudflare-credentials /etc/letsencrypt/cloudflare.ini \\
  -d *.{base_domain} \\
  -d {base_domain}
""",
            "supported_providers": [
                "Cloudflare",
                "Route53 (AWS)",
                "Google Cloud DNS",
                "DigitalOcean",
                "Namecheap"
            ]
        }
        
        return instructions
    
    @staticmethod
    def auto_renew_expiring_certificates(db_session):
        """Background task to auto-renew certificates expiring in 30 days"""
        
        from app.models.domain import Domain
        
        try:
            # Find domains with SSL expiring soon
            expiring_soon = db_session.query(Domain).filter(
                Domain.ssl_enabled == True,
                Domain.ssl_expires_at <= datetime.utcnow() + timedelta(days=30)
            ).all()
            
            for domain in expiring_soon:
                logger.info(f"Auto-renewing certificate for {domain.domain}")
                success = SSLService.renew_certificate(domain)
                
                if success:
                    db_session.commit()
                    
        except Exception as e:
            logger.error(f"Auto-renewal task failed: {e}")
