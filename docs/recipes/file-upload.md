# File Uploads

Use this recipe when users need to upload documents, images, exports, or other
binary assets.

## Setup

```bash
make api-install
cp apps/api/.env.example apps/api/.env
```

Decide whether files are stored locally for development, in object storage for
production, or both behind one storage service interface.

## Env Vars

```bash
APP_UPLOAD_MAX_BYTES=10485760
APP_STORAGE_BACKEND=local
APP_STORAGE_LOCAL_DIR=./var/uploads
S3_BUCKET=
S3_REGION=
S3_ENDPOINT_URL=
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=
```

Use provider-specific variables only when the selected storage backend needs
them.

## Implementation Notes

- Add an `app/files/` domain for upload metadata, validation, and access rules.
- Keep binary storage behind a small service interface so local and object
  storage can share endpoint behavior.
- Validate content type, extension, and size before persisting metadata.
- Store file metadata in PostgreSQL and binary content outside the database.
- Return signed URLs for private files instead of exposing storage bucket paths.
- Add cleanup paths for failed uploads and deleted records.

## Verification

```bash
make api-lint
make api-format-check
make api-typecheck
make api-test
```

Include tests for max-size rejection, unsupported content type, authorization,
and metadata persistence.
