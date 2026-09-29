"""
Importing this package registers every AI tool via the @ai_tool decorator
(see erp_ai.ai.decorators / erp_ai.ai.registry). Add new tool modules here.
"""

from erp_ai.ai.tools import system  # noqa: F401
from erp_ai.ai.tools import documents  # noqa: F401
from erp_ai.ai.tools import analytics  # noqa: F401
from erp_ai.ai.tools import reports  # noqa: F401
from erp_ai.ai.tools import workflow  # noqa: F401 - Claude-only tools, see providers=["claude"] there
from erp_ai.ai.tools import inventory  # noqa: F401 - Claude-only tools, see providers=["claude"] there
from erp_ai.ai.tools import finance  # noqa: F401 - Claude-only tools, see providers=["claude"] there
from erp_ai.ai.tools import crm  # noqa: F401 - Claude-only tools, see providers=["claude"] there
from erp_ai.ai.tools import hr  # noqa: F401 - Claude-only tools, see providers=["claude"] there
from erp_ai.ai.tools import automation  # noqa: F401 - Claude-only tools, see providers=["claude"] there
from erp_ai.ai.tools import audit  # noqa: F401 - Claude-only tools, see providers=["claude"] there
from erp_ai.ai.tools import purchasing  # noqa: F401 - Claude-only tools, see providers=["claude"] there
from erp_ai.ai.tools import projects  # noqa: F401 - Claude-only tools, see providers=["claude"] there
from erp_ai.ai.tools import support  # noqa: F401 - Claude-only tools, see providers=["claude"] there
from erp_ai.ai.tools import knowledge  # noqa: F401 - Claude-only tools, see providers=["claude"] there
from erp_ai.ai.tools import planning  # noqa: F401 - Claude-only tools, see providers=["claude"] there
from erp_ai.ai.tools import notifications  # noqa: F401 - Claude-only tools, see providers=["claude"] there
from erp_ai.ai.tools import communication  # noqa: F401 - Claude-only tools, see providers=["claude"] there