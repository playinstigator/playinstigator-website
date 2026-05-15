# Game Dev Beats — Audio Worker

A Cloudflare Worker that serves the game's audio asset (embedded as base64 in
the worker bundle) with a Referer check. Browsers loading the game from
`playinstigator.com` get the file; direct hits (curl, scrapers, hot-links from
other sites) get 403.

The audio is **not** stored in R2 — it's bundled directly into the deployed
worker. `src/audio.b64.js` and `src/audio.mp3` are gitignored and must be
regenerated locally before each deploy.

Free tier covers this entirely (audio is ~260 KB).

## Setup (one time, ~5 min)

### 1. Install Wrangler + log in

```sh
npm install -g wrangler
wrangler login
```

`wrangler login` opens a browser to authenticate against your Cloudflare account.
If you don't have a Cloudflare account, sign up at https://dash.cloudflare.com/sign-up
(free, no credit card required).

### 2. Stage the audio file and generate the base64 module

From the repo root (PowerShell):

```powershell
$src = "C:\path\to\26.5.10.mp3"
Copy-Item $src cloudflare\audio-worker\src\audio.mp3 -Force
$b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("cloudflare\audio-worker\src\audio.mp3"))
"export const AUDIO_B64 = '$b64';" | Out-File cloudflare\audio-worker\src\audio.b64.js -Encoding utf8 -NoNewline
```

### 3. Deploy the Worker

```sh
cd cloudflare/audio-worker
wrangler deploy
```

The output prints the Worker URL, e.g.
`https://gamedev-beats-audio.<account-subdomain>.workers.dev`.

### 4. Update the game's audio URL

In `games/gamedev-beats/index.html`:

```js
const TRACK_AUDIO_URL = 'https://gamedev-beats-audio.<account-subdomain>.workers.dev/26.5.10.mp3';
```

The path segment (`26.5.10.mp3`) is cosmetic — the worker ignores it and serves
the embedded bytes — but bumping it acts as a cache-buster when you swap audio.

Commit + push and the live site should play.

## Verify it works

```sh
# Should 403 (no referer):
curl -I https://gamedev-beats-audio.<account-subdomain>.workers.dev/26.5.10.mp3

# Should 200 (with referer):
curl -I -H "Referer: https://playinstigator.com/games/gamedev-beats/" \
  https://gamedev-beats-audio.<account-subdomain>.workers.dev/26.5.10.mp3
```

## Updating the audio file

1. Re-run the staging + base64 step above with the new mp3.
2. `wrangler deploy`.
3. Bump the path segment in `TRACK_AUDIO_URL` (e.g. `26.5.10.mp3` → `26.5.11.mp3`)
   to bust the 1-hour edge cache and 1-day browser cache.

## Local dev

`http://localhost:8765` and `http://127.0.0.1:8765` are in the allowed-origins
list (`src/index.js`) for local testing with `python -m http.server 8765`.
For other local ports, edit the array.

## What this protects against

- Casual hot-linking from other sites (Referer ≠ playinstigator.com)
- GitHub-clone scrapers (audio isn't in the repo)
- Search-engine indexing (no public crawlable URL)

## What this doesn't protect against

- A determined visitor opening DevTools, copying the URL, and adding a
  matching `Referer` header to a curl request. (Referer can be spoofed.)
- Anyone who has the audio in their browser cache can save it via right-click.

For an icebreaker game audio asset, this is the right level of obstruction.
