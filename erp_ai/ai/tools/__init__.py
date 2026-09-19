"""
Importing this package registers every AI tool via the @ai_tool decorator
(see erp_ai.ai.decorators / erp_ai.ai.registry). Add new tool modules here.
"""

from erp_ai.ai.tools import system  # noqa: F401
from erp_ai.ai.tools import documents  # noqa: F401
from erp_ai.ai.tools import analytics  # noqa: F401
from erp_ai.ai.tools import reports  # noqa: F401
