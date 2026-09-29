# AION Backend

AION is an agentic AI platform for B2B discovery. This `server/` package is only the backend foundation: it defines the FastAPI app, Clean Architecture package boundaries, placeholder domain models, typed schemas, service contracts, runtime shells, and mock API surfaces.

This phase intentionally does not implement AI, planner reasoning, Supabase, PostgreSQL connectivity, scraping, external APIs, vector storage, or business logic.

## Architecture

- `app/main.py` creates the FastAPI application, API versioning, Swagger, ReDoc, CORS, middleware, lifespan events, and global exception handlers.
- `app/core/` contains configuration, logging, security placeholders, constants, exceptions, and startup/shutdown hooks.
- `app/api/` contains HTTP routes, middleware, dependencies, and future websocket boundaries.
- `app/models/` contains placeholder SQLAlchemy model definitions. The platform centers on `mission_id`.
- `app/schemas/` contains Pydantic v2 create/read/update/response schemas for every placeholder model.
- `app/services/` contains service classes with method stubs only.
- `app/agents/` contains the base agent framework, registry, task/response/state types, and named mock agents.
- `app/runtime/` contains skeleton runtime components for missions, planning, orchestration, scheduling, events, memory, and execution management.
- `tests/` contains pytest placeholders for the app shell and registry.

## Folder Structure

```text
server/
  app/
    api/
      routes/
      websocket/
      middleware/
      dependencies/
    core/
    runtime/
      planner/
      orchestrator/
      scheduler/
      registry/
      event_bus/
      mission_runtime/
    agents/
      base/
      planner/
      discovery/
      enrichment/
      intelligence/
      reasoning/
      recommendation/
      utility/
    services/
    models/
    schemas/
    database/
    memory/
    integrations/
    utils/
    main.py
  tests/
  pyproject.toml
```

## How To Run

```bash
cd server
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Then open:

- Swagger: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Health: `http://127.0.0.1:8000/health`
- Versioned OpenAPI: `http://127.0.0.1:8000/api/v1/openapi.json`

## Development Guide

Treat `Mission` as the primary aggregate. Future workflows, execution graphs, agent executions, signals, companies, recommendations, timelines, intelligence reports, and knowledge graph data should reference `mission_id`.

Keep adapters at the edges:

- API routes should validate transport input and call services.
- Services should coordinate use cases.
- Runtime components should handle orchestration concerns.
- Agents should implement bounded capability contracts.
- Database and external integrations should remain behind explicit interfaces.

## Future Supabase Integration

Supabase should be added later as an infrastructure adapter, not as a domain dependency. A future implementation can add SQLAlchemy session wiring, migrations, repositories, and auth adapters under `app/database/`, `app/integrations/`, and `app/api/dependencies/` while preserving the current service and mission-centric boundaries.

