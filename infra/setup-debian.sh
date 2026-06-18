#!/bin/bash

# ############################################################################
# Projet : Edge-AI-Education
# Auteur : Barthélémy MENNOCK (GitHub: Supoz9)
# Date   : 18 Juin 2026
# Équipe : Laboratoire CIEL - Lycée Claude Chappe (Arnage)
# Objet  : Automatisation du déploiement IA (Debian 13)
# ############################################################################

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}[1/4] Mise à jour du système Debian 13 (Trixie)...${NC}"
sudo apt update && sudo apt upgrade -y

echo -e "${BLUE}[2/4] Installation des dépendances Docker...${NC}"
sudo apt install -y ca-certificates curl gnupg lsb-release wget
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo -e "${BLUE}[3/4] Ajout du dépôt NVIDIA officiel Debian 13 et installation des pilotes...${NC}"
sudo apt-add-component non-free non-free-firmware -y

# Téléchargement du keyring CUDA ciblant explicitement l'architecture Debian 13
wget https://developer.download.nvidia.com/compute/cuda/repos/debian13/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update

# Installation des pilotes de production et de CUDA
sudo apt install -y nvidia-driver cuda-drivers firmware-misc-nonfree

echo -e "${BLUE}[4/4] Configuration du NVIDIA Container Toolkit pour Docker...${NC}"
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update && sudo apt install -y nvidia-container-toolkit

echo -e "${BLUE}Redémarrage du démon Docker...${NC}"
sudo systemctl restart docker

echo -e "${GREEN}=======================================================${NC}"
echo -e "${GREEN} L'environnement technique Debian 13 est prêt !${NC}"
echo -e "${GREEN} Commande pour lancer la stack : docker compose up -d${NC}"
echo -e "${GREEN}=======================================================${NC}"
