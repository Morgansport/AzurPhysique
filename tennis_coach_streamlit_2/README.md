# Tennis Coach Dashboard — version Streamlit éditable

## Ce qui fonctionne

- Photo, prénom, nom, club et saison de l'entraîneur, modifiables par le bouton « ✏️ Modifier le coach » sur l’accueil ou dans « Gestion et joueurs ».
- Ajout / modification de joueurs, âge, catégorie.
- Présences sur huit semaines (cases à cocher), calcul du taux de participation.
- Saisie du CMJ daté, graphique d'évolution.
- Trois indices sur 100, dont les noms peuvent être personnalisés.
- Interface responsive pensée pour téléphone.
- Consultation publique facultative ; mode édition protégé par mot de passe si paramétré.

## Pour tester sur ton Mac

```bash
pip install -r requirements.txt
streamlit run app.py
```

Sans base de données configurée, les modifications sont limitées à la session Streamlit : **elles ne sont pas visibles pour d'autres visiteurs et ne sont pas persistantes**.

## Publier et obtenir un vrai lien à partager

1. Crée un dépôt GitHub (privé possible), et importe `app.py`, `requirements.txt`, `supabase_setup.sql` et le README. **Ne publie pas de fichier contenant tes secrets.**
2. Crée un projet sur [Supabase](https://supabase.com/). Dans SQL Editor, exécute `supabase_setup.sql`.
3. Dans les paramètres Supabase, relève l'URL du projet et la clé `service_role` / clé serveur secrète. **Ne la colle jamais dans GitHub ou le code.**
4. Va sur [Streamlit Community Cloud](https://share.streamlit.io/), connecte ton GitHub, clique « Create app », sélectionne ton dépôt et `app.py` comme fichier principal.
5. Avant de partager, ouvre les paramètres de l'application Streamlit → « Secrets » et renseigne les champs de `.streamlit/secrets.toml.example` avec tes propres valeurs. La clé de Supabase reste côté serveur. Pour un vrai groupe de mineurs, configure aussi `VIEW_PASSWORD`.
6. Déploie l'application. Streamlit t'attribuera une URL du type `https://nom-de-ton-app.streamlit.app` — son adresse exacte ne peut être connue qu'après publication.
7. Dans la barre latérale, active le mode édition via `EDIT_PASSWORD`, renseigne ton profil et tes joueurs ; clique « Enregistrer ». Un visiteur ouvrant le lien verra alors ces données (mot de passe de lecture requis si configuré).

## Sécurité / limites de la démo

- Il s'agit d'un **prototype**, pas d'un service conforme pour des données réelles d'enfants. Utiliser des joueurs fictifs pour la présentation au directeur sportif.
- Un mot de passe partagé n'est pas une authentification nominative : avant le déploiement réel, prévoir comptes individuels et droits d'accès.
- Les modifications sont persistantes sur Supabase, mais l'application garde un instantané en mémoire de session : le lecteur peut recharger la page, ou utiliser « Actualiser les données », pour retrouver les dernières modifications.
- L'édition simultanée par plusieurs entraîneurs n'est pas encore gérée (dernier enregistrement gagnant).
- Les présences de huit semaines sont un exemple ; une vraie saison demandera des séances datées et un historique illimité.
- La photo du coach est sauvegardée en base sous forme encodée, limitée à 1 Mo.
- Une application SwiftUI iOS pourra ensuite réutiliser le modèle de données, mais nécessitera une authentification et une API sécurisée.

## Mise à jour V3 bleu Azur

- Remplacer `tennis_coach_streamlit/app.py` et ajouter `tennis_coach_streamlit/.streamlit/config.toml` dans GitHub.
- Dans Streamlit Community Cloud, le déploiement se réactualise après le commit.
- Le thème est clair avec texte bleu-noir sur fond clair et bannière bleu Azur.
- Sans Supabase, les modifications restent propres à chaque session et ne sont pas partagées avec le directeur sportif.
