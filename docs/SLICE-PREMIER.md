# TORNE — Premier vertical slice

**Proposition — 31 octobre 2026**
**Statut : proposition argumentée. Elle attend la décision du propriétaire.**

## 1. La décision proposée

**Le premier vertical slice est le Mississippi (système fluvial intérieur américain), pas le Rhin.**

Ce n'est pas un choix d'intérêt : c'est le choix que dicte le critère le plus rare — **la disponibilité d'un témoin
économique public, à fréquence infra-mensuelle, sur toute la période d'étude**.

## 2. Pourquoi le Rhin ne peut pas être le premier slice

Le Rhin est le meilleur terrain d'intégration *technique* du paquet de référence : sources publiques, historique de
plusieurs décennies, références indépendantes (PEGEL, EWL), et un modèle de référence physique déjà spécifié. Mais
l'audit du catalogue de sources et du plan d'essai établit ceci :

- Tous les témoins économiques à fréquence infra-mensuelle sur le Rhin sont **commerciaux** : fret PJK, stocks ARA.
- Les seuls témoins publics sont **annuels ou trimestriels** (CCNR Market Observation) ou **mensuels** (Destatis).
- Or l'expérience à mesurer est un **décalage entre le fait physique, la décision publique et le témoin économique** —
  typiquement de quelques semaines à quelques mois.

**Un témoin trimestriel ne date pas un décalage de quelques semaines.** Il produit un intervalle de censure qui
contient probablement tout l'effet recherché. Concrètement : le slice Rhin, tel que spécifié, ne peut pas produire
la seule métrique qui le justifierait.

Les trois issues possibles sont donc : acheter un témoin commercial (coût récurrent, dépendance, et la mission
interdit les coûts non documentés), ou dégrader la revendication économique à une description rétrospective de
volumes (auquel cas le slice ne démontre pas la chaîne World-to-Market, seulement World Intelligence), ou choisir un
terrain qui n'a pas le problème.

## 3. Pourquoi le Mississippi passe le critère

| Critère (MISSION §8) | Mississippi | Rhin |
|---|---|---|
| Disponibilité des données | USGS (jauges, débits, révisions horodatées), USACE (écluses, tonnages, saison de navigation) | PEGEL, EWL, DWD, Copernicus — excellent aussi |
| Qualité de l'historique | decades, avec révisions **horodatées** (la preuve point-in-time est constructible) | decades, historique plus fin mais révisions moins tracées |
| Droits d'accès et de conservation | **public, gratuit, réutilisation explicitement permise** (USDA/AMS : « non-confidential and non-copyrighted sources ») | public également |
| Reconstruction historique possible | oui | oui |
| Références indépendantes | oui (USGS ≠ USACE ≠ USDA) | oui (PEGEL ≠ EWL) |
| Conséquence physique mesurable | jauge, stage, débit | jauge, tirant d'eau, tirant d'air |
| Conséquence opérationnelle mesurable | **fermetures d'écluses, tonnages hebdomadaires par écluses, saison de navigation** | tirant d'eau navigable, adaptations de barge |
| **Conséquence économique mesurable** | **taux de fret fluvial aval (percent-of-tariff) HEBDOMADAIRE, 2004 → aujourd'hui, 7 tronçons, gratuit** ; plus les prix agricoles USDA | **commercial** en infra-mensuel ; public en annuel/trimestriel/mensuel seulement |
| Existence d'une décision publique datée | fermetures d'écluses et restrictions de navigation annoncées par l'USACE | décisions de saisonnalité commerciale (festivals), EWL, CCNR |
| Difficulté d'implémentation | moyenne | moyenne |
| Valeur de connaissance | forte | forte |
| Application financière ultérieure | plausible | plausible |

**Le fait décisif, vérifié :** l'USDA Agricultural Marketing Service publie et met à jour chaque semaine les
**Downbound Grain Barge Rates** pour sept tronçons du Mississippi (Twin Cities, Mid-Mississippi, Illinois River,
St. Louis, Cincinnati, Lower Ohio, Cairo-Memphis), sous forme de taux « percent-of-tariff » rapportés au barème de
1976, **depuis 2004**, avec un accès OData direct. Le même producteur publie les **tonnages hebdomadaires** de grains
par écluses, à partir des données USACE (Lock Performance Monitoring System et Waterborne Commerce Statistics).

C'est exactement la chaîne que la thèse décrit : **un phénomène physique (le niveau, le débit), une contrainte
opérationnelle (l'éclusable, le tirant d'eau), une conséquence économique (le fret), et une décision publique
datée** (fermeture, restriction, ouverture de saison).

## 4. Ce que le slice démontre — et ce qu'il ne démontre pas

Le slice doit démontrer un chemin complet :

```
Source réelle
    ↓
Observation exploitable
    ↓
Variable ou estimation construite
    ↓
Produit de connaissance
    ↓
Évaluation reproductible
```

Concrètement, sur le Mississippi :

1. **Source réelle** : jauge USGS (niveau, débit, datum, révisions horodatées) ; tonnages hebdomadaires par
   écluses (USACE via USDA) ; taux de fret hebdomadaire (USDA/AMS) ; décisions de navigation datées (USACE).
2. **Observation exploitable** : une série de niveau et de débit reconstituée **point-in-time**, chaque valeur
   portant sa date de révision et la preuve de sa disponibilité à l'époque.
3. **Variable ou estimation construite** : une grandeur dérivée de type « navigabilité contrainte » — par exemple
   l'ensemble des fenêtres où le débit observé rendait une classe de barge inaccessible — **calculée au moment où la
   décision a été prise**, jamais recalculée après coup.
4. **Produit de connaissance** : un état de navigabilité reconstitué, versionné, avec son lignage complet
   (source, snapshot, transformation, horodatage de chaque étape).
5. **Évaluation reproductible** : un juge. L'e-processus et l'e-LOND d'`athanor.stats` sont disponibles et testés ;
   le juge doit ici être **physique** (J1–J2 : fidélité de reconstitution, compétence événementielle), pas financier.

**Ce que le slice ne démontre pas, et ne doit pas prétendre :**

- Aucune performance financière. Le produit de connaissance n'est pas encore consommé par une application de marché.
- Aucune causalité démontrée entre niveau et fret : on mesure un **décalage observé**, pas une chaîne causale.
- Aucun claim de type « BORÉE prédit le fret ». Le premier slice doit d'abord être **honnête sur ce qu'il ne
  prouve pas** — c'est la condition pour que le reste tienne.

## 5. Critères de succès — et ce qui ferait échouer le slice

Le slice réussit si, à la fin :

1. Une période de **cinq ans au moins** de niveau, débit, tonnage et fret est reconstituée **point-in-time**, avec
   les révisions USGS rejouées dans leur état d'origine et une empreinte du store vérifiable.
2. Le **décalage observé** entre contrainte physique et témoin économique est mesuré, avec son intervalle de
   censure, sur des épisodes 독립 identifiés **avant** de regarder le témoin.
3. Le juge physique est **exécuté** et rend un verdict, y compris un verdict négatif ou « pas de puissance ».
4. Chaque résultat est reproductible par une tierce personne à partir de l'empreinte du store et du commit du code.
5. Le catalogue de sources est **complet pour ce bassin** : le catalogue de référence du paquet V2.0 est borné au
   Rhin et **ne contient aucune source du Mississippi** — c'est le premier travail à faire.

Le slice échoue, et il faut le dire, si : la reconstruction point-in-time des révisions USGS s'avère impossible à
prouver ; si le décalage mesuré tombe dans l'intervalle de censure du témoin ; si la puissance est insuffisante pour
distinguer l'effet du bruit ; ou si le juge rend « pas de conclusion » — ce qui reste un résultat valide.

## 6. Le Rhin n'est pas abandonné

Le Rhin reste le **deuxième slice**, et il reste le meilleur terrain pour la reconstitution physique fine
(tirant d'eau, tirant d'air, adaptation de barge) et pour la question des **adjudications** — les releases de l'EWL
sont le contre-exemple documenté d'une décision dont la justification est elle-même un enjeu. Il reste aussi le
terrain naturel du volet financier européen.

Ce qui manque au Rhin, c'est un témoin économique public infra-mensuel. Cette question est ouverte et mérite son
propre document plutôt qu'un contournement dans le slice.

## 7. Ce qu'il faut avant de commencer

1. **Décision du propriétaire** sur le bassin (cette proposition est une recommandation, pas un fait acquis).
2. **Licence Athanor** : sans elle, le juge et le magasin brut ne sont pas reprenables (`docs/REUSE_AUDIT.md` §6).
3. **Catalogue des sources du Mississippi** : USGS, USACE, USDA/AMS, avec pour chacun l'historique de publication,
   la politique de révision et la preuve de disponibilité historique.
4. **Un pré-enregistré rempli** : le gabarit `protocol/PREREGISTRATION-TEMPLATE.md` du paquet de référence, avec les
   seuils, le juge, la population d'épisodes et la condition de kill — **avant** le premier calcul.
5. **Le store synthétique anti-fuite** : chaque valeur encode sa date, et le réalisé interdit vaut −1.
6. **La procédure de calcul de `usable_at`** : c'est la décision qui manque le plus, et elle bloque tout le reste.

## 8. Sources citées

- USDA Agricultural Marketing Service — *Downbound Grain Barge Rates* (hebdomadaire depuis 2004, sept tronçons du
  Mississippi), via Open Ag Transport Data : https://agtransport.usda.gov/Barge/Downbound-Grain-Barge-Rates/deqi-uken/data
- USDA AMS — *Grain Transportation Report* (tableaux 9 et 10 : taux de fret hebdomadaires, tonnages par écluses) :
  https://www.ams.usda.gov/services/transportation-analysis/gtr-datasets
- Paquet de référence conceptuelle V2.0 : `docs/03-INITIAL-SOURCE-CATALOGUE.md`, `docs/06-PUBLIC-DECISION-GAP-TRIAL-PLAN.md`,
  `docs/02-DATA-LAKE-AND-PHYSICAL-RECONSTRUCTION.md`, `docs/04-OPERATING-PLAN-AND-BUDGET.md`.

## 9. Ce que la qualification des sources a changé

La mission P1 (`docs/MISSISSIPPI_DATA_SOURCES.md`, 920 lignes, neuf sources vérifiées sur requêtes réelles) confirme le
choix du bassin et durcit la proposition. Cinq points changent la façon dont le slice doit être écrit.

**1. Le jeu de données minimal existe et il est borné.** Six sources, fenêtre commune **2004-01-07 → 2026-10-27**
(22 ans), trois stations USGS vérifiées comme porteuses de séries quotidiennes (St. Paul 1892, Chester 1942, Thebes
1933), plus deux séries USDA de prix et une de volumes. La fenêtre commence exactement au premier point des séries de
prix : aucune troncature n'est nécessaire.

**2. Il y a un piège d'identification, et il est structurel.** Les taux d'amont manquent en hiver — 729 des 774
absences sont des fermetures sur Twin Cities et Mid-Mississippi. Or c'est cette absence qui fait monter le prix en
aval : « l'amont a été fermé » ne peut pas servir de variable explicative quand l'indicateur de prix amont est
lui-même manquant **par construction**. L'identification devra reposer sur des variations intra-amont ou sur des
comparaisons entre semaines, jamais sur la présence/absence seule. C'est le point à écrire dans le pré-enregistré.

**3. L'alignement naïf sur la date produirait un résultat faux.** L'hydrologie est publiée à J+1, le prix de la
semaine à J+4 environ, les volumes à J+5 : le décalage de publication de 4 à 5 jours est structurel. Il doit être
modélisé, pas absorbé par un alignement sur `date`. Les deux séries USDA n'ont d'ailleurs pas la même fin de semaine :
les taux sont datés **mardi**, les mouvements **samedi**.

**4. Deux séries de prix coexistent, et le choix n'est pas neutre.** `deqi-uken` donne sept zones en pourcentage du
barème de 1976 ; `7spn-fbua` donne 26 tronçons **déjà en dollars par tonne**. La réconciliation est exacte pour 24
tronçons sur 26 testés ; deux résistent (Desoto Landing–Hurricane Point, Letsworth–Greenville) et attendent le
fichier « Rate Data by Segment ». Recommandation de P1 : `7spn-fbua` en série de référence, `deqi-uken` en complément.

**5. Une question bloquante reste ouverte, et elle n'est pas technique.** La valeur `rate` est un **moyennage sur un
nombre de jours qui n'est documenté nulle part** : les dénominateurs 3, 7, 16 et 28 observés dans les valeurs le
laissent deviner, mais c'est une déduction. Sans la confirmation écrite d'USDA/AMS, on risque de modéliser un
artefact de moyenne. Cette question passe **avant** l'écriture du moindre connecteur.

S'y ajoutent trois ruptures méthodologiques relevées par P1 (granularité des taux, convention de fin de semaine,
périodes manquantes) et treize vérifications impossibles à mener depuis ce poste, listées dans le rapport de P1.

