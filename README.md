# NAS Gallery Platform

Public GitHub Pages frontend + Flask API on the ASUSTOR NAS.

## Features
- Public galleries with title, description and a selected NAS folder.
- Admin password protects gallery creation/editing/removal and appearance changes.
- Theme presets: Midnight, Ocean, Forest, Sunset and Light.
- Custom background color and HTTPS background image URL.
- Image grid with lazy-loaded thumbnails; media listing is paginated in batches of 40.
- Fullscreen image viewer and browser video player.
- Server-side protected API endpoints for file rename and delete. Gallery removal only removes the listing, never the NAS folder.

## 1. GitHub Pages
Upload `index.html`, `style.css`, `app.js`, `config.js` to the root of a GitHub repository. Enable Settings > Pages > Deploy from a branch > `main` > `/ (root)`.
Edit `config.js` and set `API_BASE` to your public HTTPS API hostname. This URL is public; do not put a password in this file.

## 2. ASUSTOR API
Install Python 3 and pip (or run the server in a supported container). Copy the `server` folder to the NAS. Confirm the actual shared-folder path in ADM first. Example only:

```bash
python3 -m pip install -r requirements.txt
export NAS_MEDIA_ROOT="/volume1/Media"
export NAS_GALLERY_DATA="/volume1/home/aab/.nas-gallery"
export NAS_GALLERY_ADMIN_PASSWORD='CHOOSE-A-LONG-UNIQUE-PASSWORD'
export NAS_GALLERY_ORIGIN='https://YOUR-USERNAME.github.io'
python3 server.py
```

Use the exact GitHub Pages origin without repository path or trailing slash. Keep the process running for the first test. Set these environment variables persistently when configuring the service/container.

## 3. Public HTTPS with Cloudflare Tunnel
A stable named tunnel normally requires a domain added to Cloudflare:
1. Add your domain to Cloudflare and follow its nameserver setup.
2. Create a Tunnel in the Cloudflare Zero Trust dashboard.
3. Install `cloudflared` on the NAS or run it in a supported container.
4. Add a public hostname such as `gallery-api.yourdomain.com` routed to `http://127.0.0.1:8765`.
5. Run the tunnel persistently and set `API_BASE` in `config.js` to `https://gallery-api.yourdomain.com`.

Temporary connectivity test only: `cloudflared tunnel --url http://127.0.0.1:8765` creates a temporary `trycloudflare.com` URL that changes after restart. Do not open router ports. Tailscale Serve is not the right tool for a public site because it serves tailnet users; Cloudflare Tunnel provides public ingress.

## Security and limitations
- Published galleries are public: anyone can view and download files in those selected folders. Never publish private folders.
- The admin password is checked by the NAS, not JavaScript. The frontend stores a short-lived bearer token in sessionStorage (8 hours); log out on shared devices.
- Login is rate-limited per source IP in the app. Consider Cloudflare rate limiting/Access rules too.
- Rename/delete endpoints are implemented and password-protected, but file-level controls are not yet exposed in this first admin UI. The initial UI manages galleries and appearance.
- File deletion is permanent. Keep NAS backups.
- The API paginates 40 files per request; it currently scans the selected folder to determine pages. For huge folders, use an indexed media database in a later version.
- Browser codec support varies. MP4/H.264 + AAC has broad compatibility; MKV/AVI may not play.
