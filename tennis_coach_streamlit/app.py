"""Tennis Coach Dashboard — démonstration éditable et partageable."""
import base64
import copy
import hmac
import json
import uuid
from datetime import date

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Tennis Coach Dashboard", page_icon="🎾", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""<style>
.block-container{max-width:800px;padding-top:1.2rem;padding-bottom:4rem}
[data-testid="stAppViewContainer"]{background:#F6F8F6}
h1,h2,h3{letter-spacing:-.035em} h1{font-size:2rem!important}
.hero{border-radius:22px;background:#153F35;color:#fff;padding:24px;margin-bottom:18px}
.hero small{letter-spacing:.14em;color:#AFD3C2}.hero h2{color:#fff;margin:8px 0;font-size:1.6rem}
.hero p{color:#D1E4DC;margin:0}.eyebrow{color:#468471;font-size:.78rem;font-weight:700;letter-spacing:.1em}
[data-testid="stMetric"]{background:#fff;border:1px solid #E4EAE7;border-radius:15px;padding:12px}
div[data-testid="stVerticalBlockBorderWrapper"]{border-radius:17px;background:#FFF}
@media(max-width:600px){.block-container{padding-left:.8rem;padding-right:.8rem}.hero{padding:18px}}
</style>""", unsafe_allow_html=True)

DEFAULT = {
    "coach": {"first_name": "Thomas", "last_name": "Martin", "club": "Club de démonstration", "season": "2026–2027", "photo": ""},
    "indices_names": ["Régularité", "Précision", "Intensité"],
    "players": [
        {"id": "p1", "first_name": "Léo", "last_name": "Bernard", "age": 13, "category": "U14", "presence": [True,True,False,True,True,True,True,False], "cmj": [{"date":"2026-09-03","value":27},{"date":"2026-10-03","value":30},{"date":"2026-11-03","value":33}], "indices":[78,71,82]},
        {"id": "p2", "first_name": "Inès", "last_name": "Petit", "age": 14, "category": "U16", "presence": [True,True,True,True,True,False,True,True], "cmj": [{"date":"2026-09-03","value":24},{"date":"2026-10-03","value":27},{"date":"2026-11-03","value":30}], "indices":[85,89,74]},
        {"id": "p3", "first_name": "Noah", "last_name": "Martin", "age": 12, "category": "U14", "presence": [False,True,True,True,False,True,True,True], "cmj": [{"date":"2026-09-03","value":22},{"date":"2026-10-03","value":24},{"date":"2026-11-03","value":27}], "indices":[67,75,80]},
        {"id": "p4", "first_name": "Emma", "last_name": "Laurent", "age": 15, "category": "U16", "presence": [True]*8, "cmj": [{"date":"2026-09-03","value":28},{"date":"2026-10-03","value":31},{"date":"2026-11-03","value":32}], "indices":[88,80,76]},
    ],
}

def secret(name, default=""):
    try:
        return st.secrets.get(name, default)
    except (FileNotFoundError, KeyError):
        return default

SUPA_URL = str(secret("SUPABASE_URL")).rstrip("/")
SUPA_KEY = str(secret("SUPABASE_SERVICE_ROLE_KEY"))
REMOTE = bool(SUPA_URL and SUPA_KEY)
HEADERS = {"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}", "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates,return=minimal"}
API = f"{SUPA_URL}/rest/v1/tennis_dashboard_state"

def load_remote():
    response = requests.get(API, headers=HEADERS, params={"id":"eq.main", "select":"content"}, timeout=12)
    response.raise_for_status()
    result=response.json()
    return result[0]["content"] if result else copy.deepcopy(DEFAULT)

def save_remote(data):
    response = requests.post(API, headers=HEADERS, json={"id":"main", "content":data}, timeout=12)
    response.raise_for_status()

if "data" not in st.session_state:
    try:
        st.session_state.data = load_remote() if REMOTE else copy.deepcopy(DEFAULT)
    except requests.RequestException as exc:
        st.error(f"Connexion à la base impossible : {exc}")
        st.stop()

VIEW_PASSWORD = str(secret("VIEW_PASSWORD"))
EDIT_PASSWORD = str(secret("EDIT_PASSWORD"))
if "view_ok" not in st.session_state:
    st.session_state.view_ok = not bool(VIEW_PASSWORD)
if not st.session_state.view_ok:
    st.title("🎾 Tennis Coach Dashboard")
    with st.form("viewer_auth"):
        code=st.text_input("Code d'accès", type="password")
        if st.form_submit_button("Voir le tableau de bord", use_container_width=True):
            if hmac.compare_digest(code, VIEW_PASSWORD):
                st.session_state.view_ok=True
                st.rerun()
            else:
                st.error("Code incorrect")
    st.stop()

if "editor" not in st.session_state:
    st.session_state.editor=False
with st.sidebar:
    st.title("🎾 Espace coach")
    if EDIT_PASSWORD:
        if not st.session_state.editor:
            with st.form("editor_auth"):
                editor_code=st.text_input("Mot de passe modification", type="password")
                if st.form_submit_button("Activer les modifications"):
                    if hmac.compare_digest(editor_code, EDIT_PASSWORD):
                        st.session_state.editor=True
                        st.rerun()
                    else:
                        st.error("Mot de passe incorrect")
        else:
            st.success("Mode modification activé")
            if st.button("Quitter le mode modification"):
                st.session_state.editor=False
                st.rerun()
    else:
        st.info("Mode démonstration : saisie temporaire dans ce navigateur.")
        st.session_state.editor=True
    if REMOTE:
        st.caption("Données synchronisées avec Supabase. Les modifications enregistrées sont visibles par les autres visiteurs.")
        if st.button("🔄 Actualiser les données"):
            st.session_state.data=load_remote()
            st.rerun()
    else:
        st.warning("Sans Supabase, les saisies ne sont pas partagées par le lien et peuvent disparaître.")
    st.caption("L'accès au mode édition est réservé au coach. Ne publiez pas de données réelles de mineurs sans accès protégé.")

def commit(data):
    if not st.session_state.editor:
        st.error("Accès réservé à l'entraîneur")
        return
    if REMOTE:
        try:
            save_remote(data)
        except requests.RequestException as exc:
            st.error(f"Sauvegarde impossible : {exc}")
            return
    st.session_state.data=copy.deepcopy(data)
    st.rerun()

def full_name(player):
    return f"{player['first_name']} {player['last_name']}".strip()

def presence_pct(player):
    weeks=player.get("presence",[])
    return round(100*sum(weeks)/len(weeks)) if weeks else 0

def last_cmj(player):
    history=player.get("cmj",[])
    return history[-1]["value"] if history else None

data=st.session_state.data
coach=data["coach"]
st.markdown('<div class="eyebrow">TENNIS PERFORMANCE · ESPACE ENTRAÎNEUR</div>', unsafe_allow_html=True)
st.title("Mon tableau de bord")
portrait, identity=st.columns([1,3],vertical_alignment="center")
with portrait:
    if coach.get("photo"):
        try:
            st.image(base64.b64decode(coach["photo"]),width=100)
        except (ValueError, TypeError):
            st.write("👨‍🏫")
    else:
        st.markdown("<div style='height:82px;width:82px;border-radius:50%;background:#dcebe3;display:flex;justify-content:center;align-items:center;font-size:37px'>👨‍🏫</div>",unsafe_allow_html=True)
with identity:
    st.caption("MON ESPACE COACH")
    st.subheader(f"Bonjour, {coach['first_name']} 👋")
    st.caption(f"{coach.get('club','')} · Saison {coach.get('season','')}")
st.markdown('<div class="hero"><small>VUE D’ENSEMBLE</small><h2>Suivi de mon groupe 🎾</h2><p>Présences physiques, CMJ et 3 indices tennis, réunis au même endroit.</p></div>',unsafe_allow_html=True)
players=data["players"]
a,b,c=st.columns(3)
a.metric("Joueurs",len(players))
b.metric("Présences", f"{round(sum(presence_pct(p) for p in players)/len(players)) if players else 0}%")
vals=[last_cmj(p) for p in players if last_cmj(p) is not None]
c.metric("CMJ moyen",f"{sum(vals)/len(vals):.1f} cm" if vals else "—")

tab_roster, tab_profile, tab_manage=st.tabs(["👥 Joueurs","📈 Fiche joueur","⚙️ Gestion"])
with tab_roster:
    query=st.text_input("Rechercher",placeholder="Nom ou prénom",key="search_players")
    listed=[p for p in players if query.lower() in full_name(p).lower()]
    if not listed:
        st.info("Aucun joueur trouvé. Tu peux en ajouter dans Gestion.")
    for p in listed:
        with st.container(border=True):
            l,r=st.columns([3,1],vertical_alignment="center")
            with l:
                st.markdown(f"**🎾 {full_name(p)}**")
                st.caption(f"{p.get('category','')} · {p.get('age','—')} ans · Présence {presence_pct(p)} %")
            with r:
                st.metric("CMJ",f"{last_cmj(p)} cm" if last_cmj(p) is not None else "—")

with tab_profile:
    if players:
        opts={p["id"]:full_name(p) for p in players}
        selected=st.selectbox("Choisir le joueur",list(opts),format_func=lambda k:opts[k])
        p=next(x for x in players if x["id"]==selected)
        st.subheader(full_name(p))
        t1,t2,t3=st.tabs(["📅 Présences","📊 CMJ","🎯 Indices tennis"])
        with t1:
            st.caption("Une case = une séance hebdomadaire de préparation physique. Pour la démo : 8 semaines.")
            st.metric("Taux de présence",f"{presence_pct(p)} %")
            with st.form(f"att_{selected}"):
                current=p.get("presence",[False]*8)
                changed=[]
                for start in range(0,len(current),4):
                    cols=st.columns(4)
                    for j,col in enumerate(cols):
                        idx=start+j
                        if idx<len(current):
                            changed.append(col.checkbox(f"S{idx+1}",value=current[idx],key=f"week_{selected}_{idx}"))
                if st.form_submit_button("Enregistrer les présences",disabled=not st.session_state.editor):
                    updated=copy.deepcopy(data)
                    next(p2 for p2 in updated["players"] if p2["id"]==selected)["presence"]=changed
                    commit(updated)
        with t2:
            if p.get("cmj"):
                st.metric("Dernier CMJ",f"{last_cmj(p)} cm", delta=f"{last_cmj(p)-p['cmj'][0]['value']:+.1f} cm depuis le premier test")
                df=pd.DataFrame(p["cmj"])
                df["date"]=pd.to_datetime(df["date"])
                st.line_chart(df.set_index("date")["value"],color="#23765c",x_label="Date",y_label="CMJ (cm)")
            else:
                st.info("Pas encore de CMJ enregistré")
            if st.session_state.editor:
                with st.form(f"cmj_add_{selected}"):
                    test_date=st.date_input("Date du test",value=date.today())
                    cmj_value=st.number_input("Hauteur CMJ (cm)",min_value=0.0,max_value=100.0,value=30.0,step=0.5)
                    if st.form_submit_button("Ajouter ce CMJ"):
                        updated=copy.deepcopy(data)
                        target=next(p2 for p2 in updated["players"] if p2["id"]==selected)
                        target["cmj"].append({"date":test_date.isoformat(),"value":float(cmj_value)})
                        target["cmj"].sort(key=lambda x:x["date"])
                        commit(updated)
        with t3:
            st.caption("Indices personnalisables entre 0 et 100. Méthode de calcul à définir avant utilisation réelle.")
            for label,val in zip(data["indices_names"],p["indices"]):
                st.markdown(f"**{label} : {val}/100**")
                st.progress(max(0,min(100,val))/100)
            if st.session_state.editor:
                with st.form(f"idx_{selected}"):
                    values=[st.slider(label,0,100,int(val),key=f"idx_{selected}_{i}") for i,(label,val) in enumerate(zip(data["indices_names"],p["indices"]))]
                    if st.form_submit_button("Enregistrer les indices"):
                        updated=copy.deepcopy(data)
                        next(p2 for p2 in updated["players"] if p2["id"]==selected)["indices"]=values
                        commit(updated)
    else:
        st.info("Ajoute d'abord un joueur depuis Gestion.")

with tab_manage:
    if not st.session_state.editor:
        st.info("Pour modifier le coach ou les joueurs, active le mode édition dans le menu latéral.")
    else:
        st.subheader("Profil de l'entraîneur")
        with st.form("coach_details"):
            first=st.text_input("Prénom",value=coach.get("first_name",""))
            last=st.text_input("Nom",value=coach.get("last_name",""))
            club=st.text_input("Club",value=coach.get("club",""))
            season=st.text_input("Saison",value=coach.get("season",""))
            photo=st.file_uploader("Photo du coach (JPG / PNG, 1 Mo maximum)",type=["jpg","jpeg","png"])
            if st.form_submit_button("Enregistrer le profil"):
                updated=copy.deepcopy(data)
                updated["coach"].update({"first_name":first.strip(),"last_name":last.strip(),"club":club.strip(),"season":season.strip()})
                if photo:
                    if photo.size>1024*1024:
                        st.error("La photo dépasse 1 Mo. Choisis une image plus légère.")
                        st.stop()
                    updated["coach"]["photo"]=base64.b64encode(photo.getvalue()).decode("ascii")
                commit(updated)
        st.divider()
        st.subheader("Ajouter un joueur")
        with st.form("add_player",clear_on_submit=True):
            first=st.text_input("Prénom du joueur")
            last=st.text_input("Nom du joueur")
            age=st.number_input("Âge",min_value=5,max_value=99,value=13)
            cat=st.text_input("Catégorie / classement",value="U14")
            if st.form_submit_button("Ajouter ce joueur"):
                if not first.strip() or not last.strip():
                    st.error("Prénom et nom obligatoires")
                else:
                    updated=copy.deepcopy(data)
                    updated["players"].append({"id":uuid.uuid4().hex,"first_name":first.strip(),"last_name":last.strip(),"age":int(age),"category":cat.strip(),"presence":[False]*8,"cmj":[],"indices":[0,0,0]})
                    commit(updated)
        st.divider()
        st.subheader("Modifier un joueur")
        if players:
            ids={p["id"]:full_name(p) for p in players}
            editid=st.selectbox("Joueur à modifier",list(ids),format_func=lambda k:ids[k])
            ep=next(p for p in players if p["id"]==editid)
            with st.form(f"edit_player_{editid}"):
                f=st.text_input("Prénom",value=ep["first_name"])
                l=st.text_input("Nom",value=ep["last_name"])
                a=st.number_input("Âge",5,99,value=int(ep["age"]))
                cat=st.text_input("Catégorie / classement",value=ep["category"])
                if st.form_submit_button("Enregistrer ce joueur"):
                    updated=copy.deepcopy(data)
                    target=next(p for p in updated["players"] if p["id"]==editid)
                    target.update({"first_name":f.strip(),"last_name":l.strip(),"age":int(a),"category":cat.strip()})
                    commit(updated)
        st.divider()
        st.subheader("Nom des 3 indices tennis")
        with st.form("rename_indices"):
            labels=[st.text_input(f"Indice {i+1}",value=name) for i,name in enumerate(data["indices_names"])]
            if st.form_submit_button("Enregistrer les noms"):
                updated=copy.deepcopy(data)
                updated["indices_names"]=[n.strip() or f"Indice {i+1}" for i,n in enumerate(labels)]
                commit(updated)

st.divider()
st.caption("Prototype de démonstration • Les exemples initiaux sont fictifs. Données enregistrées en ligne uniquement si Supabase est configuré. Pour de vrais joueurs mineurs : authentification, consentements et protection des données à finaliser avant déploiement.")
