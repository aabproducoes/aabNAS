# NAS Media Explorer

Site estático para GitHub Pages + API somente de leitura no ASUSTOR.

## O que faz
- Lista pastas e arquivos de imagem/vídeo.
- Abre imagens e reproduz vídeos no navegador.
- Pesquisa por nome e filtra imagens/vídeos.
- Não oferece upload, exclusão, renomeação ou edição.

## 1. Publicar o site
1. Crie um repositório no GitHub chamado `NAS-Media-Explorer`.
2. Envie `index.html`, `style.css`, `config.js` e `app.js` para a raiz do repositório.
3. Em Settings > Pages, escolha `Deploy from a branch`, branch `main`, pasta `/root`.
4. Edite `config.js` e troque `API_BASE` pelo endereço HTTPS do seu ASUSTOR na sua rede Tailscale.

## 2. Preparar o ASUSTOR
É necessário ter Python 3 e pip disponíveis no NAS (ou executar o servidor em um container).
Copie a pasta `nas-server` para o NAS e instale as dependências:

    python3 -m pip install -r requirements.txt

Defina `NAS_MEDIA_ROOT` para a pasta que contém sua mídia. Exemplo (confirme o caminho real no ADM):

    export NAS_MEDIA_ROOT="/share/Media"
    export ALLOWED_ORIGIN="https://SEU-USUARIO.github.io"
    python3 server.py

O servidor escuta somente em `127.0.0.1:8765`, não diretamente na rede.

## 3. Acesso remoto seguro com Tailscale
Instale e conecte o Tailscale no NAS e nos dispositivos que usarão o site.
Com o Tailscale ativo no NAS, configure o Tailscale Serve para encaminhar HTTPS para a porta local 8765. O comando exato depende da versão do Tailscale/ADM; normalmente:

    tailscale serve --bg 8765

Use o nome HTTPS mostrado pelo Tailscale como `API_BASE` em `config.js`.
Mantenha as regras de acesso do tailnet restritas aos seus próprios dispositivos/usuários. Não configure Funnel nem encaminhamento de porta no roteador para esta API.

**Importante:** como o navegador acessa o NAS diretamente, o dispositivo que abre o GitHub Pages também precisa estar conectado ao Tailscale para visualizar a mídia fora da rede local.

## Observações
- `NAS_MEDIA_ROOT` deve apontar para a pasta compartilhada correta do seu ADM.
- `ALLOWED_ORIGIN` deve ser a origem exata do seu GitHub Pages, sem barra no final, por exemplo `https://seu-usuario.github.io`.
- CORS não é autenticação. A proteção de acesso remoto é feita pelo Tailscale e pelas regras do tailnet.
- Os navegadores não reproduzem todos os formatos. MP4 com vídeo H.264 e áudio AAC costuma ter melhor compatibilidade; MKV/AVI podem não tocar em alguns navegadores.
- Não exponha a porta 8765 diretamente à internet.
