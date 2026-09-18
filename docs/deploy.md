# Deploy — VM dos painéis

| | |
|---|---|
| Público | `https://painel.cenarios.unb.br/cenarios/hansepe/` |
| Direto, por VPN | `http://10.20.10.64:8510/cenarios/hansepe/` |
| Pasta na VM | `~/hansepe` |
| Dados | volume de `~/dashboard-sinan-pe/data` — a mesma extração do painel nacional; nada é copiado |

```bash
ssh cenarios-vm 'cd ~/hansepe && git pull && docker compose up -d --build'
```

Localmente, com a junção `data -> ../sinan/data`:

```bash
SINAN_DATA_DIR=./data docker compose up -d --build
```

No Git Bash, `-v /app/data` vira `C:/Program Files/Git/app/data` e o volume
não monta — o container fica `healthy` com `FileNotFoundError` na página.
Rode com `MSYS_NO_PATHCONV=1`, ou pelo PowerShell.

```bash
```

## O bloco do nginx

A acrescentar em `/etc/nginx/sites-enabled/telessaude`, junto dos outros
`location`. **Sem barra final** nos dois lados — o Streamlit roda com
`--server.baseUrlPath=cenarios/hansepe` e espera o prefixo.

```nginx
    location /cenarios/hansepe {
        proxy_pass         http://localhost:8510;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection $connection_upgrade;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## Depois de todo deploy

O healthcheck não sabe se a aplicação funciona — `/_stcore/health` responde
mesmo com o script quebrado. Abra a página e confira um número conhecido:
**PE 2025, taxa de detecção 24,64 e 2.356 casos novos**.
