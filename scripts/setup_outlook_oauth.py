import json
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / '.env'
SCOPE = 'offline_access https://outlook.office.com/SMTP.Send'
TIMEOUT_SECONDS = 15


def read_env_file():
    values = {}
    if not ENV_FILE.exists():
        return values

    with ENV_FILE.open('r', encoding='utf-8') as env_file:
        for line in env_file:
            stripped = line.strip()
            if not stripped or stripped.startswith('#') or '=' not in stripped:
                continue
            key, value = stripped.split('=', 1)
            values[key.strip()] = value.strip().strip('"\'')
    return values


def post_form(url, values):
    request = Request(
        url,
        data=urlencode(values).encode('ascii'),
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        method='POST',
    )
    with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode('utf-8'))


def update_env_file(values):
    existing_lines = []
    if ENV_FILE.exists():
        with ENV_FILE.open('r', encoding='utf-8', newline='') as env_file:
            existing_lines = env_file.readlines()

    updated_keys = set()
    updated_lines = []
    for line in existing_lines:
        stripped = line.lstrip()
        key = stripped.split('=', 1)[0].strip() if '=' in stripped and not stripped.startswith('#') else None
        if key in values:
            updated_lines.append(f'{key}={values[key]}\n')
            updated_keys.add(key)
        else:
            updated_lines.append(line)

    for key, value in values.items():
        if key not in updated_keys:
            updated_lines.append(f'{key}={value}\n')

    with ENV_FILE.open('w', encoding='utf-8', newline='') as env_file:
        env_file.writelines(updated_lines)


def main():
    settings = read_env_file()
    client_id = os.getenv('EMAIL_OAUTH_CLIENT_ID') or settings.get('EMAIL_OAUTH_CLIENT_ID')
    if not client_id:
        print('Set EMAIL_OAUTH_CLIENT_ID in .env after registering a Microsoft public-client app.')
        return 1

    tenant = os.getenv('EMAIL_OAUTH_TENANT') or settings.get('EMAIL_OAUTH_TENANT') or 'consumers'
    endpoint = f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0'

    try:
        device = post_form(
            f'{endpoint}/devicecode',
            {'client_id': client_id, 'scope': SCOPE},
        )
    except (HTTPError, URLError, OSError, ValueError):
        print('Could not start Microsoft sign-in. Check network access, tenant, and app registration.')
        return 1

    print(device.get('message') or 'Complete Microsoft sign-in using the URL and code below.')
    print(f'Verification URL: {device.get("verification_uri", "https://microsoft.com/devicelogin")}')
    print(f'One-time code: {device.get("user_code", "unavailable")}')

    device_code = device.get('device_code')
    if not device_code:
        print('Microsoft did not provide a device authorization code.')
        return 1

    interval = max(int(device.get('interval', 5)), 1)
    expires_at = time.monotonic() + int(device.get('expires_in', 900))
    while time.monotonic() < expires_at:
        time.sleep(interval)
        try:
            token_data = post_form(
                f'{endpoint}/token',
                {
                    'client_id': client_id,
                    'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
                    'device_code': device_code,
                },
            )
        except HTTPError as error:
            try:
                error_data = json.loads(error.read().decode('utf-8'))
            except (OSError, ValueError):
                print('Microsoft sign-in failed. Rerun setup and review the app registration.')
                return 1
            error_code = error_data.get('error')
            if error_code == 'authorization_pending':
                continue
            if error_code == 'slow_down':
                interval += 5
                continue
            print('Microsoft sign-in was not completed. Rerun setup and review the app registration.')
            return 1
        except (URLError, OSError, ValueError):
            print('Could not complete Microsoft sign-in because of a network or response error.')
            return 1

        refresh_token = token_data.get('refresh_token')
        if not refresh_token:
            print('Microsoft did not issue a refresh token. Ensure offline_access was consented.')
            return 1

        update_env_file({
            'EMAIL_AUTH_METHOD': 'oauth2',
            'EMAIL_OAUTH_TENANT': tenant,
            'EMAIL_OAUTH_REFRESH_TOKEN': refresh_token,
        })
        print('Outlook OAuth is configured in the local .env file. The refresh token was not displayed.')
        return 0

    print('Microsoft sign-in expired. Rerun setup to request a new code.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
