"""Refresh a Meta long-lived token without committing or logging its value.

Required environment: META_APP_ID, META_APP_SECRET, IG_ACCESS_TOKEN.
By default, update the IG_ACCESS_TOKEN GitHub secret using authenticated GitHub CLI.
Use --print-token only on a private local terminal, never in CI logs.
"""
from __future__ import annotations
import argparse
import os
import shutil
import subprocess
import sys
import requests

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-token", action="store_true",
                        help="print the new token locally (never use in CI logs)")
    parser.add_argument("--secret-name", default="IG_ACCESS_TOKEN")
    args = parser.parse_args()
    app_id = os.getenv("META_APP_ID", "").strip()
    app_secret = os.getenv("META_APP_SECRET", "").strip()
    current = os.getenv("IG_ACCESS_TOKEN", "").strip()
    if not all((app_id, app_secret, current)):
        raise SystemExit("Set META_APP_ID, META_APP_SECRET and IG_ACCESS_TOKEN in your local environment.")
    response = requests.get("https://graph.facebook.com/v23.0/oauth/access_token", params={
        "grant_type": "fb_exchange_token", "client_id": app_id,
        "client_secret": app_secret, "fb_exchange_token": current,
    }, timeout=30)
    response.raise_for_status()
    payload = response.json()
    refreshed = payload.get("access_token")
    if not refreshed:
        raise SystemExit("Meta did not return an access_token; inspect the API error without sharing secrets.")
    if args.print_token:
        print(refreshed)
        print(f"Token refreshed; expires_in={payload.get('expires_in', 'unknown')} seconds.", file=sys.stderr)
        return
    if shutil.which("gh"):
        result = subprocess.run(["gh", "secret", "set", args.secret_name],
                                input=refreshed, text=True, capture_output=True, check=False)
        if result.returncode == 0:
            print(f"Updated GitHub Actions secret {args.secret_name}; token value was not printed.")
            return
        print("GitHub CLI could not update the secret. Authenticate with gh auth login and retry, or use --print-token locally.", file=sys.stderr)
        raise SystemExit(result.returncode)
    raise SystemExit("GitHub CLI not found. Install/authenticate gh, or rerun with --print-token and update the secret manually.")
if __name__ == "__main__":
    main()
