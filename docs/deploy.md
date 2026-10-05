# Publicação e operação

Procedimentos de publicação do painel na VM e de atualização dos dados.

| | |
|---|---|
| Endereço público | <https://painel.cenarios.unb.br/cenarios/hansepe/> |
| Acesso direto | porta 8510 na VM dos painéis, por VPN (`ssh cenarios-vm`) |
| Pasta na VM | `~/hansepe` |
| Dados | volume em `~/hansepe/data`, cerca de 47 MB, gerado na própria VM |

## Publicar uma nova versão

```bash
ssh cenarios-vm 'cd ~/hansepe && git pull && docker compose up -d --build'
```

## Atualizar os dados

A pasta `data/` é uma cópia da extração do painel nacional, e não acompanha
a origem automaticamente. Quando o lago for atualizado, regere antes de
subir:

```bash
ssh cenarios-vm 'cd ~/hansepe && python3 -m scripts.extrair_dados_hanseniase --origem ~/dashboard-sinan-pe/data && docker compose up -d'
```

O mesmo vale em ambiente local, onde a origem padrão é `../sinan/data`:

```bash
python -m scripts.extrair_dados_hanseniase
docker compose up -d --build
```

No Windows, executando pelo Git Bash, o caminho `-v /app/data` é convertido
para `C:/Program Files/Git/app/data` e o volume não monta. O container sobe
como saudável, mas a página falha ao ler os arquivos. Use
`MSYS_NO_PATHCONV=1` ou execute pelo PowerShell.

## Configuração do nginx

O bloco abaixo vai em `/etc/nginx/sites-enabled/telessaude`, junto dos
demais `location`. Os dois lados ficam sem barra final: o Streamlit roda com
`--server.baseUrlPath=cenarios/hansepe` e espera exatamente esse prefixo.

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

## Verificação após a publicação

O healthcheck não é suficiente. O endereço `/_stcore/health` responde mesmo
quando a aplicação falha ao montar a página, porque verifica apenas se o
servidor está de pé.

Abra o painel e confira dois valores conhecidos. Pernambuco em 2024, que é o
ano de abertura, deve apresentar **taxa de detecção de 18,46** e **1.761
casos novos**.
