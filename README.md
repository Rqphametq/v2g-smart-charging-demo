# ⚡ Démonstrateur Smart Charging & V2G pour Flottes Professionnelles

## 🌍 Contexte & Enjeux
L'électrification massive des flottes d'entreprise soulève de nouveaux défis majeurs pour les opérateurs :
* **Contrainte Réseau :** Le retour simultané des utilitaires en fin de journée (17h-19h) crée un pic de consommation massif, nécessitant souvent des augmentations coûteuses de l'abonnement électrique (dépassement de puissance souscrite).
* **Volatilité des Prix (Marché Spot) :** Sur le marché Day-Ahead (ex: ENTSO-E), le prix de l'électricité varie fortement selon les heures. Charger "à l'aveugle" en début de soirée revient à payer l'énergie au prix le plus fort.
* **Potentiel de Stockage Dormant :** Une flotte de 20 utilitaires représente une immense batterie sur roues (plus de 1 MWh). Lorsqu'ils sont stationnés, ces véhicules peuvent devenir des actifs de flexibilité au service du réseau électrique.

## 🚀 Avantages Stratégiques de l'Outil
Ce démonstrateur prouve la faisabilité technique et la viabilité économique d'un pilotage intelligent (Smart Charging & V2G). Ses avantages sont triples :
1. **Réduction drastique du TCO (Total Cost of Ownership) :** Le décalage de la charge (*Load-Shifting*) vers les heures creuses nocturnes permet de diviser la facture énergétique par 2 ou 3.
2. **Génération de Nouveaux Revenus :** Grâce au Vehicle-to-Grid (V2G), les véhicules injectent de l'énergie sur le réseau lors des pics de prix et d'émissions carbone, transformant un centre de coût en centre de profit.
3. **Optimisation d'Infrastructure :** L'outil lisse l'appel de puissance du site (*Peak Shaving*), évitant le renforcement physique du raccordement au réseau Enedis et limitant les pénalités de dépassement.

---

## 🧠 Fonctionnement et Logique Mathématique

Ce démonstrateur ne repose pas sur des règles empiriques (if/else), mais sur un véritable solveur de **Recherche Opérationnelle (Google OR-Tools / Programmation Linéaire Mixte en Nombres Entiers - MILP)**. Il modélise le site et les véhicules sous forme d'équations physiques et financières pour trouver la solution mathématique optimale.

### 🛡️ Contraintes dures respectées par le modèle :
* **Service Opérationnel Garanti :** Aucun véhicule ne part le matin en tournée sans avoir atteint sa cible de charge stricte (ex: 85% ou 95%). Le besoin métier reste toujours prioritaire sur l'arbitrage financier.
* **Protection des Batteries :** L'algorithme intègre une pénalité financière d'usure de la batterie (en €/kWh déchargé). Il refuse d'activer le V2G si les gains sur le marché ne couvrent pas au moins cette usure et les pertes de l'onduleur (rendement de 92%). Il s'interdit aussi de descendre sous les 20% d'état de charge en stationnement.
* **Bilan de Puissance :** La puissance totale appelée par le site est strictement bridée.
* **Autoconsommation Maximisée :** Si des ombrières solaires sont présentes, le modèle synchronisera naturellement la charge avec l'ensoleillement (énergie locale perçue comme un coût nul).

### 📊 Scénario de Référence (ASAP)
Pour objectiver les gains, l'outil calcule une facture "Baseline". Celle-ci simule un comportement "Non piloté" classique (As Soon As Possible) : chaque véhicule se branche à pleine puissance dès son arrivée, sans aucune considération pour le signal de prix ou l'état du réseau.