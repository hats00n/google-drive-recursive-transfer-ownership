# Google Drive Recursive Transfer Ownership

A minimal Python CLI to transfer ownership of Google Drive files and folders. It can:

- Transfer every file owned by a source account to a destination account.
- Recursively transfer only selected folders (and their contents).
- Run in dry-run mode to preview changes.

## Prerequisites

- Python 3.9+
- A Google Cloud project with the **Drive API** enabled.
- An OAuth 2.0 **Desktop** client ID downloaded as `client_secret.json`.
- Permission in your Google Workspace to transfer ownership between accounts (consumer Gmail accounts cannot transfer ownership outside their domain).

## Setup

1. Create or activate a virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Place your OAuth client JSON in the repository root (default path: `client_secret.json`).
4. The first run will prompt a browser-based OAuth flow and save credentials to `token.json`.

## Usage

> For all commands, authenticate as the **current owner** account.

### Transfer everything owned by a user

```bash
python gdrive_transfer.py \
  --source-email alice@example.com \
  --target-email bob@example.com
```

### Transfer selected folders recursively

Pass one or more Drive folder IDs (found in the folder URL). Contents are traversed recursively and only items owned by the source are changed.

```bash
python gdrive_transfer.py \
  --source-email alice@example.com \
  --target-email bob@example.com \
  --folder-id 1a2B3cFolderId \
  --folder-id AnotherFolderId
```

### Preview without making changes

```bash
python gdrive_transfer.py \
  --source-email alice@example.com \
  --target-email bob@example.com \
  --dry-run
```

### Custom auth file locations

If you keep the OAuth files elsewhere, point the CLI to them:

```bash
python gdrive_transfer.py \
  --client-secret path/to/client_secret.json \
  --token path/to/token.json \
  --source-email alice@example.com \
  --target-email bob@example.com
```

## Notes

- The tool requests the `https://www.googleapis.com/auth/drive` scope to allow ownership changes.
- Files you do **not** own are skipped automatically.
- Google requires notification emails to be sent for ownership transfers, so recipients will
  receive transfer emails automatically.
- Google imposes limits: ownership transfers may be restricted by domain policies or file types (e.g., some shared drives).
- Errors for individual files are logged but do not stop the rest of the transfers.
