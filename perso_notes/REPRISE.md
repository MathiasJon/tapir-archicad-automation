# Reprise : version perso complète de Tapir

Branche `perso/complete`, sur le fork MathiasJon uniquement. Rien n'a été poussé sur ENZYME-APD depuis cette branche.
État au 2026-10-22.

## Contenu de la branche

Base : `upstream/main` @ `ebf2685b` (2026-10-21).

On y a fusionné :
- **Mes PR** : #1398 (modification partielle Composite / Layer Combination), #1399 (ModifyGraphicOverrideCombinations + CreateGraphicOverrideRuleGroups), #1052 (`feature/graphic-overrides-fields`), #995 (`fix/section-elevation-commands`).
- **Les PR revues, avec mes correctifs** (commit `899a9b03`) : #953, #1024, #1026 (dossiers d'attributs), #916 (ActivateLayerCombination), #1333 + #1365 (propriétés des attributs), #1178 (ordre des groupes de règles).
- **Les PR « prêtes »** : #1121, #1354, #1374, #1008, #1009, #1221, #1347, #997, #1075, #1176.

**Conflits résolus à la main** : #995, #1121, #1354, #1374, #1009, #997, #1176. Pour chacun, j'ai vérifié que les lignes ajoutées par la PR sont toutes présentes.

**Seule concession** : pour #997 (creationInfo), les sorties Grasshopper et la vérification de l'exemple `get_attributes_by_type.py` ne sont pas reprises. Elles entraient en conflit avec `folderPath`. Le C++ de #997, lui, est bien intégré.

## Ce qui reste à faire

1. **Compiler.** La dernière tentative échouait sur 3 `);` manquants dans `AddOnMain.cpp`, après les registrations de MoveAttributesAndFolders, ActivateLayerCombination et SetGraphicOverrideRuleOrder. C'est corrigé dans ce commit mais **pas recompilé**. D'autres erreurs peuvent apparaître.

   ```
   cd archicad-addon
   cmake -S . -B Build_AC29 -G "Visual Studio 17 2022" -A x64 -DAC_API_DEVKIT_DIR="<DevKit29>/Support" -DAC_VERSION=29 -DAPI_AC_VERSION=29
   cmake --build Build_AC29 --config RelWithDebInfo
   ```

   Pour AC25 et AC27, ajouter `-T v142` à la commande cmake, sinon on obtient l'erreur « VC++ 2019 v142 toolset is required ».
2. **Déployer.** Copier l'APX dans `Documents\TapirDev\ACxx`, Archicad fermé. Il faut fermer avec la commande Tapir `QuitArchicad` : un kill laisse un `.lck` et déclenche des dialogues de récupération.
3. **Tester en live** avec les scripts de `perso_notes/tests/` :
   - `test_partial_composite_layercomb.py` : #1398, 27/27 sur la branche seule.
   - `test_override_modify_create.py` : #1399, 24/24.
   - `test_maintainer_review.py` : dossiers, Activate, ordre des groupes, propriétés. 34/35 sur la branche de revue ; l'échec restant est une attente du test devenue obsolète avec le correctif #1178.
   - `run_goldens.py` + `click_open.ps1` : exécute les exemples sur une copie fraîche de `Test/TestProject.pla` et les compare aux goldens sans les réécrire. Le dialogue « Ouvrir TestProject.pla » est cliqué automatiquement.

   Les chemins en dur dans ces scripts (scratchpad, worktrees) sont à adapter sur l'autre poste.

## Revue mainteneur (commentaires postés le 2026-10-22)

Le texte exact de chaque commentaire est dans `review_comments/`, et les correctifs, un par PR, dans `review_patches/`. Chaque patch s'applique proprement sur la branche de sa PR.

| PR | Verdict |
|---|---|
| #953 | Bug : `ACAPI_Attribute_CreateFolder` est in/out, donc seul le premier niveau était créé. Correctif : un seul appel sur une copie du dossier. |
| #1024 | OK. Version 1.7.3 et rebase à faire. |
| #1026 | Bug : le chemin contenait le nom localisé du dossier racine (« Calques »). Correctif : partir d'un chemin racine vide. Les goldens sont à réenregistrer. |
| #1029 | OK. À fusionner après #953 et #1024. |
| #916 | Bug : un guid de calque était accepté. Correctif : relire l'attribut comme layer combination et comparer les guids. |
| #1365 | OK sur les 3 étapes. Undo non vérifié, description à corriger. |
| #1178 | Bug : le groupe built-in RENOVATION ne peut pas être déplacé. Correctif : les groupes built-in gardent leur place. |

#953, #1024 et #916 sont encore enregistrées en 1.7.2, qui est déjà sortie ; elles devraient être en 1.7.3.

## Faits Archicad vérifiés en live (AC29, interface FR)

- Le dossier racine d'un type d'attribut a pour path son **nom localisé**, et tous les paths de sous-dossiers commencent par ce nom. En entrée, `GetFolder` et `Move` attendent le path **sans** ce préfixe.
- `ACAPI_Attribute_Get` par guid peut renvoyer un attribut d'**un autre type**. Il faut toujours revérifier le type.
- Pour savoir si un groupe de règles est built-in : appeler `ChangeOverrideRuleGroup` en lui redonnant son propre nom. L'appel échoue avec `APIERR_NOACCESSRIGHT` uniquement pour un groupe built-in.
- `Test/TestProject.pla` contient déjà des dossiers d'attributs imbriqués.
- Un Ctrl+Z simulé (keybd_event) n'annule rien. L'Undo n'est donc pas testable automatiquement de cette manière.
