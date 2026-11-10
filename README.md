# PS Buttons pour Hookshot

Mod pour **The Legend of Zelda: Ocarina of Time** (remake Switch 2) joué sur PC avec **Hookshot** :
les icônes de boutons Nintendo sont remplacées par celles d'une **manette PlayStation**, dans le style graphique du jeu.

> 🇬🇧 *PlayStation button prompts for Ocarina of Time (Switch 2) on Hookshot. Unzip into `Hookshot\mods\` and keep
> the default "Nintendo" layout preset. Requires game update 2.0.0.*

![Icônes : originales en haut, mod au milieu, textures en bas](docs/icones.png)

## Ce qui change

| Dans le jeu | Avant | Avec le mod |
|---|---|---|
| Invites à l'écran (« Ⓐ Parler », menus, textes) | Ⓐ Ⓑ Ⓧ Ⓨ | ○ ✕ △ □ |
| Gâchettes | L, R, ZL, ZR | L1, R1, L2, R2 |
| Boutons + et − | + / − | Options (☰) / Create |
| Notes d'ocarina | A, B, X, Y | ○, ✕, △, □ |
| Écran « Commandes » | manette Switch Pro | manette de style DualSense |

Les icônes gardent le style d'origine : mêmes pastilles et étiquettes, même épaisseur de trait que les lettres du jeu,
en blanc et noir.

![Écran Commandes avec la manette de style DualSense](docs/commandes.png)

## Prérequis

- **Hookshot** (testé avec la version 2.0.10) et le jeu en **mise à jour 2.0.0**.
- Une manette PlayStation (DualShock 4 ou DualSense) : Hookshot la gère déjà, le mod ne change que l'affichage.

## Installation

1. Télécharge le mod : bouton vert **Code → Download ZIP** sur cette page.
2. Ouvre ton dossier Hookshot (celui qui contient `romfs` et `hookshot.exe`) et crée un dossier `mods` s'il n'existe pas.
3. Décompresse le ZIP **dans `mods`**. Tu dois obtenir exactement :

   ```
   Hookshot\
   └── mods\
       └── ps_button-hookshot-main\
           └── romfs\
               ├── Font2\Scalable\External.Nin_Ounce_NVN2.bfotf.zs
               ├── System\Resource\ResourceSizeTable.Product.111.Nin_Ounce_NVN2.rsizetable.zs
               └── UI\Layout2Archive\Common.Product.100.Nin_Ounce_NVN2.bntx.zs
   ```

   Le nom du dossier (`ps_button-hookshot-main`) n'a pas d'importance. Ce qui compte, c'est que `romfs` soit
   directement dedans, et pas un niveau plus bas.
4. Lance le jeu.

### Vérifier que le mod est chargé

Dans `Hookshot\hookshot_log.txt`, tu dois trouver une ligne de ce genre :

```
mods: ps_button-hookshot-main: 3 RomFS files
```

### Désactiver ou désinstaller

- **Désactiver** : renomme le dossier du mod en le faisant commencer par `_` (ex. `_ps_button-hookshot-main`).
  Hookshot ignore les dossiers qui commencent par `_` ou `-`.
- **Désinstaller** : supprime le dossier.

## Réglage important : disposition « Nintendo »

Le mod place ○ sur le bouton de **droite** et ✕ sur le bouton du **bas**, comme sur une vraie manette PlayStation.
Garde donc le préréglage par défaut de Hookshot :

**Menu Hookshot → Controls → Layout preset → Nintendo**

Avec ce réglage, le bouton qui valide est ○ (bouton de droite). Si tu passes sur « Xbox / PC » ou « Swap Face », ✕ devient le bouton qui valide et les icônes ○ / ✕ affichées seront
inversées par rapport à ta manette.

Pour ouvrir le menu Hookshot : **Insert** ou **F1** au clavier, ou le bouton **PS** (ou **Share + Options**) sur la manette.

## Comment ça marche

Hookshot charge tout dossier `mods\<nom>\romfs\…` par-dessus les fichiers du jeu, sans les modifier. Le mod remplace
3 fichiers :

| Fichier | Contenu | Ce que le mod y change |
|---|---|---|
| `Font2/Scalable/External…bfotf.zs` | police d'icônes utilisée dans les textes et les invites | glyphes Ⓐ Ⓑ Ⓧ Ⓨ, L/R/ZL/ZR, + et − redessinés |
| `UI/Layout2Archive/Common…bntx.zs` | textures de l'interface | icônes de boutons des textes, notes d'ocarina, dessin et traits de l'écran « Commandes » |
| `System/Resource/ResourceSizeTable…rsizetable.zs` | table des tailles des fichiers du jeu | taille de la police agrandie (elle pèse 1 Ko de plus) |

Quelques détails techniques, pour les curieux et les moddeurs :

- **Police** : les polices `.bfotf` sont des polices OpenType chiffrées par un simple XOR (clé `a6 01 85 02`, après un
  en-tête de 8 octets). Les glyphes sont redessinés dans le même fichier, aux mêmes codes (E040–E04C).
- **Textures** : format BNTX de la Switch 2, avec le rangement de pixels de la Tegra X1 **dont les bits 5 et 6 de
  l'adresse sont échangés**. Les icônes sont en BC4 ou ASTC, réencodées au même format et à la même taille.
- **Table des tailles** : le jeu réserve la mémoire de chaque fichier d'après cette table. Comme la police grossit, son
  entrée est agrandie. Cette table est compressée en zstd **sans dictionnaire**, car le jeu la lit avant d'avoir chargé
  ses dictionnaires : la compresser avec un dictionnaire fait planter le jeu au démarrage.
- **Écran « Commandes »** : la manette dessinée est un dessin original inspiré de la DualSense, pas l'image officielle
  de Sony. Les traits qui relient les libellés aux boutons sont redessinés quand un bouton a changé de place
  (croix, stick gauche, Create, Options).

## Limites connues

- Les icônes de joystick (L et R ronds de « Se déplacer » / « Caméra ») ne changent pas.
- Les notes L et R de l'ocarina gardent L et R.
- Le bouton PS de l'écran « Commandes » est un simple rond (pas de logo PlayStation).
- Seule la version « manette Pro » de l'écran « Commandes » est modifiée. Une manette PlayStation est vue comme une
  manette Pro, donc c'est celle que tu verras.

## Compatibilité avec d'autres mods

Un autre mod qui remplace l'un des 3 fichiers ci-dessus entrera en conflit avec celui-ci (celui chargé en dernier
l'emporte). C'est surtout le cas de la table des tailles, que beaucoup de mods modifient. Hookshot charge les mods par
ordre alphabétique : nomme les dossiers `01-…`, `02-…` pour choisir l'ordre.

## Crédits

Mod réalisé par **TELOS**.

*Projet de fan, non affilié à Nintendo ni à Sony. Il te faut ta propre copie du jeu.*
