import os
import random
import streamlit_scrollable_textbox as stx
import streamlit as st
from utils import download_from_url, transcribe_audio, insert_transcript, create_csv, save_file, split_audio, table_config, display_audio, display_video, local_css, transcript_exists, create_files_from_db, init_connection

# set page width 
st.set_page_config(layout='wide')

local_css('style.css')
page_bg_img = f"""
<style>

[data-testid="stAppViewContainer"] > .main {{
background-image: url("https://r4.wallpaperflare.com/wallpaper/707/220/899/gradient-blue-pink-abstract-art-wallpaper-a33b436d2de9cbc5dfa6225748ab3818.jpg");
background-size: 150%;
background-position: center;
background-repeat: no-repeat;
background-attachment: fixed;
}}

[data-testid="stHeader"] {{
background: rgba(2,0,0,0);
}}

[data-testid="stToolbar"] {{
right: 2rem;
}}
</style>
"""
tab1, tab2 = st.tabs(["Home", "Transcribe"])

transcriptions = init_connection()

with tab1:
    st.markdown(page_bg_img, unsafe_allow_html=True)
    st.markdown("This is the homepage")
    
# sidebar
with st.sidebar:
    boolean_options = st.sidebar.radio("**Select upload option**", options=['Upload From URL','Upload From Local Directory'], index=0)

    with tab2:
        st.markdown(page_bg_img, unsafe_allow_html=True)
        column1, column2 = st.columns(2)

        if boolean_options == 'Upload From URL':

            url_input = st.sidebar.text_input('Enter Video URL')

            if url_input:
                try:
                    with column2:
                        st.video(data=url_input)

                    with st.spinner('downloading video...'):
                        info, hash = download_from_url(url_input)

                        result = transcript_exists(info['id'], hash, transcriptions)
                        if result == False:
                            with st.spinner('transcribing audio...'):
                                transcript = transcribe_audio(f'{hash}.wav')
                                insert_transcript(transcript, info, transcriptions)
                                df, csv = create_csv(transcript)
                                txt = transcript['text']
                        else:
                            df, csv, txt = create_files_from_db(result)
                            
                        st.sidebar.success('Done')

                    with column1:
                        table_config(df)
                        export_csv = st.download_button(
                            label="Export CSV",
                            data=csv,
                            file_name=f"{info['title']}.csv",
                            mime='text/csv'
                        )
                        st.markdown('\n\n')
                    
                        stx.scrollableTextbox(txt, height=255)
                        export_txt = st.download_button(
                            label="Export TXT",
                            data=txt,
                            file_name=f"{info['title']}.txt"
                        )
                           
                except Exception as e:
                    st.error('Invalid URL')
                    print(e)
            

        if boolean_options == 'Upload From Local Directory':
            st.markdown(page_bg_img, unsafe_allow_html=True)
            file_input = st.sidebar.file_uploader(
                label='Upload an audio or video file', 
                type=['wav', 'mp3', 'mp4', 'mov']
            )
            if file_input:
                file = save_file(file_input)
                print(file_input.type)
                
                if file_input.type in ["audio/wav", "audio/mpeg", "audio/x-wav"]:
                    with column2:
                        display_audio(file, file_input.type)
                        st.markdown(f'{file}')

                if file_input.type in ["video/mp4", "video/mov"]:
                    with column2:
                        display_video(file)
                        st.markdown(f'{file}')

                    with st.spinner('splitting audio from video...'):
                        file = split_audio(file)

                with st.spinner('transcribing audio...'):
                    result = transcribe_audio(file)
                st.sidebar.success('success')

                df, csv = create_csv(result)

                with column1:
                    table_config(df)
                    export_csv = st.download_button(
                        label="Export CSV",
                        data=csv,
                        file_name=f"{os.path.splitext(file_input.name)[0]}.csv",
                        mime='text/csv'
                    )
                    st.markdown('\n\n')

                    stx.scrollableTextbox(result['text'], height=255)
                    export_txt = st.download_button(
                        label="Export TXT",
                        data=result['text'],
                        file_name=f"{os.path.splitext(file_input.name)[0]}.txt"
                    )