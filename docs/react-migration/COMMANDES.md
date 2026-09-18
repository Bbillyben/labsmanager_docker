# Commandes operateur

## Lot 0 - Analyse et documentation initiales

### VM de developpement

Aucune action requise.

### Packages Python

Aucune action requise.

### Packages npm

Aucune action requise.

### Base de donnees

Aucune action requise.

### Build frontend

Aucune action requise.

### Docker / distribution

Aucune action requise.

## Lot 1 - Stabilisation documentaire de la structure Git

### VM de developpement

Aucune action requise.

### Packages Python

Aucune action requise.

### Packages npm

Aucune action requise.

### Base de donnees

Aucune action requise.

### Build frontend

Aucune action requise.

### Docker / distribution

Aucune action requise.

## Lot 2 - Adaptation Docker au sous-module backend

### VM de developpement

Aucune action requise.

### Packages Python

Aucune action requise.

### Packages npm

Aucune action requise.

### Base de donnees

Aucune action requise.

### Build frontend

Aucune action requise.

### Docker / distribution

Apres recuperation du changement sur l'hote de distribution :

```bash
git submodule update --init --recursive
docker compose build lab-server lab-worker
docker compose up -d lab-server lab-worker lab-proxy
```
