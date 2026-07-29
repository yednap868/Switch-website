# Scripts

Testing and utility scripts for Vance. Run from the project root directory.

## Prerequisites

```bash
source env_vars.sh  # Load environment variables
```

## Scripts

| Script | Description |
|--------|-------------|
| `cli_test.py` | Interactive CLI for testing agent conversations |
| `cli_test_postcall.py` | Test post-call webhook flow with real Firebase data |
| `test_elevenlabs_webhook.py` | Execute ElevenLabs webhook handler directly |
| `test_hybrid_matching.py` | Interactive hybrid matching service tester |
| `test_matching_repl.py` | REPL for testing profile matching queries |
| `test_qdrant_collections.py` | Export Qdrant collections to JSON |
| `sync_extractions_to_qdrant.py` | Sync Firebase extractions to Qdrant |
| `import_linkedin_csv_to_qdrant.py` | Import LinkedIn CSV profiles to Qdrant |
| `delete_user_data.py` | Delete user data from Firebase collections |

## Usage

### cli_test.py
```bash
python scripts/cli_test.py
python scripts/cli_test.py --phone 919876543210
```
Commands: `/quit`, `/profile`, `/tools`, `/type`, `/reset`, `/history`, `/help`

### cli_test_postcall.py
```bash
python scripts/cli_test_postcall.py
python scripts/cli_test_postcall.py --phone 919876543210
```
Commands: `/test`, `/intent`, `/decision`, `/match`, `/data`, `/set-extraction`, `/help`, `/quit`

### test_elevenlabs_webhook.py
```bash
python scripts/test_elevenlabs_webhook.py
python scripts/test_elevenlabs_webhook.py --phone 919876543210
python scripts/test_elevenlabs_webhook.py --template job_provider
python scripts/test_elevenlabs_webhook.py --dry-run
```
Templates: `job_provider_backend`, `job_provider_frontend`, `job_seeker_fullstack`, `job_seeker_backend`, `general_founder`, `general_investor`, `minimal_test`

### test_hybrid_matching.py
```bash
python scripts/test_hybrid_matching.py
```
Interactive menu with pre-defined test scenarios.

### test_matching_repl.py
```bash
python scripts/test_matching_repl.py
```
Commands: `/quit`, `/example`, `/fields`, `/limit N`, `/min N.N`

### test_qdrant_collections.py
```bash
python scripts/test_qdrant_collections.py
```
Exports to `qdrant_export_YYYYMMDD_HHMMSS.json`

### sync_extractions_to_qdrant.py
```bash
python scripts/sync_extractions_to_qdrant.py
```

### import_linkedin_csv_to_qdrant.py
```bash
python scripts/import_linkedin_csv_to_qdrant.py
```
Edit script to set CSV file path.

### delete_user_data.py
```bash
python scripts/delete_user_data.py
```
Edit script to set phone numbers to delete.
