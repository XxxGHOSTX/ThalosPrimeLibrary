# Thalos Prime Library - Deployment Guide

This guide covers all deployment options for the Thalos Prime Library, from simple package installation to production server deployment.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Installation Methods](#installation-methods)
4. [Configuration](#configuration)
5. [Running the Library](#running-the-library)
6. [Running the API Server](#running-the-api-server)
7. [Docker Deployment](#docker-deployment)
8. [Production Deployment](#production-deployment)
9. [Troubleshooting](#troubleshooting)

---

## Quick Start

**For Python library usage:**
```bash
pip install -e .
python example_usage.py
```

**For API server:**
```bash
pip install -e .
python run_thalos.py
# Or: ./run_thalos.sh
```

**For Docker:**
```bash
docker build -t thalos-prime .
docker run -p 8000:8000 thalos-prime
```

---

## Prerequisites

### System Requirements
- **Python**: 3.7 or higher (3.11+ recommended)
- **OS**: Linux, macOS, or Windows
- **Memory**: Minimum 512MB RAM, 2GB+ recommended
- **Storage**: 100MB+ free disk space

### Required Tools
- `pip` (Python package manager)
- `git` (for source installation)
- `docker` (optional, for containerized deployment)

---

## Installation Methods

### Method 1: Install as Python Package (Development Mode)

This is the recommended method for development and testing:

```bash
# Clone the repository
git clone https://github.com/XxxGHOSTX/ThalosPrimeLibrary.git
cd ThalosPrimeLibrary

# Install in editable mode with development dependencies
pip install -e ".[dev]"

# Verify installation
python -c "import thalos_prime; print(thalos_prime.__version__)"
```

### Method 2: Install as Python Package (Production Mode)

For production use or when you don't need to modify the code:

```bash
# Clone the repository
git clone https://github.com/XxxGHOSTX/ThalosPrimeLibrary.git
cd ThalosPrimeLibrary

# Install in production mode
pip install .

# Verify installation
python -c "import thalos_prime; print(thalos_prime.__version__)"
```

### Method 3: Install from PyPI (Future)

Once published to PyPI, you will be able to install directly:

```bash
pip install thalos-prime-library
```

---

## Configuration

### Environment Variables

Thalos Prime uses environment variables for configuration:

| Variable | Description | Default |
|----------|-------------|---------|
| `THALOS_LIBRARY_PATH` | Path to local Library of Babel directory | `C:\Users\LT\Desktop\THALOSPRIMEBRAIN\ThalosPrimeLibraryOfBabel` |
| `THALOS_API_HOST` | API server host | `127.0.0.1` |
| `THALOS_API_PORT` | API server port | `8000` |
| `THALOS_LOG_LEVEL` | Logging level | `INFO` |

**Setting environment variables:**

**Linux/macOS:**
```bash
export THALOS_LIBRARY_PATH="/path/to/your/library"
export THALOS_API_PORT=8080
```

**Windows (PowerShell):**
```powershell
$env:THALOS_LIBRARY_PATH="C:\path\to\your\library"
$env:THALOS_API_PORT=8080
```

**Windows (Command Prompt):**
```cmd
set THALOS_LIBRARY_PATH=C:\path\to\your\library
set THALOS_API_PORT=8080
```

### Configuration in Code

You can also configure the library programmatically:

```python
from thalos_prime.config import setup_local_imports

# Use custom path
setup_local_imports(custom_path="/your/custom/path")
```

---

## Running the Library

### As a Python Library

Thalos Prime is primarily designed to be used as a Python library:

```python
# Import the main components
from thalos_prime import (
    BabelGenerator,
    BabelEnumerator,
    BabelDecoder,
    address_to_page,
    enumerate_addresses,
    score_coherence
)

# Generate a page from an address
page = address_to_page("abc123def456")
print(f"Generated page: {page[:100]}...")

# Enumerate addresses from a query
addresses = enumerate_addresses("hello world", max_results=5)
for addr in addresses:
    print(f"Address: {addr['address']}, Score: {addr['score']}")

# Score coherence of text
from thalos_prime.lob_decoder import BabelDecoder
decoder = BabelDecoder()
coherence = decoder.score_coherence("the quick brown fox", query="fox")
print(f"Coherence score: {coherence.overall_score}/100")
```

### Running Example Scripts

The repository includes example scripts to demonstrate functionality:

**Basic usage example:**
```bash
python example_usage.py
```

**Full integration demo:**
```bash
python integration_example.py
```

**System verification:**
```bash
python verify_system.py
```

### Running Tests

To verify your installation and ensure everything works correctly:

```bash
# Run all tests
python -m pytest tests -v

# Run specific test modules
python -m pytest tests/test_generator.py -v
python -m pytest tests/test_enumerator.py -v
python -m pytest tests/test_decoder.py -v

# Run with coverage
python -m pytest tests --cov=thalos_prime --cov-report=html
```

---

## Running the API Server

Thalos Prime includes a FastAPI-based REST API server.

### Development Server

**Using the provided script (Windows):**
```bash
python run_thalos.py
```

**Using the shell script (Linux/macOS):**
```bash
chmod +x run_thalos.sh
./run_thalos.sh
```

**Using uvicorn directly:**
```bash
# Development mode with auto-reload
uvicorn thalos_prime.api.server:app --host 127.0.0.1 --port 8000 --reload

# Production mode
uvicorn thalos_prime.api.server:app --host 0.0.0.0 --port 8000 --workers 4
```

### Accessing the API

Once the server is running, you can access:

- **API Documentation (Swagger UI)**: http://localhost:8000/docs
- **Alternative Documentation (ReDoc)**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json
- **Health Check**: http://localhost:8000/health

### API Endpoints

Key endpoints include:

- `GET /health` - Health check
- `POST /api/v1/generate` - Generate pages from addresses
- `POST /api/v1/enumerate` - Enumerate addresses from queries
- `POST /api/v1/decode` - Decode and score pages
- `POST /api/v1/search` - Search for content
- `POST /api/v1/chat` - Interactive chat interface

### Testing the API

**Using curl:**
```bash
# Health check
curl http://localhost:8000/health

# Generate a page (if endpoint exists)
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"address": "abc123"}'
```

**Using Python requests:**
```python
import requests

# Health check
response = requests.get("http://localhost:8000/health")
print(response.json())

# API request
response = requests.post(
    "http://localhost:8000/api/v1/generate",
    json={"address": "abc123"}
)
print(response.json())
```

---

## Docker Deployment

### Building the Docker Image

```bash
# Build the image
docker build -t thalos-prime:latest .

# Build with specific version tag
docker build -t thalos-prime:0.1.0 .
```

### Running with Docker

**Basic run:**
```bash
docker run -p 8000:8000 thalos-prime:latest
```

**With environment variables:**
```bash
docker run -p 8000:8000 \
  -e THALOS_LIBRARY_PATH=/app/data \
  -e THALOS_LOG_LEVEL=DEBUG \
  thalos-prime:latest
```

**With volume mount (for persistent data):**
```bash
docker run -p 8000:8000 \
  -v /path/to/local/data:/app/data \
  thalos-prime:latest
```

**Run in detached mode:**
```bash
docker run -d \
  --name thalos-prime \
  -p 8000:8000 \
  --restart unless-stopped \
  thalos-prime:latest
```

### Docker Compose (Recommended for Production)

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  thalos-prime:
    build: .
    container_name: thalos-prime
    ports:
      - "8000:8000"
    environment:
      - THALOS_LIBRARY_PATH=/app/data
      - THALOS_LOG_LEVEL=INFO
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://127.0.0.1:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

Then run:
```bash
docker-compose up -d
docker-compose logs -f  # View logs
docker-compose down     # Stop
```

---

## Production Deployment

### Using a Production WSGI/ASGI Server

For production, use a production-grade ASGI server like Gunicorn with Uvicorn workers:

**Install Gunicorn:**
```bash
pip install gunicorn
```

**Run with Gunicorn:**
```bash
gunicorn thalos_prime.api.server:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile /var/log/thalos/access.log \
  --error-logfile /var/log/thalos/error.log \
  --log-level info
```

### Systemd Service (Linux)

Create a systemd service file at `/etc/systemd/system/thalos-prime.service`:

```ini
[Unit]
Description=Thalos Prime API Server
After=network.target

[Service]
Type=notify
User=thalos
Group=thalos
WorkingDirectory=/opt/thalos-prime
Environment="PATH=/opt/thalos-prime/venv/bin"
Environment="THALOS_LIBRARY_PATH=/opt/thalos-prime/data"
ExecStart=/opt/thalos-prime/venv/bin/gunicorn \
  thalos_prime.api.server:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable thalos-prime
sudo systemctl start thalos-prime
sudo systemctl status thalos-prime
```

### Reverse Proxy with Nginx

Configure Nginx as a reverse proxy:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### SSL/TLS with Let's Encrypt

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
```

### Security Best Practices

1. **Run as non-root user**: Create dedicated user for the service
2. **Firewall**: Only expose necessary ports (80, 443)
3. **Environment variables**: Use secrets management (e.g., Vault, AWS Secrets Manager)
4. **Rate limiting**: Implement at nginx or application level
5. **Monitoring**: Set up logging and monitoring (Prometheus, Grafana)
6. **Backups**: Regular backups of data and configuration
7. **Updates**: Keep dependencies and system packages updated

### Cloud Deployment

**AWS (Elastic Beanstalk):**
```bash
eb init -p python-3.11 thalos-prime
eb create thalos-prime-env
eb deploy
```

**Heroku:**
```bash
heroku create thalos-prime
git push heroku main
```

**Google Cloud Run:**
```bash
gcloud run deploy thalos-prime \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

**Azure Container Instances:**
```bash
az container create \
  --resource-group thalos-rg \
  --name thalos-prime \
  --image thalos-prime:latest \
  --dns-name-label thalos-prime \
  --ports 8000
```

---

## Troubleshooting

### Common Issues

**1. Import errors when running scripts**

```
ImportError: No module named 'thalos_prime'
```

**Solution:**
```bash
# Install the package in editable mode
pip install -e .

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**2. Port already in use**

```
OSError: [Errno 98] Address already in use
```

**Solution:**
```bash
# Find process using the port
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Kill the process or use a different port
uvicorn thalos_prime.api.server:app --port 8001
```

**3. Permission denied on startup scripts**

```
Permission denied: ./run_thalos.sh
```

**Solution:**
```bash
chmod +x run_thalos.sh
```

**4. Library path not found**

```
WARNING: Local library path does not exist: /path/to/library
```

**Solution:**
Set the correct path via environment variable:
```bash
export THALOS_LIBRARY_PATH="/correct/path/to/library"
```

Or configure in code:
```python
from thalos_prime.config import setup_local_imports
setup_local_imports(custom_path="/correct/path")
```

**5. Tests failing**

**Solution:**
```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests with verbose output
python -m pytest tests -v -s
```

**6. Docker build fails**

**Solution:**
```bash
# Build with no cache
docker build --no-cache -t thalos-prime .

# Check logs
docker logs thalos-prime
```

### Getting Help

- **GitHub Issues**: https://github.com/XxxGHOSTX/ThalosPrimeLibrary/issues
- **Documentation**: See `ARCHITECTURE.md`, `IMPLEMENTATION_COMPLETE.md`
- **Examples**: Check `example_usage.py` and `integration_example.py`
- **Tests**: Review test files in `tests/` directory for usage patterns

---

## Additional Resources

- [README.md](README.md) - Project overview
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md) - Implementation details
- [PHASE1_PHASE2_GUIDE.md](PHASE1_PHASE2_GUIDE.md) - Phase 1 & 2 features
- [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) - System verification
- [.github/copilot-instructions.md](.github/copilot-instructions.md) - Development guidelines

---

## License

MIT License - See [LICENSE](LICENSE) file for details.

---

**Last Updated**: 2026-02-13  
**Version**: 0.1.0
