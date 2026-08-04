# Import all ORM models to populate the SQLAlchemy registry before any mapper
# configuration runs. Any module that triggers SQLAlchemy relationship resolution
# (e.g. the worker) must have the full registry in place.
from app.models import user as _  # noqa: F401
from app.models import source as _  # noqa: F401
from app.models import chunk as _  # noqa: F401
from app.models import knowledge_base as _  # noqa: F401
from app.models import collection as _  # noqa: F401
from app.models import learning as _  # noqa: F401
from app.models import asset as _  # noqa: F401
