# TORNE — Architecture

**Quatre frontières, responsabilités transversales — 31 octobre 2026**
**Statut : vue de responsabilité. Ce document ne décrit aucune implémentation : le dépôt ne
contient à ce jour aucun modèle, aucun service, aucun registre.**

## 1. Le modèle mental

```text
SOURCES
   ↓
MODÈLES
   ↓
PRODUITS DE CONNAISSANCE
   ↓
APPLICATIONS

PROVENANCE · TEMPORALITÉ · INCERTITUDE · VALIDATION   (transversales)
```

Quatre concepts suffisent. Les modèles physiques, opérationnels, économiques et financiers sont
des **familles de modèles spécialisées et composables**, pas des étapes successives obligatoires :
il n'existe aucune chaîne universelle, et un modèle peut consommer directement des sources ou
bien des produits d'autres modèles.

Les frontières sont **logiques**. Elles n'impliquent ni microservices, ni déploiement séparé, ni
bus d'événements, ni exécution strictement linéaire.

## 2. Frontière 1 — Sources

**Question :** d'où viennent les informations, et sous quelles conditions étaient-elles
disponibles ?

**Responsabilité :** identifier le producteur d'une information, acquérir le contenu brut, le
conserver, le dater, le versionner, le normaliser, et en qualifier la disponibilité. Une source
est un producteur ou un détenteur d'information ; une observation est une donnée se rapportant à
un état ou un événement du monde.

**Ce que cette frontière garantit :**

- la version exacte de la donnée est identifiable et reproductible ;
- la date de validité, la date de publication et la date de disponibilité sont distinguées ;
- l'identité, les unités et les références spatiales sont portées par la donnée, pas par la
  mémoire du code ;
- la révision d'une donnée est visible et n'est jamais présentée comme si elle était disponible à
  l'époque.

**Ce qu'elle ne fait pas :** elle ne déduit rien. Une source ne produit pas de connaissance ; elle
fournit la matière dont la connaissance est dérivée.

**Point d'attention :** les règles temporelles du protocole scellé Borée H3 sont hors périmètre et
ne sont pas reprises ici. TORNE définira ses propres conventions temporelles, en s'appuyant sur la
distinction canonique entre temps de validité, temps de publication, temps de réception, temps de
disponibilité et temps d'usage.

## 3. Frontière 2 — Modèles

**Question :** quelle question scientifique ou opérationnelle traitons-nous ?

**Responsabilité :** transformer des entrées en résultats selon une méthode et des hypothèses
explicites. Un modèle possède une question précise, un domaine, des entrées, une sortie, des
hypothèses et des limites déclarées.

**Ce que cette frontière garantit :**

- un résultat porte toujours la mention de ce qu'il est : état reconstruit, estimation,
  prévision, simulation, variable dérivée, contrainte, mécanisme ou conséquence économique ;
- les hypothèses sont écrites, pas implicites ;
- le domaine de validité est dit ;
- l'incertitude est qualifiée selon ce qui est réellement connu.

**Ce qu'elle ne fait pas :** elle ne transforme pas une estimation en observation, ni une
simulation en fait. Un modèle n'est pas un moteur par le fait de contenir plusieurs étapes ; un
moteur est un regroupement fonctionnel, et son existence doit être justifiée par une
responsabilité distincte et une raison opérationnelle démontrée.

## 4. Frontière 3 — Produits de connaissance

**Question :** quel résultat réutilisable publions-nous ?

**Responsabilité :** produire des résultats versionnés et documentés, destinés à être consommés
par une application ou à être audités. Un produit est un état, une estimation, une prévision, une
simulation, une contrainte, un mécanisme ou une conséquence économique.

**Ce que cette frontière garantit :**

- une version, une date d'étatisation et une provenance ;
- une incertitude et un domaine de validité ;
- le lien vers les sources, transformations, modèles et paramètres qui l'ont produite ;
- un statut de validité explicite : utilisable, dégradé, retiré, ou résultat inconclusif.

**Ce qu'elle ne fait pas :** elle n'est pas un registre. Un produit n'est publié que s'il doit
être réutilisé, audité ou consommé indépendamment ; les intermédiaires internes restent internes.
Aucun index, catalogue ou registre n'est créé dans le dépôt tant qu'un besoin réel ne le
justifie.

## 5. Frontière 4 — Applications

**Question :** quelle décision ou quelle compréhension ce résultat permet-il ?

**Responsabilité :** consommer des produits de connaissance pour produire une compréhension, une
alerte, une cartographie, une analyse d'exposition ou une hypothèse de recherche. L'intelligence
financière est une application parmi d'autres, et non la propriétaire du socle.

**Ce que cette frontière garantit :**

- l'application ne modifie pas les produits qu'elle consomme ;
- l'usage déclaré : quel résultat, pour quelle décision, sous quelles conditions ;
- l'échec d'une application ne remet pas en cause les produits valides.

**Ce qu'elle ne fait pas :** elle ne décide pas de la validité d'un modèle. Une application qui
réussit ne valide pas rétroactivement les modèles amont.

## 6. Préoccupations transversales

Les quatre préoccupations suivantes ne sont pas une cinquième frontière ni une couche : elles
s'appliquent à chaque élément du schéma et ne recopient ni les données ni les fonctions.

### 6.1 Provenance

Toute conclusion remonte aux sources, aux versions, aux transformations, aux modèles et aux
paramètres qui l'ont produite. Un résultat sans provenance n'est pas publiable : il n'est ni
reproductible, ni auditable, ni réutilisable.

### 6.2 Temporalité

Une donnée porte plusieurs instants distincts, non interchangeables : celui auquel le fait se
rapporte, celui déclaré par l'émetteur, celui où la version était accessible, celui de sa
réception, celui où elle devient utilisable, et celui de son utilisation. Une version révisée
n'est pas présentée comme étant disponible à l'époque sans preuve. Une donnée absente porte la
raison de son absence ; elle ne porte jamais zéro en guise d'absence.

### 6.3 Incertitude

L'incertitude est décrite selon ce qui est connu : données, paramètres, structure du modèle,
conditions initiales, approximation numérique, scénario. La forme est adaptée à ce qui est
réellement connu : intervalle, distribution, scénarios, borne, sensibilité, ou conclusion
qualitative. Une distribution sophistiquée n'est pas requise si les données ne la justifient pas.
L'inconnu n'est jamais remplacé par zéro, et les sorties dépendantes ne sont pas comptées comme
des confirmations indépendantes.

### 6.4 Validation

La validation est choisie selon l'affirmation testée, jamais appliquée uniformément. Elle est
décrite dans `docs/RESEARCH_AND_VALIDATION.md`. La validation physique, la validation
économique et la validation financière restent distinctes, et un juge qui dépend d'un autre
n'est pas une confirmation indépendante.

## 7. Frontières de responsabilité

| Frontière | Garantit | Ne fait pas |
|---|---|---|
| Sources | Version, date, qualité, provenance de l'information | Ne déduit rien, ne produit pas de connaissance |
| Modèles | Méthode, hypothèses, limites, nature et incertitude du résultat | Ne transforme pas une estimation en observation |
| Produits de connaissance | Version, provenance, domaine de validité, statut | N'est pas un registre, ne catalogue pas l'existant |
| Applications | Usage déclaré et conditions de la décision | Ne valide pas les modèles amont |

Deux règles transversales de non-duplication :

1. Une couche transversale ne recopie ni les données ni les fonctions qu'elle gouverne.
2. Un contrat partagé ne contient que les champs réellement communs ; le détail métier reste
   dans le domaine.

## 8. Ce que cette architecture ne crée pas

Elle ne propose aujourd'hui aucun moteur, aucun service, aucun registre, aucun bus, aucun
graphe, aucun framework de plugins, aucun système de workflow, ni aucun répertoire de packages
prévu pour les contenir. Les frontières décrites sont des responsabilités à remplir par le
code, pas des répertoires à créer.

Une proposition d'architecture nouvelle doit répondre à quatre questions avant d'être acceptée :

1. Quel problème réel ou quelle preuve manquante justifie le changement ?
2. Pourquoi les composants existants ne suffisent-ils pas ?
3. Quel est le plus petit changement qui résout le problème ?
4. Comment saura-t-on qu'il a amélioré le système ?

Sans ces réponses, la proposition reste une hypothèse ou est rejetée.
