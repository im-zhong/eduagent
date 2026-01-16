"""Shared SQLAlchemy Base for all modules.

This module provides a single global Base class that all feature modules
should use for their database models. Using a shared Base ensures:

1. Cross-module foreign keys work correctly (e.g., quiz.doc_id -> source_document.id)
2. All tables are in a single metadata object for proper FK resolution
3. Simpler table creation and migration management
4. No need for complex metadata sharing or stub table registration

Architecture decision: Single global Base vs module-specific Bases
------------------------------------------------------------------
Earlier we considered having each module own its own Base class for
modularity. However, this created complexity with cross-module foreign keys:
- String-based FKs work for DDL but not for ORM flush operations
- Required complex metadata sharing between modules
- Made table creation and testing more complicated

The chosen approach: Single global Base
- All models inherit from a common Base
- Simpler FK resolution
- Each module still owns its models (just not the Base)
- Clear separation of concerns via module organization

If true module isolation is needed in the future (separate databases per module),
then each module would need its own Base + separate database connections.
"""
from sqlalchemy.orm import DeclarativeBase


# Global Base class - all feature modules should inherit from this
# SQLAlchemy 2.0 requires creating a subclass of DeclarativeBase
class Base(DeclarativeBase):
    """Global SQLAlchemy Base class for all modules.

    All feature modules (documents, quiz, etc.) should import and inherit
    from this Base class. This ensures all tables are registered in a
    single metadata object, enabling cross-module foreign keys to work.
    """
    pass
