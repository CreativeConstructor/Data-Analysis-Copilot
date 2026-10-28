# PostgreSQL and pgvector setup

DataPilot's migration `datapilot.0002_columnschema` enables PostgreSQL's
`vector` extension and creates a 768-dimensional vector field for each
dataset column. Install the pgvector server extension on the PostgreSQL
instance before applying Django migrations. The migration runs
`CREATE EXTENSION vector`, which requires a database role permitted to create
extensions (commonly a superuser or a role granted suitable extension
privileges by the database administrator). Once installed and enabled, the
application role needs normal table and schema privileges for Django
migrations and runtime queries.

The Gemini embedding model and dimensions are configured with
`GEMINI_EMBEDDING_MODEL` and `GEMINI_EMBEDDING_DIMENSIONS`; the checked-in
example uses `gemini-embedding-001` with 768 dimensions. Changing dimensions
requires a matching migration and re-indexing existing schema documents.
SQLite is useful for local unit tests but does not provide pgvector similarity
search; use PostgreSQL with the extension to verify retrieval end to end.
