# Dev Container Dockerfile baseado em Arch Linux
# Instala Python e ferramentas úteis para desenvolvimento
FROM archlinux:latest

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=1000

# Atualizar e instalar pacotes necessários
RUN pacman -Syu --noconfirm \
    && pacman -S --noconfirm --needed python python-pip base-devel git tcl tk openssh sudo \
    && pacman -Scc --noconfirm

# Criar utilizador não-root (vscode) e dar permissões sudo sem password ao grupo wheel
RUN useradd -m -u ${USER_UID} -G wheel ${USERNAME} \
    && echo "%wheel ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Criar um virtualenv global (opcional) e garantir permissões
RUN python -m venv /opt/venv \
    && chown -R ${USERNAME}:${USERNAME} /opt/venv

ENV PATH="/home/${USERNAME}/.local/bin:/opt/venv/bin:${PATH}"

# Criar directoria de trabalho que será usada pelo Dev Container
RUN mkdir /workspace && chown ${USERNAME}:${USERNAME} /workspace

USER ${USERNAME}
WORKDIR /workspace

# Comando por omissão abre um shell; o VS Code irá sobrepor quando abrir o workspace
CMD ["bash"]
