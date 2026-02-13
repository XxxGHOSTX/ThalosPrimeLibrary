# Data Directory

This directory is used for storing runtime data, configurations, and persistent storage for Thalos Prime.

## Contents

- **Library Data**: Local Library of Babel data (if configured)
- **Cache**: Temporary cache files
- **Logs**: Application logs (in production deployments)
- **Database**: Local database files (if using SQLite)

## Configuration

Set the `THALOS_LIBRARY_PATH` environment variable to point to this directory:

```bash
export THALOS_LIBRARY_PATH=/path/to/ThalosPrimeLibrary/data
```

## Docker

When using Docker, this directory is mounted as a volume for persistent storage:

```bash
docker run -v $(pwd)/data:/app/data thalos-prime
```

## Note

This directory is gitignored to prevent committing runtime data to version control.

