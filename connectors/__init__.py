"""Provider Connectors Package.

Strict Architectural Rule:
Connectors must NEVER import or access the database or SQLAlchemy models directly.
They accept credentials and parameters, communicate only with approved official provider APIs,
and return normalized Pydantic models.
"""
