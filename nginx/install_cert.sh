#!/bin/bash

# nstall acme.sh
curl https://get.acme.sh | sh
source ~/.bashrc

~/.acme.sh/acme.sh --set-default-ca --server letsencrypt

~/.acme.sh/acme.sh --issue --dns -d xxxxxxx.com -d www.xxxxxxx.com --yes-I-know-dns-manual-mode-enough-go-ahead-please

# MANUAL STEP: Add txt records on DNS.
# Verify witht dig TXT _acme-challenge.investandgorget.com
# Verificar con: dig TXT _acme-challenge.xxxxxxx.com
echo -e "Now go and mofify DNS records!"
read -p "Press enter to continue..."

# 4. Finish verification
~/.acme.sh/acme.sh --renew -d xxxxxxx.com -d www.xxxxxxx.com --yes-I-know-dns-manual-mode-enough-go-ahead-please

# 5. Instalar certificado en directorio accesible para nginx
local cert_dir=~./certs
mkdir -p  $cert_dir

~/.acme.sh/acme.sh --install-cert -d xxxxxxx.com \
  --cert-file ${cert_dir}/cert.pem \
  --key-file ${cert_dir}/key.pem \
  --fullchain-file ${cert_dir}/fullchain.pem
