# Thalos Prime Library of Babel

A fully integrated, deterministic conversational system with TF-IDF retrieval, control-plane lifecycle management, and observable state.

## Features

- **Deterministic Seeded Generation**: Reproducible responses using session ID, user input, salt, and time buckets
- **TF-IDF Retrieval**: Local corpus indexing with deterministic top-k document retrieval
- **Control Plane Lifecycle**: Complete lifecycle management (initialize/validate/operate/reconcile/checkpoint/terminate)
- **Observability**: Structured logging and JSONL event log
- **State Persistence**: SQLite-based session and seed storage
- **FastAPI HTTP API**: RESTful endpoints with `/api/chat` for conversations
- **Static Web UI**: Interactive chat interface with real-time updates
- **Security**: Optional API key authentication
- **Docker Support**: Containerized deployment with docker-compose
- **CI/CD**: GitHub Actions workflow with linting, type checking, and testing

## Requirements

- Python 3.12+
- pip (Python package manager)
- Make (optional, for convenience commands)

## Quick Start

### 1. Installation

Clone the repository and install dependencies:

```bash
# Clone repository
git clone https://github.com/XxxGHOSTX/ThalosPrimeLibrary.git
cd ThalosPrimeLibrary

# Install dependencies
pip install -r requirements.txt

# Install in development mode (optional)
pip install -e ".[dev]"
```

### 2. Build the Index

Build the TF-IDF index from the corpus:

```bash
python scripts/build_index.py
```

This will:
- Read all `.txt` files from the `corpus/` directory
- Create a TF-IDF index at `data/tfidf_index.pkl`
- Generate a manifest at `data/manifest.json`

### 3. Start the Server

Run the Thalos Prime server:

```bash
python scripts/serve.py
```

Or use Make:

```bash
make serve
```

The server will start on http://localhost:8000

### 4. Access the UI

Open your browser and navigate to:

```
http://localhost:8000
```

You'll see the Thalos Prime chat interface. Start a conversation!

## Configuration

Create a `.env` file in the project root (use `.env.example` as a template):

## Overview
ThalosPrime Library provides a Python package structure that allows importing from your local ThalosPrimeLibraryOfBabel directory. It includes deterministic page generation, query enumeration, and enhanced coherence scoring for the Library of Babel.

## Quick Start

### Installation

**For Development:**
```bash
pip install -e ".[dev]"
```

**For Production:**
```bash
cp .env.example .env
```

Key configuration options:
### Running Examples
```bash
# Basic usage
python example_usage.py

# Full integration demo
python integration_example.py

# Run the API server
python run_thalos.py
```

## Deployment

For comprehensive deployment instructions including Docker, production setup, and cloud deployment options, see:

📖 **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide

Quick deployment options:
- **Python package**: `pip install -e .`
- **API server**: `python run_thalos.py` or `./run_thalos.sh`
- **Docker**: `docker build -t thalos-prime . && docker run -p 8000:8000 thalos-prime`

## Usage

```env
# API Settings
API_KEY=your_secret_key
ENABLE_API_KEY_AUTH=false

# Seed Policy
SEED_SALT=thalos_prime_default_salt
TIME_BUCKET_SECONDS=3600

# Generation Parameters
MAX_SENTENCES=5
TOP_K_RETRIEVAL=3
```

## API Endpoints

### Chat Endpoint

**POST** `/api/chat`

Request:
```json
{
  "session_id": "optional-session-id",
  "message": "Your question here",
  "timestamp": 1234567890.0
}
```

Response:
```json
{
  "session_id": "abc-123",
  "response": "Generated response with source citation",
  "seed": 1234567890,
  "retrieved_docs": 3
}
```

### Status Endpoint

**GET** `/api/status`

Returns system status and control plane state.

### Checkpoint Endpoint

**POST** `/api/checkpoint`

Creates a system checkpoint with validation hashes and configuration.

### Reconcile Endpoint

**POST** `/api/reconcile`

Triggers system reconciliation (re-validation).

## Docker Deployment

### Build and Run

```bash
# Build the image
docker build -t thalos-prime .

# Run with docker-compose
docker-compose up -d
```

The service will be available at http://localhost:8000

### Volumes

- `./data:/app/data` - Persistent state, index, and logs
- `./corpus:/app/corpus` - Corpus documents

## Development

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=term-missing

# Or use Make
make test
```

### Linting and Type Checking

```bash
# Lint code
ruff check src/ tests/ scripts/ configs/

# Type check
mypy src/ tests/ scripts/ configs/

# Or use Make
make lint
make typecheck
```

### Adding Corpus Documents

1. Add `.txt` files to the `corpus/` directory
2. Rebuild the index:
   ```bash
   python scripts/build_index.py
   ```
3. Restart the server

## Checkpointing

Create a checkpoint of the current system state:

```bash
curl -X POST http://localhost:8000/api/checkpoint
```

Checkpoints are saved to `data/checkpoints/` and include:
- Timestamp
- Validation hashes (index, manifest)
- Configuration settings

## Deterministic Behavior

Thalos Prime ensures deterministic responses:

1. **Seed Generation**: Seeds are computed from:
   - Session ID
   - User input
   - Salt (configurable)
   - Time bucket (configurable, default 1 hour)

2. **Reproducibility**: Same inputs within the same time bucket produce identical seeds and responses

3. **Seed Logging**: All seeds are logged in:
   - State database (`data/state.db`)
   - Event log (`data/events.jsonl`)
   - Response payload

## Observability

### Structured Logs

Logs are written to stdout with structured format:
```
2024-01-01 12:00:00 | INFO     | module | message | key=value
```

### Event Log

All system events are logged to `data/events.jsonl`:
```json
{"timestamp": "2024-01-01T12:00:00", "event_type": "chat", "session_id": "abc", "data": {...}}
```

Event types:
- `lifecycle` - System lifecycle events
- `seed_generated` - Seed generation
- `retrieval` - Document retrieval
- `generation` - Response generation
- `chat` - Complete chat interactions

## Lifecycle States

The control plane manages these lifecycle states:

1. **UNINITIALIZED** - Initial state
2. **INITIALIZING** - Components being initialized
3. **INITIALIZED** - Ready for validation
4. **VALIDATING** - Running validation checks
5. **VALIDATED** - Validation passed
6. **OPERATING** - Normal operation
7. **RECONCILING** - Re-validating system
8. **CHECKPOINTING** - Creating checkpoint
9. **TERMINATING** - Shutting down
10. **TERMINATED** - Shut down complete
11. **ERROR** - Error state

## Architecture

```
Thalos Prime
├── src/
│   ├── api/         - FastAPI application
│   ├── control/     - Control plane lifecycle
│   ├── data_plane/  - TF-IDF retrieval & generation
│   ├── state/       - SQLite state store
│   ├── observability/ - Logging & event tracking
│   └── utils/       - Utility functions
├── configs/         - Configuration management
├── corpus/          - Text corpus documents
├── scripts/         - Build & serve scripts
├── static/          - Web UI (HTML/CSS/JS)
└── tests/           - Test suite
```

## Troubleshooting

### Index Not Found

If you see "Index not found" errors:
```bash
python scripts/build_index.py
```

### Port Already in Use

Change the port in `.env`:
```env
PORT=8001
```

### Import Errors

Ensure you're running scripts from the project root:
```bash
cd /path/to/ThalosPrimeLibrary
python scripts/serve.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `make test`
5. Submit a pull request
## Core Features

- **Deterministic Page Generation**: Generate Library of Babel pages from hex addresses
- **Query Enumeration**: Map search queries to candidate addresses
- **Enhanced Coherence Scoring**: Multi-metric analysis with language, structure, n-gram, and exact match scoring
- **Hybrid Search**: Local generation and remote fetching capabilities
- **REST API**: FastAPI-based server with full documentation
- **Production Ready**: 80 passing tests, comprehensive error handling, and deterministic behavior

## API Server

Access interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Testing

```bash
# Run all tests
python -m pytest tests -v

# Run with coverage
python -m pytest tests --cov=thalos_prime
```

## Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) - Complete deployment guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md) - Implementation details
- [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) - System verification

## Requirements

- Python 3.7+ (3.11+ recommended)
- See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed prerequisites

## License

MIT License - See LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: https://github.com/XxxGHOSTX/ThalosPrimeLibrary/issues
- Documentation: See `ARCHITECTURE.md` and inline code comments
