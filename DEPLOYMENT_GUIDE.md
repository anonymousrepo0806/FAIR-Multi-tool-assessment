# FAIR Multi-tool Assessment — Deployment Guide (anonymous review)

**Setup**

```
Reviewer ─► https://anonymousrepo0806.github.io/FAIR-Multi-tool-assessment/   (frontend, GitHub Pages)
                │  API calls
                ▼
            https://<random>.trycloudflare.com   (Cloudflare tunnel, hides server IP)
                │
                ▼
            Oracle VM 129.152.8.86 → nginx :80 → backend :8000 + F-UJI :1071
```

| Item | Value |
|---|---|
| GitHub account | `anonymousrepo0806` |
| Repo | https://github.com/anonymousrepo0806/FAIR-Multi-tool-assessment |
| Server | Oracle `FAIR-Multi-assess`, Ubuntu, Milan, IP `129.152.8.86` |
| SSH key | `D:\keys\FAIR-multi-assess\ssh-key-2026-10-07-1.key` |
| Frontend URL | https://anonymousrepo0806.github.io/FAIR-Multi-tool-assessment/ |
| Backend URL | changes on restart — see Part 9 |

> Keep this file private. Do **not** commit it to the repo (it contains the server IP and key path).

---

## Part 1 — Anonymous code on GitHub ✅ done

- Anonymous account `anonymousrepo0806`; public repo with anonymized code.
- Commits authored as `Anonymous <anonymous@example.com>`; no `.env` in the repo.

To push changes later from Windows (PowerShell, inside the project folder):

```powershell
git add .
git commit -m "Update"
git push https://anonymousrepo0806:YOUR_TOKEN@github.com/anonymousrepo0806/FAIR-Multi-tool-assessment.git main
Clear-History
```

Use a **classic** token with the `repo` scope from the anonymous account. Never authorize with your personal account.

---

## Part 2 — Oracle server ✅ done (resize still to do)

1. Compute → Instances → Create instance → **Canonical Ubuntu**, shape **VM.Standard.A1.Flex**, generate an SSH key pair and **download the private key**.
2. ⚠️ **Resize:** the VM currently has only ~1 GB RAM. Instance → **Actions → Edit → Edit shape** → **2 OCPU / 12 GB** (Always Free limit since June 2026). The server reboots.
3. Windows key permissions (once):

```powershell
icacls "D:\keys\FAIR-multi-assess\ssh-key-2026-10-07-1.key" /inheritance:r
icacls "D:\keys\FAIR-multi-assess\ssh-key-2026-10-07-1.key" /grant:r "$($env:USERNAME):(R)"
icacls "D:\keys\FAIR-multi-assess\ssh-key-2026-10-07-1.key" /remove "NT AUTHORITY\Authenticated Users" "BUILTIN\Users" "Everyone"
```

4. Connect:

```powershell
ssh -i "D:\keys\FAIR-multi-assess\ssh-key-2026-10-07-1.key" ubuntu@129.152.8.86
```

| Problem | Fix |
|---|---|
| `Permission denied (publickey)` | Wrong key file — use `ssh-key-2026-10-07-1.key` (the one without `.pub`) |
| `bad permissions` | Run the three `icacls` lines above |
| `Connection refused` | Server still booting — wait 1–2 min |
| Login hangs / commands freeze | Out of memory → Oracle console → Actions → **Reboot** (force), then Part 4 |
| `Out of capacity` when creating/resizing | Retry later (early morning works best) or try 1 OCPU / 6 GB |

---

## Part 3 — Prepare the server ✅ done

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER
newgrp docker

# 4 GB swap — safety net against freezing
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h      # should show Swap: 4.0Gi
```

---

## Part 4 — Run the backend ✅ done

```bash
cd ~
git clone https://github.com/anonymousrepo0806/FAIR-Multi-tool-assessment.git
cd FAIR-Multi-tool-assessment
cp .env.example .env
nano .env
```

Set in `.env` (save: Ctrl+O, Enter, Ctrl+X):

```
GEMINI_API_KEY=your_key
FRONTEND_ORIGINS=https://anonymousrepo0806.github.io
```

Start **only** the three services the app needs (GraphDB and Postgres are unused by default and overload a small server):

```bash
docker compose build fuji backend frontend
docker compose up -d --no-deps fuji backend frontend
docker compose stop graphdb postgres
sleep 60
curl http://localhost/health      # → {"status":"ok"}
```

A `502 Bad Gateway` right after starting is normal — the backend needs ~30–60 s to load. Try again.

After any change to `.env`:

```bash
docker compose up -d --no-deps backend
```

---

## Part 5 — Public HTTPS address for the backend ✅ done

```bash
docker run -d --name tunnel --restart unless-stopped --network host \
  cloudflare/cloudflared:latest tunnel --no-autoupdate --url http://localhost:80
sleep 20
docker logs tunnel 2>&1 | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' | tail -1
```

Current address: `https://big-acm-saves-mysimon.trycloudflare.com` (changes after a restart).

Test in a browser: `https://<address>/health` → `{"status":"ok"}`.

---

## Part 6 — Frontend on GitHub Pages ⬅ next

On https://github.com/anonymousrepo0806/FAIR-Multi-tool-assessment (logged in as the **anonymous** account):

**6.1 Backend address variable**
Settings → Secrets and variables → Actions → **Variables** tab → New repository variable

- Name: `API_URL`
- Value: `https://big-acm-saves-mysimon.trycloudflare.com` (no trailing slash)

**6.2 Enable Pages**
Settings → Pages → Build and deployment → Source: **GitHub Actions**

**6.3 Add the deploy workflow**
Code → Add file → **Create new file** → name: `.github/workflows/pages.yml` → paste the content of the attached `pages.yml` → **Commit changes**.

**6.4 Wait for the build**
Actions tab → wait for the green ✓ (~2 min).

Live at: **https://anonymousrepo0806.github.io/FAIR-Multi-tool-assessment/**

---

## Part 7 — Test like a reviewer

1. Open the GitHub Pages link in an **incognito** window, on PC and phone.
2. Click every page; run one new assessment.
3. Check that nothing shows your name, unisa, ISISLab, or colleagues' names.

If pages load but show no data → press **F12 → Console**:

| Error | Fix |
|---|---|
| CORS / "blocked by CORS policy" | Check `FRONTEND_ORIGINS=https://anonymousrepo0806.github.io` in `.env`, then `docker compose up -d --no-deps backend` |
| Failed to fetch / 530 / 502 | Backend address changed or backend down → Part 9 |
| 404 on the Pages URL | Settings → Pages source must be **GitHub Actions**; check the Actions run succeeded |

---

## Part 8 — Anonymous code link for the paper

1. https://anonymous.4open.science → log in with the **anonymous** GitHub account.
2. **Anonymize** → choose the repo → terms to hide: `sana`, `latif`, `unisa`, `salerno`, `isislab`.
3. Copy the generated link.

In the paper:

```
Demo: https://anonymousrepo0806.github.io/FAIR-Multi-tool-assessment/
Code: https://anonymous.4open.science/r/<your-id>
```

Optional note: *"The demo may take up to a minute to respond on first use."*

---

## Part 9 — Maintenance during the review period

**Health check** (on the server):

```bash
cd ~/FAIR-Multi-tool-assessment
docker compose ps
curl http://localhost/health
docker logs tunnel 2>&1 | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' | tail -1
```

**After a reboot or resize** — containers restart by themselves, but the tunnel address **changes**:

1. Get the new address (last command above).
2. GitHub → Settings → Secrets and variables → Actions → Variables → edit **`API_URL`**.
3. Actions → **Deploy frontend to GitHub Pages** → **Run workflow**.
4. If GraphDB/Postgres started again: `docker compose stop graphdb postgres`

**After updating code on GitHub:**

```bash
cd ~/FAIR-Multi-tool-assessment
git pull
docker compose build backend frontend
docker compose up -d --no-deps backend frontend
```

(The GitHub Pages frontend rebuilds automatically on every push.)

**Checklist before submitting**

- [ ] VM resized to 2 OCPU / 12 GB
- [ ] `API_URL` updated to the current tunnel address and workflow re-run
- [ ] Frontend tested in incognito, including one live assessment
- [ ] 4open.science link created and checked for identifying text
- [ ] Gemini key in `.env` is a fresh key (old one was pasted in a chat)

**Optional — permanent backend address:** buy a cheap neutral domain, add it to a free Cloudflare account, and use a *named* tunnel instead of the quick tunnel. Then `API_URL` never changes.

**After acceptance:** transfer or recreate the repo under your real account and update the paper links.
#if i change something on github
cd ~/FAIR-Multi-tool-assessment
git pull
docker compose build backend
docker compose up -d --no-deps backend
sleep 45
curl http://localhost/health