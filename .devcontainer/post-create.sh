
#!/usr/bin/env bash
set -euo pipefail

# post-create simples para devcontainer
# 1) executa install.sh se existir
# 2) no final, se não houver um virtualenv activo, faz "source venv/bin/activate" se ./venv existir

echo "Running post-create script..."

# Encontrar install.sh preferindo o diretório do workspace atual
if [ -f "./install.sh" ]; then
  INSTALL_SH="./install.sh"
elif [ -f "/workspaces/Projeto-IA/install.sh" ]; then
  INSTALL_SH="/workspaces/Projeto-IA/install.sh"
else
  INSTALL_SH="$(find /workspaces -maxdepth 2 -type f -name install.sh 2>/dev/null | head -n1 || true)"
fi

if [ -n "${INSTALL_SH:-}" ] && [ -f "${INSTALL_SH}" ] && [ -z "${SKIP_INSTALL:-}" ]; then
  echo "Running ${INSTALL_SH}..."
  bash "${INSTALL_SH}"
else
  if [ -n "${INSTALL_SH:-}" ] && [ -f "${INSTALL_SH}" ]; then
    echo "SKIP_INSTALL is set; skipping ${INSTALL_SH}"
  else
    echo "install.sh not found; skipping"
  fi
fi

# No final: se não houver virtualenv activa, e se existir ./venv, ativar com source
if [ -z "${VIRTUAL_ENV:-}" ]; then
  if [ -d "./venv" ] && [ -f "./venv/bin/activate" ]; then
    echo "No active virtualenv detected. Activating ./venv..."
    # shellcheck source=/dev/null
    source ./venv/bin/activate
  else
    echo "No active virtualenv and ./venv not found; not activating."
  fi
else
  echo "Virtualenv already active: ${VIRTUAL_ENV}. Nothing to do."
fi

echo "post-create completed"
