"""Identity for an explicitly configured private Dialogs Cloud Function only.

The deployment must restrict IAM invocation to Dialogs and trusted administrators.
JSON identifiers alone are never credentials for the public device API.
"""

import hashlib
import os

from shared_chess.repository import encode


def dialogs_owner(event, context):
    function_id = os.environ.get('SHARED_DIALOGS_FUNCTION_ID', '')
    skill_id = os.environ.get('SHARED_DIALOGS_SKILL_ID', '')
    if not function_id or not skill_id or getattr(context, 'function_name', None) != function_id:
        raise ValueError('Native Dialogs transport is not configured')
    if any(key in event for key in ('httpMethod', 'requestContext', 'body')):
        raise ValueError('An HTTP envelope cannot authenticate a Dialogs user')
    session = event.get('session', {})
    if session.get('skill_id') != skill_id:
        raise ValueError('Unexpected skill')
    user_id = (session.get('user') or {}).get('user_id')
    if user_id is None:
        return None  # Anonymous application IDs are not an account identity.
    if not isinstance(user_id, str) or not 1 <= len(user_id) <= 128:
        raise ValueError('Invalid account identity')
    return 'dialogs:' + hashlib.sha256(encode([skill_id, user_id]).encode()).hexdigest()
