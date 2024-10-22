# Copyright © 2024 IOTIC LABS LTD. info@iotics.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://github.com/Iotic-Labs/nyx-sdk/blob/main/LICENSE
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from functools import wraps

import requests


def ensure_setup(func):
    """Makes sure the client has performed inital setup."""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self._is_setup:
            self._setup()
        return func(self, *args, **kwargs)

    return wrapper


def auth_retry(func):
    """Simple retry wrapper, that retries the function once, on 401."""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401 and not getattr(wrapper, "_retried", False):
                # Unauthorized error and haven't retried yet
                wrapper._retried = True
                self._authorise(refresh=True)
                return func(self, *args, **kwargs)
            else:
                # Either it's not an auth error or we've already retried
                raise
        finally:
            wrapper._retried = False

    return wrapper
