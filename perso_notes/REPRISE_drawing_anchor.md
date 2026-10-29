# Reprise — ancrage des Drawings et correspondance modèle → mise en page

Branche `feature/drawing-anchor-placement` (fork MathiasJon), partie de `upstream/main` 342d952a, le 2026-10-29.
**Ce dossier `perso_notes/` et les deux scripts `Examples/test_drawing_anchor_mapping*.py` sont des notes de travail : supprimer ce commit avant d'ouvrir une PR officielle.**

## But

Bug sur un autre projet : la correspondance entre l'espace modèle et l'espace papier « marche parfois oui, parfois non ».
Objectif : vérifier, de manière systématique (zoom, dézoom, rotation de vue, ancrages, angle, ratio), qu'Archicad sait où il dessine les éléments, et exposer dans Tapir tout ce qu'il faut pour le recalculer.
Règle décidée : les options d'ancrage (`useOwnOrigoAsAnchor`, `anchorPoint`) doivent être proposées dans **toutes** les commandes qui touchent un Drawing.

## Ce qui est fait (commit de code)

- `GetDetailsOfElements` (Drawing) renvoie en plus `useOwnOrigoAsAnchor`, `anchorPoint` et `offset` (lecture seule).
- `SetDetailsOfElements` accepte `useOwnOrigoAsAnchor` et `anchorPoint`.
- `CreateDrawings` accepte `useOwnOrigoAsAnchor` et `anchorPoint` (par défaut : Center comme avant ; useOwnOrigoAsAnchor = valeur par défaut de l'outil Dessin).
- `ChangeDrawingLink` conserve l'ancrage du dessin d'origine.
- Nouvelle définition `DrawingAnchorPoint` dans `CommonSchemaDefinitions.json`.

Compilé et testé en **AC27** seulement (build `-G "Visual Studio 17 2022" -A x64 -T v142 -DAC_VERSION=27`). AC29/AC25 pas encore compilés.

## Résultats mesurés (AC27, TESTAPAPRT27.pln)

Méthode : carrés RGB purs (rouge, vert, bleu) posés à des coordonnées connues dans le modèle, sur un étage vide.
Export de l'image de la mise en page (`SaveCurrentWindowAsImage`, environ 0,75 mm par pixel), puis conversion des pixels en coordonnées papier grâce au cadrage de la fenêtre.
Ce calibrage est vérifié par deux carrés posés directement sur la mise en page (erreur ≈ 1 pixel).
On en déduit l'échelle, l'angle et l'origine réels, qu'on compare aux champs du Drawing.

**Formule validée (résidu < 0,3 mm) :**

    point papier = offset + drawingScale × ratio × R(angle + rotation de la vue source) × point modèle

| Cas | pos | origine du modèle |
|---|---|---|
| découpé (isCutWithFrame) | = origine | = pos = offset |
| non découpé, ancre de boîte | = nœud d'ancre de `bounds` (exact) | = **offset** ≠ pos |
| useOwnOrigoAsAnchor | = origine | = pos = offset (stable si le contenu change) |

- La rotation de la vue (SetViewRotation) s'ajoute exactement à `angle` (30° + 20° → 50,004°). `ratio` 0,5 donne exactement 1:200. Le zoom ne change que le cadre.
- **Cause probable du bug** : `Examples/zone_clip.py` (et sans doute l'autre projet) utilise `pos` et ignore `ratio` et la rotation de vue. C'est juste uniquement pour un dessin découpé, sans rotation.

**Comportements Archicad découverts :**
- `anchorPoint` est ramené à BottomLeft quand `useOwnOrigoAsAnchor` est false, à la création comme via SetDetailsOfElements (la commande répond « success » mais la valeur est ignorée).
- CreateDrawings sans origo : `position` devient le coin bas-gauche du cadre. Avec origo dès la création, `position` est mal interprétée (pos relue = −s·R·position). Mieux vaut créer, puis régler useOwnOrigoAsAnchor, puis pos, chacun dans un appel séparé (c'est ce que fait la phase 2).
- Une vue avec un zoom enregistré (même avec ignoreSavedZoom = true) découpe le dessin au cadre du zoom : isCutWithFrame est true dès la création.
- `GetDrawingContentBoxes` semble renvoyer des coordonnées du modèle, pas de la mise en page.

## Reste à faire

1. Signaler comme un échec un `anchorPoint` ignoré par Archicad, comme c'est fait pour `drawingScale` (comparer après ACAPI_Element_Change).
2. Ajouter à GetDetailsOfElements une transformation « modèle → papier » calculée (origine, échelle, rotation) ; la rotation de vue est à lire sur la vue source (sourceNavigatorItemId de l'arbre LayoutBook + GetViewSettings.rotation).
3. Refaire proprement les tests non concluants :
   - changement de contenu avec une ancre de boîte (l'élément ajouté à (-30,-20) n'apparaissait pas dans `bounds` après UpdateDrawings) ;
   - `modelOffset` (les carrés étaient hors du cadre capturé) ;
   - certains scénarios de la phase 2 étaient pollués : ne garder que les mesures nettes (résidu faible, échelle 1:100,0).
4. Corriger `zone_clip.py` et l'autre projet : utiliser `offset`, `ratio` et la rotation de la vue.
5. Compiler AC29 (+ AC25), puis documenter les champs dans le schéma et la doc, et ouvrir une PR.
6. Idée en attente : une commande `CopyDrawingsToLayout` (copier un dessin vers une autre mise en page avec tous ses réglages ; n'existe pas, l'API n'a pas de presse-papiers). Rappel : créer un favori depuis un Drawing échoue toujours (issue #652).

## Relancer les tests

Archicad 27 ouvert sur un projet de test, avec l'add-on de cette branche chargé depuis `Documents\TapirDev\AC27`. Trouver le port avec API.GetProductInfo (plusieurs Archicad peuvent tourner en même temps) :

    cd archicad-addon/Examples
    uv run --with pillow --with numpy python test_drawing_anchor_mapping.py --port <port>
    uv run --with pillow --with numpy python test_drawing_anchor_mapping_phase2.py --port <port>

Le test crée l'étage `TAPIR_ANCHOR_TEST`, des vues `TAPIR_ANCHOR_*`, une mise en page et des dessins. Fermer ensuite le projet **sans enregistrer**.
Les images et `results*.json` sont écrits dans `%TEMP%\tapir_anchor_test`.
