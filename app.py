import streamlit as st
import sqlite3
import bcrypt
import os
import torch
import soundfile as sf
import base64
from transformers import MusicgenForConditionalGeneration, AutoProcessor
from datetime import datetime
from pydub import AudioSegment
from pydub.effects import compress_dynamic_range, normalize

st.set_page_config(page_title="LUYANDO PRODUCER V1.2", page_icon="🎚️", layout="wide")

# FUNCTION 1: BACKGROUND
def set_background(image_file):
    with open(image_file, "rb") as f: img_data = f.read()
    b64 = base64.b64encode(img_data).decode()
    st.markdown(f"""<style>.stApp {{background-image: url("data:image/jpg;base64,{b64}"); background-size: cover;}}
.login-box {{background-color: rgba(0,0,0,0.85); padding: 35px; border-radius: 20px; border: 3px solid #EF7D00; max-width: 450px; margin: auto; margin-top: 8%;}}
.title {{color: #EF7D00; text-align: center; font-size: 32px; font-weight: 900;}}
.song-card {{background-color: #111; padding: 15px; border-radius: 10px; border: 1px solid #333; margin-bottom: 10px;}}</style>""", unsafe_allow_html=True)

set_background("background.jpg")

for folder in ["generated_songs", "temp", "uploads"]: os.makedirs(folder, exist_ok=True)

def init_db():
    conn = sqlite3.connect('luyando.db'); c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS songs (id INTEGER PRIMARY KEY, user_id INTEGER, song_name TEXT, file_path TEXT, genre TEXT, date TEXT)')
    conn.commit(); conn.close()
init_db()

@st.cache_resource
def load_ai():
    with st.spinner("Loading AI Producer..."):
        processor = AutoProcessor.from_pretrained("facebook/musicgen-small")
        model = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small")
    return processor, model
processor, model = load_ai()

def signup(u,p):
    try: conn=sqlite3.connect('luyando.db');c=conn.cursor();c.execute("INSERT INTO users VALUES (NULL,?,?)",(u,bcrypt.hashpw(p.encode(),bcrypt.gensalt()).decode()));conn.commit();conn.close();return True
    except: return False

def login(u,p):
    conn=sqlite3.connect('luyando.db');c=conn.cursor();c.execute("SELECT * FROM users WHERE username=?",(u,));user=c.fetchone();conn.close()
    return user if user and bcrypt.checkpw(p.encode(),user[2].encode()) else None

def save_song(user_id, song_name, file_path, genre):
    conn=sqlite3.connect('luyando.db');c=conn.cursor();c.execute("INSERT INTO songs VALUES (NULL,?,?,?,?,?)",(user_id, song_name, file_path, genre, datetime.now().strftime("%Y-%m-%d %H:%M")));conn.commit();conn.close()

def get_user_songs(user_id):
    conn=sqlite3.connect('luyando.db');c=conn.cursor();c.execute("SELECT * FROM songs WHERE user_id=? ORDER BY id DESC",(user_id,));songs=c.fetchall();conn.close();return songs

def delete_song(song_id, file_path):
    try: os.remove(file_path)
    except: pass
    conn=sqlite3.connect('luyando.db');c=conn.cursor();c.execute("DELETE FROM songs WHERE id=?",(song_id,));conn.commit();conn.close()

def pro_mix(vocal_path, instrumental_path, output_path):
    vocal = AudioSegment.from_wav(vocal_path); instrumental = AudioSegment.from_wav(instrumental_path)
    vocal = normalize(vocal); instrumental = normalize(instrumental)
    vocal = compress_dynamic_range(vocal, threshold=-20.0, ratio=4.0)
    instrumental = instrumental - 6; vocal = vocal + 3
    final_mix = instrumental.overlay(vocal); final_mix = normalize(final_mix)
    final_mix.export(output_path, format="wav")

def generate_beat(genre):
    with st.spinner("🎵 AI producing beat..."):
        prompt = f"Professional {genre} instrumental, clean, sweet, radio quality, no vocals"
        inputs = processor(text=[prompt], return_tensors="pt")
        audio = model.generate(**inputs, max_new_tokens=1500)
        beat_path = f"temp/beat_{datetime.now().strftime('%H%M%S')}.wav"
        sf.write(beat_path, audio[0].cpu().numpy(), model.config.audio_encoder.sampling_rate)
    return beat_path

def music_storage(user_id):
    st.markdown('<h1 class="title">📁 MY MUSIC STORAGE</h1>', unsafe_allow_html=True)
    songs = get_user_songs(user_id)
    if not songs: st.info("No songs yet. Go to 'New Song' to produce!"); return
    st.write(f"**Total Songs: {len(songs)}**"); st.divider()
    for song in songs:
        song_id, uid, song_name, file_path, genre, date = song
        st.markdown('<div class="song-card">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([3,3,1])
        with col1: st.write(f"**🎵 {song_name}**"); st.caption(f"Genre: {genre} | {date}")
        with col2: st.audio(file_path)
        with col3: st.download_button("⬇️", file_path, key=f"dl{song_id}")
        if st.button("🗑️", key=f"del{song_id}"): delete_song(song_id, file_path); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

def producer_app(user_id):
    st.markdown('<h1 class="title">🎚️ LUYANDO PRODUCER V1.2</h1>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["🎤 New Song", "📁 Music Storage"])
    with tab1:
        genre = st.selectbox("Genre", ["Afrobeats", "Kalindula", "Gospel", "Hip Hop"])
        song_name = st.text_input("Song Name")
        voice_file = st.file_uploader("Upload Voice", type=["wav", "mp3", "m4a"])
        if st.button("🚀 PRODUCE & SAVE", type="primary", use_container_width=True):
            if voice_file and song_name:
                voice_path = f"uploads/{song_name}_voice.wav"
                with open(voice_path, "wb") as f: f.write(voice_file.read())
                beat_path = generate_beat(genre)
                final_path = f"generated_songs/{song_name}_{datetime.now().strftime('%H%M%S')}.wav"
                with st.spinner("🎚️ Mixing..."): pro_mix(voice_path, beat_path, final_path)
                save_song(user_id, song_name, final_path, genre)
                st.success("✅ SONG SAVED!"); st.audio(final_path); st.download_button("⬇️ Download", final_path)
            else: st.warning("Add Song Name + Upload Voice")
    with tab2: music_storage(user_id)

if 'logged' not in st.session_state: st.session_state.logged=False
if not st.session_state.logged:
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown('<h1 class="title">🎵 LUYANDO PRODUCER</h1>', unsafe_allow_html=True)
    tab1,tab2=st.tabs(["🔑 Login","📝 Signup"])
    with tab1:
        u=st.text_input("Username");p=st.text_input("Password",type="password")
        if st.button("Login", type="primary", use_container_width=True):
            user = login(u,p)
            if user: st.session_state.logged=True; st.session_state.user_id=user[0]; st.session_state.username=user[1]; st.markdown("""<style>.stApp {background-image: none; background-color: #000;}</style>""", unsafe_allow_html=True); st.rerun()
            else: st.error("Invalid Login")
    with tab2:
        nu=st.text_input("New Username");np=st.text_input("New Password",type="password")
        if st.button("Create Account", use_container_width=True):
            if signup(nu,np): st.success("✅ Account Created!")
            else: st.error("Username exists")
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.markdown("""<style>.stApp {background-image: none; background-color: #000;}</style>""", unsafe_allow_html=True)
    st.sidebar.success(f"Producer: {st.session_state.username}")
    if st.sidebar.button("Logout"): st.session_state.logged=False; st.rerun()
    producer_app(st.session_state.user_id)
