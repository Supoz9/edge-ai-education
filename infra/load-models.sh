#!/bin/bash

# ############################################################################
# Projet : Edge-AI-Education
# Fichier: load-models.sh (Chargement et configuration interactive des modèles)
# Auteur : Barthélémy MENNOCK (GitHub: Supoz9)
# Date   : 18 Juin 2026
# Équipe : Laboratoire CIEL - Lycée Claude Chappe (Arnage)
# ############################################################################

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo -e "${BLUE}=======================================================${NC}"
echo -e "${BLUE}    Configuration et Chargement des Modèles d'IA       ${NC}"
echo -e "${BLUE}=======================================================${NC}"
echo ""
echo "Sélectionnez la configuration de votre serveur (VRAM disponible) :"
echo "1) Moins de 12 Go VRAM (Frugal : Modèles 7B)"
echo "2) Entre 12 Go et 24 Go VRAM (Intermédiaire : Modèles 12B/14B)"
echo "3) Plus de 24 Go VRAM (Confort - Config Labo Chappe : Modèles complets simultanés)"
echo ""
read -p "Votre choix (1, 2 ou 3) : " CONFIG_CHOICE

case $CONFIG_CHOICE in
    1)
        JARVIS_BASE="mistral"
        ADA_BASE="qwen2.5-coder:7b"
        WILLIAM_BASE="qwen2.5:7b"
        echo -e "${YELLOW} Option Frugale sélectionnée (Modèles 7B).${NC}"
        ;;
    2)
        JARVIS_BASE="mistral-nemo"
        ADA_BASE="qwen2.5-coder:14b"
        WILLIAM_BASE="qwen2.5:14b"
        echo -e "${YELLOW} Option Intermédiaire sélectionnée (Modèles 12B/14B).${NC}"
        ;;
    3)
        JARVIS_BASE="mistral-nemo"
        ADA_BASE="qwen2.5-coder:14b"
        WILLIAM_BASE="qwen2.5:14b"
        echo -e "${YELLOW} Option Confort sélectionnée (Idéal pour Rig Multi-GPU).${NC}"
        ;;
    *)
        echo "Choix invalide. Sortie du script."
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}[1/3] Téléchargement des modèles de base dans Docker...${NC}"
docker exec -it ollama-server ollama pull $JARVIS_BASE
docker exec -it ollama-server ollama pull $ADA_BASE
docker exec -it ollama-server ollama pull $WILLIAM_BASE

echo ""
echo -e "${BLUE}[2/3] Génération des tuteurs maïeutiques personnalisés...${NC}"

# Injection et création des modèles personnalisés à partir des Modelfiles locaux
echo "Création de Jarvis..."
docker exec -i ollama-server ollama create jarvis -f - < ../agents/Jarvis.modelfile

echo "Création d'Ada..."
docker exec -i ollama-server ollama create ada -f - < ../agents/Ada.modelfile

echo "Création de William..."
docker exec -i ollama-server ollama create william -f - < ../agents/William.modelfile

echo ""
echo -e "${GREEN}[3/3] Opération terminée avec succès !${NC}"
echo -e "${GREEN}Vos 3 agents (jarvis, ada, william) sont prêts dans Ollama.${NC}"
echo -e "${GREEN}Ils sont désormais visibles dans votre interface Open WebUI !${NC}"
echo -e "${GREEN}=======================================================${NC}"
