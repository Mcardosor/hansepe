# Deploy — VM dos painéis

| | |
|---|---|
| Público | `https://painel.cenarios.unb.br/cenarios/hansepe/` |
| Direto, por VPN | porta 8510 na VM dos painéis (`ssh cenarios-vm`) |
| Pasta na VM | `~/hansepe` |
| Dados | volume de `~/hansepe/data` — só hanseníase, 44 MB, gerado na VM por `python3 -m scripts.extrair_dados_hanseniase --origem ~/dashboard-sinan-pe/data` |

```bash
ssh cenarios-vm 'cd ~/hansepe && git pull && docker compose up -d --build'
```

Quando o lago do painel nacional for atualizado, os dados daqui **não**
acompanham sozinhos — é preciso regerar antes de subir:

```bash
ssh cenarios-vm 'cd ~/hansepe && python3 -m scripts.extrair_dados_hanseniase --origem ~/dashboard-sinan-pe/data && docker compose up -d'
```

Localmente vale o mesmo, com o padrão `../sinan/data`:

```bash
python -m scripts.extrair_dados_hanseniase
docker compose up -d --build
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
