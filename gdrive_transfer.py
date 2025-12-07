"""
CLI tool to recursively transfer ownership of Google Drive files.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import deque
from typing import Iterable, List, Optional, Set

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/drive"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Recursively transfer ownership of Google Drive files."
        )
    )
    parser.add_argument(
        "--client-secret",
        default="client_secret.json",
        help="Path to OAuth client secret JSON file (defaults to client_secret.json)",
    )
    parser.add_argument(
        "--token",
        default="token.json",
        help="Path to store OAuth token (defaults to token.json)",
    )
    parser.add_argument("--source-email", required=True, help="Email of current owner")
    parser.add_argument(
        "--target-email", required=True, help="Email that should become the new owner"
    )
    parser.add_argument(
        "--folder-id",
        action="append",
        dest="folder_ids",
        help=(
            "Folder ID to transfer recursively. "
            "Provide multiple times to include several folders. "
            "If omitted, all files owned by the source will be transferred."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be transferred without changing ownership",
    )
    return parser.parse_args()


def load_credentials(client_secret_path: str, token_path: str) -> Credentials:
    creds: Optional[Credentials] = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(token_path, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())
    return creds


def build_service(creds: Credentials):
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def list_owned_files(service, source_email: str) -> List[dict]:
    files: List[dict] = []
    page_token = None
    query = f"'{source_email}' in owners and trashed = false"

    while True:
        response = (
            service.files()
            .list(
                q=query,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                pageSize=1000,
                pageToken=page_token,
                fields="nextPageToken, files(id, name, mimeType)",
            )
            .execute()
        )
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return files


def list_owned_in_folders(service, source_email: str, folder_ids: Iterable[str]) -> List[dict]:
    seen: Set[str] = set()
    queue: deque[str] = deque(folder_ids)
    files: List[dict] = []

    while queue:
        folder_id = queue.popleft()
        if folder_id in seen:
            continue
        seen.add(folder_id)

        query = (
            f"'{folder_id}' in parents and trashed = false and '{source_email}' in owners"
        )
        page_token = None
        while True:
            response = (
                service.files()
                .list(
                    q=query,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    pageSize=200,
                    pageToken=page_token,
                    fields="nextPageToken, files(id, name, mimeType)",
                )
                .execute()
            )
            for item in response.get("files", []):
                files.append(item)
                if item.get("mimeType") == "application/vnd.google-apps.folder":
                    queue.append(item["id"])
            page_token = response.get("nextPageToken")
            if not page_token:
                break
    return files


def transfer_file(service, file_id: str, target_email: str) -> None:
    permission = {"type": "user", "role": "owner", "emailAddress": target_email}
    service.permissions().create(
        fileId=file_id,
        body=permission,
        transferOwnership=True,
        supportsAllDrives=True,
        sendNotificationEmail=False,
    ).execute()


def main() -> int:
    args = parse_args()
    creds = load_credentials(args.client_secret, args.token)
    service = build_service(creds)

    try:
        if args.folder_ids:
            files = list_owned_in_folders(service, args.source_email, args.folder_ids)
        else:
            files = list_owned_files(service, args.source_email)
    except HttpError as error:
        print(f"Failed to list files: {error}", file=sys.stderr)
        return 1

    if not files:
        print("No files owned by the source account matched the selection.")
        return 0

    print(f"Found {len(files)} files/folders to transfer.")

    for item in files:
        if args.dry_run:
            print(f"[dry-run] Would transfer {item['name']} ({item['id']})")
            continue
        try:
            transfer_file(service, item["id"], args.target_email)
            print(f"Transferred ownership: {item['name']} ({item['id']})")
        except HttpError as error:
            print(
                f"Failed to transfer {item['name']} ({item['id']}): {error}",
                file=sys.stderr,
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
