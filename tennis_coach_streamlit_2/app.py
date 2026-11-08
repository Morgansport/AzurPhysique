"""Azur Physique — interface bleue, gestion simple des coachs et joueurs."""
import base64
import copy
import hmac
import uuid
from datetime import date

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Azur Physique · Tennis", page_icon="🎾", layout="centered", initial_sidebar_state="collapsed")
st.markdown('''<style>
:root{color-scheme:light}
html,body,[data-testid="stApp"],[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:#F4F8FD!important;color:#11243A!important}
.block-container{max-width:920px;padding-top:1.2rem;padding-bottom:4rem}
[data-testid="stHeader"]{background:#F4F8FD!important}
[data-testid="stSidebar"]{background:#EAF3FC!important}
h1,h2,h3,h4,h5,p,label,small,[data-testid="stMarkdownContainer"],[data-testid="stCaptionContainer"],[data-testid="stWidgetLabel"],[data-testid="stMetricLabel"],[data-testid="stMetricValue"]{color:#102033!important}
[data-testid="stMetric"]{background:#fff;border:1px solid #CBDEEE;border-radius:15px;padding:12px}
[data-testid="stTabs"] button{color:#183959!important}
[data-testid="stTabs"] button[aria-selected="true"]{color:#0756A8!important;border-bottom-color:#0756A8!important}
[data-testid="stTextInput"] input,[data-testid="stNumberInput"] input,[data-testid="stDateInput"] input,div[data-baseweb="select"]>div{background:#fff!important;color:#102033!important}
.stButton button[kind="primary"],button[data-testid="stBaseButton-primary"],[data-testid="stFormSubmitButton"] button{background:#0756A8!important;border-color:#0756A8!important;color:#fff!important}
.stButton button[kind="primary"] *,[data-testid="stFormSubmitButton"] button *{color:#fff!important}
.stButton button[kind="secondary"]{background:#fff!important;color:#0756A8!important;border:1px solid #8FB4DA!important}
.stButton button[kind="secondary"] *{color:#0756A8!important}
.hero{border-radius:22px;background:linear-gradient(120deg,#073D79,#0874C3);padding:24px;margin:14px 0 18px;box-shadow:0 8px 22px #063F7820}
.hero h2,.hero p,.hero small{color:#fff!important}.hero p{opacity:.95}
.coach-note{font-size:.85rem;color:#526A83}
@media(max-width:640px){.block-container{padding-left:.75rem;padding-right:.75rem}.hero{padding:18px}}
</style>''', unsafe_allow_html=True)

EMPTY_DATA = {
    "schema_version": 5,
    "club": "Azur Tennis Club d’Asnières",
    "season": "2026–2027",
    "coaches": [],
    "indices_names": ["Régularité", "Précision", "Intensité"],
    "players": [],
}

def get_secret(name):
    try:
        return str(st.secrets.get(name, ""))
    except (FileNotFoundError, KeyError):
        return ""

SUPA_URL=get_secret("SUPABASE_URL").rstrip("/")
SUPA_KEY=get_secret("SUPABASE_SERVICE_ROLE_KEY")
REMOTE=bool(SUPA_URL and SUPA_KEY)
SECRET_WARNING = ""
if not REMOTE:
    if SUPA_URL and get_secret("SUPABASE_KEY") and not SUPA_KEY:
        SECRET_WARNING = ("Tu as renseigné SUPABASE_KEY, mais le code attend "
                          "SUPABASE_SERVICE_ROLE_KEY. Renomme cette entrée dans "
                          "Streamlit → Manage app → Settings → Secrets (avec la clé serveur).")
    elif SUPA_URL and not SUPA_KEY:
        SECRET_WARNING = "Il manque SUPABASE_SERVICE_ROLE_KEY dans les Secrets Streamlit."
    elif SUPA_KEY and not SUPA_URL:
        SECRET_WARNING = "Il manque SUPABASE_URL dans les Secrets Streamlit."
    else:
        SECRET_WARNING = "Les Secrets Supabase ne sont pas configurés pour cette application."
API=f"{SUPA_URL}/rest/v1/tennis_dashboard_state"
HEADERS={"apikey":SUPA_KEY,"Authorization":f"Bearer {SUPA_KEY}","Content-Type":"application/json","Prefer":"resolution=merge-duplicates,return=minimal"}

def migrate(raw):
    """Conserve les éventuelles données déjà enregistrées lors d'une mise à jour."""
    data=copy.deepcopy(raw if isinstance(raw,dict) else EMPTY_DATA)
    if "coaches" not in data:
        old=data.pop("coach", {})
        data["coaches"]=[{"id":"c1","first_name":old.get("first_name",""),"last_name":old.get("last_name",""),"photo":old.get("photo","")}] if old.get("first_name", "").strip() else []
        data.setdefault("club",old.get("club",EMPTY_DATA["club"]))
        data.setdefault("season",old.get("season",EMPTY_DATA["season"]))
        for p in data.get("players",[]): p.setdefault("coach_id","c1")
    data.setdefault("club",EMPTY_DATA["club"])
    data.setdefault("season",EMPTY_DATA["season"])
    data.setdefault("indices_names",EMPTY_DATA["indices_names"])
    data.setdefault("coaches",[])
    data.setdefault("players",[])
    for p in data["players"]:
        p.setdefault("coach_id",None)
        p.setdefault("goals",[])
        p.setdefault("presence",[])
        p.setdefault("cmj",[])
        p.setdefault("indices",[0,0,0])
    data["schema_version"]=5
    return data

def load_remote():
    r=requests.get(API,headers=HEADERS,params={"id":"eq.main","select":"content"},timeout=12)
    r.raise_for_status()
    entries=r.json()
    return migrate(entries[0]["content"] if entries else EMPTY_DATA)

def save_remote(data):
    r=requests.post(API,headers=HEADERS,json={"id":"main","content":data},timeout=12)
    r.raise_for_status()

# Réinitialise la connexion si les paramètres changent entre deux sessions Streamlit.
BACKEND_ID = (SUPA_URL, bool(SUPA_KEY))
if "data" not in st.session_state or st.session_state.get("backend_id") != BACKEND_ID:
    try:
        st.session_state.data = load_remote() if REMOTE else migrate(EMPTY_DATA)
        st.session_state.backend_id = BACKEND_ID
    except requests.RequestException as e:
        st.error(f"Impossible de charger les données : {e}")
        st.stop()

view_pwd=get_secret("VIEW_PASSWORD")
edit_pwd=get_secret("EDIT_PASSWORD")
if "view_ok" not in st.session_state: st.session_state.view_ok=not bool(view_pwd)
if not st.session_state.view_ok:
    st.title("🎾 Azur Physique")
    with st.form("viewer_login"):
        password=st.text_input("Code d’accès",type="password")
        if st.form_submit_button("Entrer"):
            if hmac.compare_digest(password,view_pwd):
                st.session_state.view_ok=True
                st.rerun()
            else: st.error("Code incorrect")
    st.stop()
if "editor" not in st.session_state: st.session_state.editor=False
with st.sidebar:
    st.title("🎾 Azur Physique")
    if edit_pwd:
        if not st.session_state.editor:
            with st.form("editor_login"):
                password=st.text_input("Mot de passe modification",type="password")
                if st.form_submit_button("Activer les modifications"):
                    if hmac.compare_digest(password,edit_pwd):
                        st.session_state.editor=True
                        st.rerun()
                    else: st.error("Mot de passe incorrect")
        else:
            st.success("Mode modification actif")
            if st.button("Verrouiller les modifications"):
                st.session_state.editor=False
                st.rerun()
    else:
        st.session_state.editor=True
        st.warning("Aucun mot de passe édition : toute personne ayant accès à l’application peut modifier les fiches. Configure EDIT_PASSWORD avant le partage.")
    if REMOTE:
        st.success("Supabase configuré — stockage distant disponible")
        if st.button("🔎 Vérifier la connexion à la base"):
            try:
                response = requests.get(API, headers=HEADERS,
                                        params={"id":"eq.main","select":"id,updated_at"}, timeout=12)
                response.raise_for_status()
                rows = response.json()
                if rows:
                    st.success("Connexion OK : une sauvegarde existe dans Supabase.")
                    st.caption("Dernière sauvegarde : " + str(rows[0].get("updated_at", "inconnue")))
                else:
                    st.warning("Connexion OK, mais aucune sauvegarde n'existe encore dans cette table. Ajoute ou modifie un coach en mode édition pour enregistrer les données.")
            except requests.RequestException as exc:
                st.error(f"Connexion Supabase en échec : {exc}")
        if st.button("🔄 Recharger depuis Supabase"):
            try:
                st.session_state.data=load_remote()
                st.rerun()
            except requests.RequestException as exc:
                st.error(f"Impossible de recharger : {exc}")
    else:
        st.error("Sauvegarde distante désactivée : " + SECRET_WARNING)
        st.warning("Les modifications restent uniquement dans la session Streamlit et peuvent disparaître.")
    st.caption("Ne pas saisir de données réelles de mineurs avant sécurisation des accès.")

if not REMOTE:
    st.warning("⚠️ Aucune sauvegarde permanente n’est active. " + SECRET_WARNING)

def commit(updated):
    if not st.session_state.editor:
        st.error("Active le mode modification dans le menu ☰.")
        return
    updated=migrate(updated)
    if REMOTE:
        try: save_remote(updated)
        except requests.RequestException as e:
            st.error(f"Sauvegarde impossible : {e}")
            return
    st.session_state.data=updated
    st.rerun()

def name(record): return (record.get("first_name","")+" "+record.get("last_name","")).strip()
def coach_name(id_,coaches): return next((name(c) for c in coaches if c["id"]==id_),"Non attribué")
def percent(p):
    v=p.get("presence",[])
    return round(100*sum(v)/len(v)) if v else 0

def cmj(p):
    h=p.get("cmj",[])
    return sorted(h,key=lambda x:x["date"])[-1]["value"] if h else None

def edit_record(data,section,record_id): return next(x for x in data[section] if x["id"]==record_id)
def uploaded_photo(file):
    if file is None: return None
    if file.size>1024*1024:
        st.error("La photo doit faire moins de 1 Mo")
        return False
    return base64.b64encode(file.getvalue()).decode("ascii")


D=st.session_state.data
coaches=D["coaches"]
players=D["players"]
st.caption("AZUR TENNIS CLUB D’ASNIÈRES · PRÉPARATION PHYSIQUE")
st.title("Azur · Tableau de bord")
if coaches:
    coach_options={c["id"]:name(c) for c in coaches}
    selected_coach=st.selectbox("Entraîneur",list(coach_options),format_func=lambda i:coach_options[i],key="selected_coach")
    active_coach=next(c for c in coaches if c["id"]==selected_coach)
    left,right=st.columns([1,4],vertical_alignment="center")
    with left:
        if active_coach.get("photo"):
            try: st.image(base64.b64decode(active_coach["photo"]),width=94)
            except (ValueError,TypeError): st.markdown("## 👨‍🏫")
        else: st.markdown("## 👨‍🏫")
    with right:
        st.subheader(f"Bonjour, {active_coach['first_name']} 👋")
        st.caption(f"{D['club']} · Saison {D['season']}")
    with st.popover("✏️ Modifier cet entraîneur", use_container_width=True):
        if not st.session_state.editor:
            st.info("Active le mode modification via le menu ☰.")
        else:
            with st.form(f"quick_coach_{selected_coach}"):
                first=st.text_input("Prénom",value=active_coach["first_name"])
                last=st.text_input("Nom",value=active_coach.get("last_name",""))
                photo=st.file_uploader("Changer la photo (JPG / PNG, 1 Mo maximum)",type=["jpg","jpeg","png"],key=f"quick_photo_{selected_coach}")
                if st.form_submit_button("Enregistrer le coach"):
                    blob=uploaded_photo(photo)
                    if not first.strip(): st.error("Le prénom est obligatoire.")
                    elif blob is not False:
                        updated=copy.deepcopy(D)
                        target=edit_record(updated,"coaches",selected_coach)
                        target.update(first_name=first.strip(),last_name=last.strip())
                        if blob is not None: target["photo"]=blob
                        commit(updated)
    scope=st.radio("Voir les joueurs",["Cet entraîneur","Tous les joueurs"],horizontal=True,label_visibility="collapsed")
    group=[p for p in players if p.get("coach_id")==selected_coach] if scope=="Cet entraîneur" else players
else:
    st.info("Aucun coach enregistré. Ajoute ton premier coach dans Gestion.")
    selected_coach=None
    group=players

st.markdown('<div class="hero"><small>VUE D’ENSEMBLE</small><h2>Suivi de mon groupe 🎾</h2><p>Entraîneurs, joueurs, présences, CMJ et indices tennis.</p></div>',unsafe_allow_html=True)
a,b,c=st.columns(3)
a.metric("Joueurs",len(group))
tracked=[p for p in group if p.get("presence")]
b.metric("Présences",f"{round(sum(percent(p) for p in tracked)/len(tracked))}%" if tracked else "—")
cmjs=[cmj(p) for p in group if cmj(p) is not None]
c.metric("CMJ moyen",f"{sum(cmjs)/len(cmjs):.1f} cm" if cmjs else "—")

tab_players,tab_player,tab_manage=st.tabs(["👥 Joueurs","📈 Fiche joueur","⚙️ Gestion"])
with tab_players:
    query=st.text_input("Rechercher un joueur",placeholder="Prénom ou nom")
    found=[p for p in group if query.lower() in name(p).lower()]
    if not found: st.info("Aucun joueur trouvé.")
    for p in found:
        with st.container(border=True):
            x,y=st.columns([3,1],vertical_alignment="center")
            with x:
                st.markdown(f"**🎾 {name(p)}**")
                st.caption(f"{p.get('category') or 'Catégorie non renseignée'} · {str(p.get('age')) + ' ans' if p.get('age') else 'Âge non renseigné'} · {coach_name(p.get('coach_id'),coaches)}")
                st.caption(f"Présences : {percent(p)} %" if p.get("presence") else "Présences : aucune séance enregistrée")
            with y: st.metric("CMJ",f"{cmj(p)} cm" if cmj(p) is not None else "—")

with tab_player:
    if players:
        choices={p["id"]:name(p) for p in players}
        default_id=next((p["id"] for p in group),players[0]["id"])
        keys=list(choices)
        chosen=st.selectbox("Fiche du joueur",keys,index=keys.index(default_id),format_func=lambda x:choices[x])
        p=edit_record(D,"players",chosen)
        st.subheader(name(p))
        st.caption(f"{p.get('category','')} · Coach : {coach_name(p.get('coach_id'),coaches)}")
        tatt,tcmj,tindices=st.tabs(["📅 Présences","📊 CMJ","🎾 Tennis"])
        with tatt:
            st.metric("Présences aux séances physiques",f"{percent(p)} %" if p.get("presence") else "—")
            if st.session_state.editor:
                with st.form(f"att_{chosen}"):
                    v=p.get("presence",[])
                    checks=[]
                    for start in range(0,len(v),4):
                        cols=st.columns(4)
                        for offset,col in enumerate(cols):
                            i=start+offset
                            if i<len(v): checks.append(col.checkbox(f"S{i+1}",value=bool(v[i]),key=f"att_{chosen}_{i}"))
                    save=st.form_submit_button("Enregistrer les présences")
                    if save:
                        updated=copy.deepcopy(D)
                        edit_record(updated,"players",chosen)["presence"]=checks
                        commit(updated)
                if st.button("➕ Ajouter une semaine",key=f"week_add_{chosen}"):
                    updated=copy.deepcopy(D)
                    edit_record(updated,"players",chosen)["presence"].append(False)
                    commit(updated)
            else:
                st.write(" · ".join(f"S{i+1}: {'✓' if v else '—'}" for i,v in enumerate(p.get('presence',[]))))
        with tcmj:
            history=sorted(p.get("cmj",[]),key=lambda x:x["date"])
            if history:
                st.metric("Dernier CMJ",f"{history[-1]['value']} cm",delta=f"{history[-1]['value']-history[0]['value']:+.1f} cm depuis le premier test")
                frame=pd.DataFrame(history)
                frame["date"]=pd.to_datetime(frame["date"])
                st.line_chart(frame.set_index("date")["value"],color="#0756A8",x_label="Date",y_label="Hauteur (cm)")
            else: st.info("Aucun CMJ enregistré")
            if st.session_state.editor:
                with st.form(f"add_cmj_{chosen}"):
                    testdate=st.date_input("Date du test",value=date.today())
                    height=st.number_input("CMJ en cm",min_value=0.0,max_value=100.0,value=0.0,step=0.5)
                    if st.form_submit_button("Ajouter le CMJ"):
                        updated=copy.deepcopy(D)
                        target=edit_record(updated,"players",chosen)
                        target["cmj"].append({"date":testdate.isoformat(),"value":float(height)})
                        target["cmj"].sort(key=lambda x:x["date"])
                        commit(updated)
        with tindices:
            st.caption("Indices sur 100 saisis par le coach ; définis une méthode d'évaluation avant usage réel.")
            for i,label in enumerate(D["indices_names"]):
                value=p.get("indices",[0,0,0])[i]
                st.markdown(f"**{label} — {value}/100**")
                st.progress(value/100)
            if st.session_state.editor:
                with st.form(f"indices_{chosen}"):
                    vals=[st.slider(label,0,100,int(p['indices'][i]),key=f"idx_{chosen}_{i}") for i,label in enumerate(D["indices_names"])]
                    if st.form_submit_button("Enregistrer les trois indices"):
                        updated=copy.deepcopy(D)
                        edit_record(updated,"players",chosen)["indices"]=vals
                        commit(updated)
    else: st.info("Ajoute d'abord un joueur dans Gestion.")

with tab_manage:
    if not st.session_state.editor:
        st.info("Active le mode modification dans le menu ☰ pour gérer les entraîneurs et les joueurs.")
    else:
        st.subheader("🏅 Entraîneurs")
        st.caption("Ajoute un coach ou ouvre son profil pour modifier son prénom, son nom ou sa photo.")
        with st.expander("➕ Ajouter un entraîneur",expanded=not bool(coaches)):
            with st.form("coach_add",clear_on_submit=True):
                first=st.text_input("Prénom du coach")
                last=st.text_input("Nom du coach")
                photo=st.file_uploader("Photo (JPG/PNG, 1 Mo max)",type=["jpg","jpeg","png"],key="coach_add_photo")
                if st.form_submit_button("Ajouter le coach"):
                    blob=uploaded_photo(photo)
                    if not first.strip(): st.error("Le prénom est obligatoire.")
                    elif blob is not False:
                        updated=copy.deepcopy(D)
                        updated["coaches"].append({"id":uuid.uuid4().hex,"first_name":first.strip(),"last_name":last.strip(),"photo":blob or ""})
                        commit(updated)
        if coaches:
            for coach in coaches:
                with st.expander(f"✏️ {name(coach)}"):
                    with st.form(f"coach_edit_{coach['id']}"):
                        first=st.text_input("Prénom",value=coach["first_name"])
                        last=st.text_input("Nom",value=coach.get("last_name",""))
                        photo=st.file_uploader("Nouvelle photo",type=["jpg","jpeg","png"],key=f"photo_{coach['id']}")
                        remove_photo=st.checkbox("Supprimer la photo actuelle")
                        if st.form_submit_button("Enregistrer ce coach"):
                            blob=uploaded_photo(photo)
                            if not first.strip(): st.error("Le prénom est obligatoire")
                            elif blob is not False:
                                updated=copy.deepcopy(D)
                                target=edit_record(updated,"coaches",coach["id"])
                                target.update(first_name=first.strip(),last_name=last.strip())
                                if remove_photo: target["photo"]=""
                                elif blob is not None: target["photo"]=blob
                                commit(updated)
                    st.markdown("**Supprimer cet entraîneur**")
                    st.caption("Ses joueurs et leurs données sont conservés et deviennent non attribués.")
                    confirm_key=f"confirm_coach_delete_{coach['id']}"
                    confirmed=st.checkbox("Je confirme la suppression de cet entraîneur",key=confirm_key)
                    if st.button("🗑️ Supprimer cet entraîneur",key=f"delete_coach_{coach['id']}",disabled=not confirmed):
                        updated=copy.deepcopy(D)
                        updated["coaches"]=[c for c in updated["coaches"] if c["id"]!=coach["id"]]
                        for player in updated["players"]:
                            if player.get("coach_id")==coach["id"]:
                                player["coach_id"]=None
                        # Après le rerun, le choix du coach est corrigé en amont du selectbox.
                        commit(updated)
        st.divider()
        st.subheader("🎾 Joueurs")
        st.caption("Ajoute un joueur, puis affecte-le à un entraîneur. Ses résultats restent dans sa fiche.")
        opts={"": "Non attribué",**{c["id"]:name(c) for c in coaches}}
        with st.expander("➕ Ajouter un joueur"):
            with st.form("player_add",clear_on_submit=True):
                first=st.text_input("Prénom du joueur")
                last=st.text_input("Nom du joueur")
                age=st.number_input("Âge (0 si non renseigné)",min_value=0,max_value=99,value=0)
                category=st.text_input("Catégorie / classement",value="")
                coach_id=st.selectbox("Entraîneur référent",list(opts),format_func=lambda k:opts[k])
                if st.form_submit_button("Ajouter le joueur"):
                    if not first.strip(): st.error("Le prénom est obligatoire")
                    else:
                        updated=copy.deepcopy(D)
                        updated["players"].append({"id":uuid.uuid4().hex,"coach_id":coach_id or None,"first_name":first.strip(),"last_name":last.strip(),"age":int(age),"category":category.strip(),"presence":[],"cmj":[],"indices":[0,0,0],"goals":[]})
                        commit(updated)
        if players:
            player_ids={p["id"]:name(p) for p in players}
            edit_id=st.selectbox("Modifier ou supprimer un joueur",list(player_ids),format_func=lambda k:player_ids[k])
            ep=edit_record(D,"players",edit_id)
            with st.form(f"player_edit_{edit_id}"):
                first=st.text_input("Prénom",value=ep["first_name"])
                last=st.text_input("Nom",value=ep.get("last_name",""))
                age=st.number_input("Âge du joueur (0 si non renseigné)",min_value=0,max_value=99,value=int(ep.get("age") or 0))
                category=st.text_input("Catégorie",value=ep.get("category",""))
                existing=ep.get("coach_id") or ""
                coach_id=st.selectbox("Attribuer à un coach",list(opts),index=list(opts).index(existing) if existing in opts else 0,format_func=lambda k:opts[k])
                if st.form_submit_button("Enregistrer ce joueur"):
                    if not first.strip(): st.error("Le prénom est obligatoire")
                    else:
                        updated=copy.deepcopy(D)
                        edit_record(updated,"players",edit_id).update(first_name=first.strip(),last_name=last.strip(),age=int(age),category=category.strip(),coach_id=coach_id or None)
                        commit(updated)
            st.markdown("**Supprimer ce joueur**")
            st.caption("La suppression efface définitivement la fiche du joueur, ses présences, ses CMJ et ses indices tennis.")
            confirm_key=f"confirm_player_delete_{edit_id}"
            confirmed=st.checkbox("Je confirme la suppression de ce joueur et de ses résultats",key=confirm_key)
            if st.button("🗑️ Supprimer ce joueur",key=f"delete_player_{edit_id}",disabled=not confirmed):
                updated=copy.deepcopy(D)
                updated["players"]=[p for p in updated["players"] if p["id"]!=edit_id]
                commit(updated)
        st.divider()
        with st.expander("🧹 Remettre les listes de joueurs et de coachs à zéro"):
            st.warning("Cette action supprime tous les entraîneurs et tous les joueurs, y compris leurs présences, CMJ et indices. Utilise-la uniquement si tu souhaites effacer les anciennes fiches de démonstration.")
            confirm_all=st.checkbox("Je confirme la suppression de toutes les fiches",key="confirm_all_delete")
            if st.button("Vider toutes les fiches",disabled=not confirm_all,type="secondary"):
                updated=copy.deepcopy(D)
                updated["coaches"]=[]
                updated["players"]=[]
                commit(updated)
        st.divider()
        st.subheader("⚙️ Paramètres")
        with st.form("settings"):
            club=st.text_input("Club",value=D["club"])
            season=st.text_input("Saison",value=D["season"])
            indexnames=[st.text_input(f"Nom indice tennis {i+1}",value=D["indices_names"][i]) for i in range(3)]
            if st.form_submit_button("Enregistrer les paramètres"):
                updated=copy.deepcopy(D)
                updated.update(club=club.strip(),season=season.strip(),indices_names=[v.strip() or f"Indice {i+1}" for i,v in enumerate(indexnames)])
                commit(updated)

st.divider()
st.caption("Azur Physique · Fiches initialement vides. La sauvegarde partagée exige Supabase ; protéger les accès avant utilisation réelle avec des mineurs.")
