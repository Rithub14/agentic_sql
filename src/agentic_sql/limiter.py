from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared rate-limiter instance imported by both main.py and routes.py.
# Keeping it here breaks the circular import that would arise if routes.py
# tried to import it from main.py.
limiter = Limiter(key_func=get_remote_address)
