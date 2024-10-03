from functools import wraps
import requests

def ensure_setup(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self._is_setup:
            self._setup()
        return func(self, *args, **kwargs)
    return wrapper

def auth_retry(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401 and not getattr(wrapper, '_retried', False):
                # Unauthorized error and haven't retried yet
                print("Retrying auth...")
                self._authorise(refresh=True)
                wrapper._retried = True
                return func(self, *args, **kwargs)
            else:
                # Either it's not an auth error or we've already retried
                print("Auth failed again!")
                raise
        finally:
            wrapper._retried = False

    return wrapper
