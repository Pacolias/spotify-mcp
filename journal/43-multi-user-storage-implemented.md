# Multi-user storage implemented: users, encrypted Spotify credentials

**Date:** 2026-09-28

Implements decisions 1 and 5 of [entry 42](42-multi-user-data-model.md). The OAuth-server tables (clients, pending authorizations, auth codes, refresh tokens) are **not** added yet. They'll arrive with the provider that uses them, so no table exists without code behind it.

## What changed

- **`users`** (keyed by Spotify user ID) and **`spotify_credentials`** (one row per user) replace the old single-row `spotifytoken` table.
- Spotify tokens are **Fernet-encrypted** (`spotify_mcp/db/encryption.py`) using the new required `TOKEN_ENCRYPTION_KEY` setting. Fernet is authenticated encryption, so tampered ciphertext, or ciphertext made with another key, fails loudly instead of decrypting to garbage.
- The login callback now calls Spotify's `/v1/me` to find out *who* logged in, and stores the tokens under that user.
- `get_valid_access_token(user_id)` works per user. With `user_id=None`, meaning the local stdio server, which has no authenticated caller, it uses the single stored user, and refuses to guess if there's more than one. The remote server will pass the user from the verified access token's `sub`.

## Old data: dropped, not migrated

`init_db()` drops the old `spotifytoken` table. It held **plaintext** tokens, and migrating them would have meant keeping them on disk until the migration ran. Since there's a single local user, one more `spotify-mcp login` repopulates everything, now encrypted. There's no migration tool (e.g. Alembic) yet. Whether to add one gets decided together with the production database (SQLite vs Postgres) when we get to deployment.
