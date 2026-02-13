# Thalos Prime - Quick Deployment Reference

## 🚀 Installation

```bash
# Development (editable)
pip install -e ".[dev]"

# Production
pip install .

# With automated script
./deploy.sh
```

## 🔧 Configuration

```bash
# Set library path
export THALOS_LIBRARY_PATH="/path/to/library"

# Set API port
export THALOS_API_PORT=8000
```

## 📦 Run as Library

```python
from thalos_prime import (
    address_to_page,
    enumerate_addresses,
    score_coherence
)

# Generate page
page = address_to_page("abc123")

# Enumerate addresses
addresses = enumerate_addresses("query", max_results=5)

# Score coherence
coherence = score_coherence("text", query="query")
```

## 🌐 Run API Server

```bash
# Development
python run_thalos.py
./run_thalos.sh

# Direct with uvicorn
uvicorn thalos_prime.api.server:app --reload

# Production
gunicorn thalos_prime.api.server:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

**API Docs:** http://localhost:8000/docs

## 🐳 Docker

```bash
# Build
docker build -t thalos-prime .

# Run
docker run -p 8000:8000 thalos-prime

# With Docker Compose (recommended)
docker-compose up -d
docker-compose logs -f
docker-compose down
```

## 🧪 Testing

```bash
# All tests
python -m pytest tests -v

# Specific module
python -m pytest tests/test_generator.py -v

# With coverage
python -m pytest tests --cov=thalos_prime
```

## 📊 Examples

```bash
# Basic usage
python example_usage.py

# Full integration
python integration_example.py

# System verification
python verify_system.py
```

## 🔍 Troubleshooting

**Import error:**
```bash
pip install -e .
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Port in use:**
```bash
# Find process
lsof -i :8000
# Use different port
uvicorn thalos_prime.api.server:app --port 8001
```

**Library path not found:**
```bash
export THALOS_LIBRARY_PATH="/correct/path"
```

## 📚 Key Files

- `DEPLOYMENT.md` - Full deployment guide
- `README.md` - Project overview
- `ARCHITECTURE.md` - System design
- `deploy.sh` - Automated deployment
- `docker-compose.yml` - Docker config

## 🔐 Production Checklist

- [ ] Use production ASGI server (Gunicorn/Uvicorn)
- [ ] Set up reverse proxy (Nginx)
- [ ] Configure SSL/TLS certificates
- [ ] Enable firewall (ports 80, 443)
- [ ] Set up monitoring and logging
- [ ] Configure environment variables
- [ ] Set up regular backups
- [ ] Run as non-root user
- [ ] Enable health checks
- [ ] Configure rate limiting

## 🌍 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `THALOS_LIBRARY_PATH` | Library directory | (system default) |
| `THALOS_API_HOST` | API host | `127.0.0.1` |
| `THALOS_API_PORT` | API port | `8000` |
| `THALOS_LOG_LEVEL` | Log level | `INFO` |

## 📞 Support

- Issues: https://github.com/XxxGHOSTX/ThalosPrimeLibrary/issues
- Docs: See `DEPLOYMENT.md` for detailed instructions

---

**Version:** 0.1.0 | **License:** MIT
