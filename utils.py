import os
import random
import datetime
import youtube_dl
import streamlit as st
import whisper
import pandas as pd
import moviepy.editor as mp
import streamlit.components.v1 as components

from st_aggrid import AgGrid, GridOptionsBuilder, AgGridTheme
from st_aggrid.shared import GridUpdateMode
from pymongo import MongoClient
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())


CONNECTION_STRING = os.getenv("mongodb_connect")


# @st.cache_resource
# def create_client():
#     client = MongoClient(CONNECTION_STRING)
#     db = client['vt_dashboard']
#     transcriptions = db['transcriptions']
#     return transcriptions


@st.cache_resource
def init_connection():
    '''mongodb connection'''
    client =  MongoClient(CONNECTION_STRING)
    db = client['vt_dashboard']
    transcriptions = db['transcriptions']
    return transcriptions


@st.cache_resource
def model():
    '''load model'''
    whisp = whisper.load_model("base", device='cpu')
    return whisp


@st.cache_resource
def download_from_url(url):
    '''download video from url'''
    random_bits = random.getrandbits(128)
    hash = "%032x" % random_bits
    ydl_opts = {
        'outtmpl': f'{hash}.wav',
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }]
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info, hash
  

@st.cache_data
def transcribe_audio(audio):
    result = model().transcribe(audio, verbose=True)
    os.remove(audio)
    return result


def insert_transcript(result, info, _transcriptions):
    '''insert data to mongodb'''
    db_data = {
        "youtube_id": info['id'],
        "title": info['title'],
        "transcript": {}
    }
    for segment in result['segments']:
        start = str(datetime.timedelta(seconds=int(segment['start'])))
        db_data['transcript'][start] = segment['text']

    _transcriptions.insert_one(db_data)


@st.cache_data
def create_csv(result):
    '''create csv for export'''
    data = []
    for segment in result['segments']:
        start = str(datetime.timedelta(seconds=int(segment['start'])))
        data.append({
            "start": start,
            "text": segment['text']
        })
    df = pd.DataFrame(data)
    csv = df.to_csv(index=False).encode('utf-8')
    return df, csv


@st.cache_data
def save_file(file_input):
    '''save file before processing through whisper'''
    with open(file_input.name, 'wb') as f:
        f.write(file_input.getbuffer())
    return file_input.name


@st.cache_data
def split_audio(video):
    '''split audio from video file'''
    audio_file = os.path.basename(video)
    audio_file = f"{os.path.splitext(audio_file)[0]}.wav"

    clip = mp.VideoFileClip(video)
    if clip.audio is not None:
        clip.audio.write_audiofile(audio_file, logger=None)

    os.remove(video)
    return audio_file


@st.cache_data
def export_data(result):
    '''export txt'''
    st.download_button(
        label="export_data",
        data=result['text'],
        file_name="test.txt"
    )


def table_config(df):
    '''streamlit-aggrid dataframe display'''
    options = GridOptionsBuilder.from_dataframe(
        df, enableColResize = True
    )
    selection = AgGrid(
        df,
        enable_enterprise_modules=False,
        gridOptions=options.build(),
        theme=AgGridTheme.STREAMLIT,
        reload_data=False,
        fit_columns_on_grid_load=True,
        grid_update_mode = GridUpdateMode.GRID_CHANGED,
        height=300,
        width=2000,
        allow_unsafe_jscode=True,
        custom_css={
        "#gridToolBar": {
            "padding-bottom": "0px !important",
        }
    }
    )
    return selection
    

@st.cache_data
def display_video(video):
    '''video display'''
    video_file = open(video, 'rb')
    video_bytes = video_file.read()
    st.video(video_bytes)


@st.cache_data
def display_audio(audio, file_type):
    '''audio display'''
    audio_file = open(audio, 'rb')
    audio_bytes = audio_file.read()
    st.audio(audio_bytes, format=file_type)

    
def local_css(file_name):
    '''input box color config loads style.css file'''
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)


@st.cache_data
def transcript_exists(youtube_id, hash, _transcriptions):
    '''check if transcription exists in mongodb before processing video/audio'''
    result = _transcriptions.find_one({"youtube_id": youtube_id})
    if result == None:
        return False
    else:
        os.remove(f'{hash}.wav')
        return result


def create_files_from_db(result):
    '''creates files from db if transcript exists in db'''
    df = pd.DataFrame(result['transcript'].items(), columns=['start', 'text'])
    csv = df.to_csv(index=False).encode('utf-8')
    txt = "".join(result['transcript'].values())
    return df, csv, txt