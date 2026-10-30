# Hardening HTTP Headers su Cloudflare (Guida Operativa)

Questa guida illustra la configurazione raccomandata su **Cloudflare** (disponibile nel piano Free) per aggiungere gli header HTTP nativi di sicurezza che **GitHub Pages** non permette di impostare a livello di web server.

---

## 1. Configurazione tramite Cloudflare Transform Rules

1. Accedi alla dashboard di **Cloudflare** e seleziona il tuo dominio.
2. Nel menu laterale, vai su **Rules** → **Transform Rules**.
3. Seleziona la scheda **Modify Response Header** e clicca su **Create rule**.
4. Assegna un nome alla regola: `Security Headers - Hardening A+`.
5. In **When incoming requests match...**, seleziona:
   - **All incoming requests**
6. Nella sezione **Modify response headers**, aggiungi i seguenti header (azione: *Set dynamic* o *Set static* come indicato):

| Header Name | Type | Value | Scopo / Mitigazione |
| :--- | :--- | :--- | :--- |
| `X-Content-Type-Options` | Static | `nosniff` | Blocca attacchi MIME-sniffing / confusion |
| `X-Frame-Options` | Static | `SAMEORIGIN` | Previene il Clickjacking / UI Redressing a livello HTTP |
| `Referrer-Policy` | Static | `strict-origin-when-cross-origin` | Tutela la privacy dell'utente sui link esterni |
| `Permissions-Policy` | Static | `camera=(), microphone=(), geolocation=(), payment=()` | Disabilita API hardware del browser non utilizzate |
| `Strict-Transport-Security` | Static | `max-age=63072000; includeSubDomains; preload` | Forza HTTPS per 2 anni e abilita l'inclusione nella preload list HSTS |
| `Cross-Origin-Opener-Policy` | Static | `same-origin` | Isola il contesto di navigazione da attacchi Spectre/XS-Leaks |

7. Clicca su **Deploy**.

---

## 2. Verifica del Risultato

Dopo il deploy della regola, verifica la corretta ricezione degli header con il comando:
```bash
curl -I https://tuodominio.it/
```
Oppure analizza il sito su:
- [SecurityHeaders.com](https://securityheaders.com/) (Punteggio atteso: **A+**)
- [Mozilla Observatory](https://observatory.mozilla.org/)

