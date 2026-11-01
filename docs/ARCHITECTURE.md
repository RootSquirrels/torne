# TORNE — Architecture

**Frontières, responsabilités et couches**
**Statut : vue de responsabilité.** Ce document ne décrit pas d'implémentation : il fixe **où passe chaque
responsabilité**, pas comment elle est rendue. Le code en est une application, pas la source : quand les deux
divergent, c'est le document qui a tort, et il est corrigé.

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

### 1.1 Trois niveaux, séparés par des contrats explicites

Au-dessus des quatre frontières, le dépôt distingue trois **niveaux** de responsabilité, qui ne se mélangent
jamais dans un même module :

| Niveau | Ce qu'il contient | Ce qu'il ne contient pas |
|---|---|---|
| **Socle transversal** | acquisition, transport, conservation de la preuve, contrats de données, exécution, empreinte | aucune connaissance du domaine : ni débit, ni hauteur d'eau, ni série temporelle |
| **Couche sémantique** | ce qui donne un sens métier aux objets du socle : observation, grandeur dérivée, produit de connaissance | aucun accès direct au réseau ni au magasin brut |
| **Couche scientifique** | les méthodes : régression, rupture, puissance, filtrage d'état, comparaison à une référence | aucune écriture, aucun accès réseau |

La séparation n'est pas cosmétique : c'est elle qui permet d'ajouter une méthode sans toucher au socle, et
d'ajouter une source sans réécrire une méthode. Un adaptateur de source ne sait rien du domaine — il construit
une URL et dit comment la source se parcourt ; un modèle ne sait rien du réseau.

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

**Les quatre règles que l'acquisition doit tenir.** C'est là que l'erreur est la plus facile à commettre et la
plus difficile à voir : on peut croire avoir obtenu la chose demandée sans l'avoir obtenue. Chaque règle est un
invariant vérifiable (`docs/CONTRATS_FONDAMENTAUX.md` §4.8 et §4.9) :

- **La présence de données brutes ne vaut pas conformité sémantique.** Un adaptateur vérifie, sur les lignes
  réellement reçues, que les identifiants demandés sont ceux qui reviennent ; il ne suppose pas que le
  fournisseur a obéi. **L'écho d'un filtre dans l'URL n'est pas une preuve de filtrage** : un fournisseur
  peut accepter le filtre, le renvoyer dans ses liens, et l'ignorer dans la population qu'il rend.
- **Le prédicat est propre à la source ; le socle ne fait qu'orchestrer.** Le socle ne connaît ni les
  identifiants de stations, ni les unités, ni les règles du domaine : il enregistre le verdict, il ne le
  décide pas. Et les **prédicats de transférabilité** (`docs/RESEARCH_AND_VALIDATION.md` §12) ne sont pas
  concernés ici : ils relèvent du contrat de validation des affirmations, pas de l'acquisition.
- **L'exhaustivité est qualifiée par source.** Une réponse HTTP réussie ne prouve pas que le fournisseur a
  rendu toutes les observations attendues : soit la source le dit, soit elle ne le dit pas, et le parcours peut
  être tronqué par notre propre budget.
- **Une erreur d'adaptateur est un résultat, pas une exception.** Une réponse malformée produit une issue
  structurée — `failed` ou `partial` — et la tentative est consignée comme toute autre.
- **Un secret ne circule que par référence.** Ce qui est consigné — journal, manifeste, empreinte — porte une
  référence d'identifiant, jamais la valeur ; et un identifiant ne franchit pas une redirection qui change de
  serveur, de port ou de schéma.

**Deux axes, et une seule porte.** La conformité a son **propre** axe et son **propre** verdict ; le statut
d'acquisition ne parle que de l'acquisition — la réponse est-elle arrivée, la page a-t-elle été conservée ?
— et ne dit rien de la conformité de la réponse à la question posée. Une source qui renvoie les lignes
d'une autre station **ne crée aucune observation** : la porte est `exploitable`, et c'est elle, et elle
seule, qui décide de l'usage. Ce n'est pas un échec d'acquisition : la réponse est bien arrivée, bien
conservée, bien empreintée — une réponse non conforme est une preuve, et elle est d'autant plus utile
qu'on sait qu'elle ne convient pas. Un verdict sans motif n'est pas accepté.

**Point d'attention :** les règles temporelles du protocole scellé de l'ancien projet électrique sont hors
périmètre et ne sont pas reprises ici. TORNE a défini ses propres conventions temporelles, en s'appuyant sur la
distinction canonique entre temps de validité, temps de publication, temps de réception, temps de
disponibilité et temps d'usage (`docs/CONTRATS_FONDAMENTAUX.md` §3.1).

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

**Cette frontière n'est pas ouverte.** La branche « world-to-market » — transformer une intelligence du monde
physique en décision financière — est **reportée** tant que le socle d'intelligence physique n'est pas
suffisamment mature. Le report est délibéré, et il découle de la règle ci-dessus : une application financière
qui réussit ne valide pas rétroactivement les modèles physiques amont, et elle n'a rien à dire de leur justesse.
Elle s'ouvrira quand les produits de connaissance qu'elle consomme seront eux-mêmes validés.

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

Deux règles complètent cette liste, et elles ont bite sur ce que le dépôt a accepté de contenir :

- **Une responsabilité, une implémentation.** Le dépôt n'héberge jamais deux briques de la même responsabilité,
  et toute brique reprise d'un dépôt d'origine est classée avant d'entrer — REUSE, ADAPT, REIMPLEMENT ou
  REJECT — avec son origine déclarée en tête de module. La règle, ses conditions et ce qui a été repris sont
  dans `docs/CONTRATS_FONDAMENTAUX.md` §5.
- **Aucune dépendance runtime sans import réel.** Une dépendance qui n'est jamais importée n'est pas une
  dépendance : elle ne figure ni dans `pyproject.toml`, ni dans le verrou.
- **Aucun modèle générique remplacé par son état de l'art.** Un modèle n'entre pas parce qu'il a été qualifié
  ailleurs, mais parce que les données disponibles et la grandeur à reconstruire le demandent.
- **Aucune bibliothèque de modèles d'un domaine avant que ce domaine ait un premier problème.**
- **Aucun framework bayésien global, aucun moteur de validation, de simulation ou de sélection** : ces
  briques ne sont justifiées par aucun besoin concret démontré (`docs/PROGRAMME.md` §9).

Une proposition d'architecture nouvelle doit répondre à quatre questions avant d'être acceptée :

1. Quel problème réel ou quelle preuve manquante justifie le changement ?
2. Pourquoi les composants existants ne suffisent-ils pas ?
3. Quel est le plus petit changement qui résout le problème ?
4. Comment saura-t-on qu'il a amélioré le système ?

Sans ces réponses, la proposition reste une hypothèse ou est rejetée.
