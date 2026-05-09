# Game Dev Beats — Audio Worker

A Cloudflare Worker that serves the game's audio asset from a private R2 bucket
with a Referer check. Browsers loading the game from `playinstigator.com` get
the file; direct hits (curl, scrapers, hot-links from other sites) get 403.

Free tier covers this entirely (audio is ~220 KB; R2 has unlimited free egress).

## Setup (one time, ~10 min)

### 1. Install Wrangler + log in

```sh
npm install -g wrangler
wrangler login
```

`wrangler login` opens a browser to authenticate against your Cloudflare account.
If you don't have a Cloudflare account, sign up at https://dash.cloudflare.com/sign-up
(free, no credit card required).

### 2. Create the R2 bucket

```sh
wrangler r2 bucket create gamedev-beats-audio
```

R2 has to be enabled on the account once before this works. The dashboard
prompts you to enable it the first time you visit `https://dash.cloudflare.com`
→ R2 (still free).

### 3. Upload the audio file

From the repo root:

```sh
wrangler r2 object put gamedev-beats-audio/26.5.9.mp3 \
  --file games/gamedev-beats/26.5.9.mp3 \
  --content-type audio/mpeg
```

### 4. Deploy the Worker

From this directory:

```sh
cd cloudflare/audio-worker
wrangler deploy
```

The output prints your Worker URL, something like:

```
https://gamedev-beats-audio.<account-subdomain>.workers.dev
```

Copy that URL.

### 5. Update the game's audio URL

In `games/gamedev-beats/index.html`, change:

```js
const TRACK_AUDIO_URL = './26.5.9.mp3';
```

to:

```js
const TRACK_AUDIO_URL = 'https://gamedev-beats-audio.<account-subdomain>.workers.dev/26.5.9.mp3';
```

Commit + push and the live site should play.

## Verify it works

```sh
# Should 403 (no referer):
curl -I https://gamedev-beats-audio.<account-subdomain>.workers.dev/26.5.9.mp3

# Should 200 (with referer):
curl -I -H "Referer: https://playinstigator.com/games/gamedev-beats/" \
  https://gamedev-beats-audio.<account-subdomain>.workers.dev/26.5.9.mp3
```

## Updating the audio file

Replace the file:

```sh
wrangler r2 object put gamedev-beats-audio/26.5.9.mp3 \
  --file games/gamedev-beats/26.5.9.mp3 \
  --content-type audio/mpeg
```

The Worker has 1-hour edge cache and 1-day browser cache. To bust caches
immediately, append `?v=2` to `TRACK_AUDIO_URL` and bump the number on each
update.

## Local dev

`http://localhost:8765` and `http://127.0.0.1:8765` are in the allowed-origins
list (`src/index.js`) for local testing with `python -m http.server 8765`.
For other local ports, edit the array.

## What this protects against

- Casual hot-linking from other sites (Referer ≠ playinstigator.com)
- GitHub-clone scrapers (file isn't in the repo)
- Search-engine indexing (no public crawlable URL)

## What this doesn't protect against

- A determined visitor opening DevTools, copying the URL, and adding a
  matching `Referer` header to a curl request. (Referer can be spoofed.)
- Anyone who has the audio in their browser cache can save it via right-click.

For an icebreaker game audio asset, this is the right level of obstruction.
