from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound
from moviepy.editor import AudioFileClip
import os
from pydub import AudioSegment
import time


def wyrownaj_glosnosc(folder_path, audio_file, target_volume=-30):
    audio_path = os.path.join(folder_path, audio_file)
    audio = AudioSegment.from_mp3(audio_path)
    audio_volume = audio.dBFS
    volume_change = target_volume - audio_volume
    audio = audio + volume_change
    output_path = os.path.join(folder_path, audio_file)
    audio.export(output_path, format="mp3")

def zmien_probkowanie(audio_path, czestotliwosc_probkowania=16000):
    audio = AudioSegment.from_file(audio_path)
    audio = audio.set_frame_rate(czestotliwosc_probkowania)
    audio.export(audio_path, format="mp3")
    zmienione_audio = AudioSegment.from_file(audio_path)
    print("Nowa częstotliwość próbkowania:", zmienione_audio.frame_rate, "Hz")

def clean_filename(filename):
    return "".join(char for char in filename if char.isalnum() or char in ['_', ' ']).rstrip()

def pobierz_audio(folder_wyjsciowy, youtube_url):
    yt = YouTube(youtube_url)
    folder_mowcy = folder_wyjsciowy
    if not os.path.exists(folder_mowcy):
        os.makedirs(folder_mowcy)

    audio_nazwa = f"{clean_filename(yt.title)}.mp3"
    audio_path = os.path.join(folder_mowcy, audio_nazwa)
    audio = yt.streams.filter(only_audio=True).first()
    audio.download(filename=audio_path)
    return audio_path, folder_mowcy, yt, audio_nazwa

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def podziel_audio(audio_path, transcript, id_mowcy, folder_wyjsciowy, id_filmu):
    clip = AudioFileClip(audio_path)
    clip1 = AudioSegment.from_file(audio_path)
    print("Częstotliwość próbkowania:", clip1.frame_rate, "Hz") 
    for i, entry in enumerate(transcript):
        start_time = entry['start']
        end_time = start_time + entry['duration']
        
        if start_time < clip1.duration_seconds and end_time < clip1.duration_seconds:
            if start_time > 0.1:
                start_time -= 0.1
            if end_time < clip1.duration_seconds - 0.1:
                end_time += 0.1
            split_clip = clip.subclip(start_time, end_time)
            folder_zapisu = os.path.join(folder_wyjsciowy, f'{id_mowcy}_{id_filmu}_{i+1}.mp3')
            
            if not wykluczenie_linii(entry['text']):
                split_clip.write_audiofile(folder_zapisu)
            else:
                print(f"Wykryto warunek pominiecia w transkrypcji dla próbki {i+1}.")
        else:
            print(f"Czas próbki poza zakresem pliku audio dla próbki {i+1}.")
            
    clip.close()

def wykluczenie_linii(text):
    lista_wykluczen = ['*', '(', ')', '[', ']', '$', '&', '♪']
    for wykluczenie in lista_wykluczen:
        if wykluczenie.lower() in text.lower():
            return True
    return False

def pobierz_transkrypcje(youtube_url, folder_mowcy, id_mowcy, id_filmu, lang='pl'):
    _id = youtube_url.split("=")[1].split("&")[0]
    
    transcript_filename = f"{id_mowcy}_{id_filmu}_transcript.txt" 
    transcript_path = os.path.join(folder_mowcy, transcript_filename)
    try:
        transcript = YouTubeTranscriptApi.get_transcript(_id, languages=[lang])
        konwertuj_transkrypcje(transcript, transcript_path)
        return transcript
    except NoTranscriptFound:
        print("Transkrypcja w języku polskim nie jest dostępna dla tego filmu.")
        return None

def konwertuj_transkrypcje(transcript, transcript_path):
    with open(transcript_path, 'w', encoding='utf-8') as file:
        for i, entry in enumerate(transcript):
            text = entry['text'].replace('\n', ' ')
            
            if not wykluczenie_linii(text):
                file.write(f"{i+1}: {text}\n")
            else:
                print(f"Usunięto linię w transkrypcji dla próbki {i+1}.")

def usun_plik(file_path):
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            os.remove(file_path)
            print(f"Plik {file_path} usunięto.")
            break
        except PermissionError:
            print(f"Próba {attempt + 1}/{max_attempts}: Plik {file_path} jest w użyciu...")
            time.sleep(2)

def stworz_legende_mowca(folder, legend_filename, legenda):
    os.makedirs(folder, exist_ok=True)
    legend_path = os.path.join(folder, legend_filename)
    with open(legend_path, 'w', encoding='utf-8') as file:
        for entry in legenda:
            file.write(f"{entry['idM']} {entry['name']}\n")

def stworz_legende_filmy(folder, legend_filename, legenda):
    os.makedirs(folder, exist_ok=True)
    legend_path = os.path.join(folder, legend_filename)
    with open(legend_path, 'w', encoding='utf-8') as file:
        for entry in legenda:
            file.write(f"{entry['idM']} {entry['idF']} {entry['name']}\n")

def main():
    youtube_url_list = ["https://www.youtube.com/watch?v=EaY-_Y83WNs",
                        "https://www.youtube.com/watch?v=p5_qOTRjAbE",
                        "https://www.youtube.com/watch?v=-lLHs5DHRfI"]
    mowcy_legenda = []
    filmy_legenda = []
    lang = 'pl'

    for youtube_url in youtube_url_list:
        id_mowcy = None
        id_filmu = None
        folder_wyjsciowy = None

        yt = YouTube(youtube_url)
        
        _id = youtube_url.split("=")[1].split("&")[0]
        try:
            transcript = YouTubeTranscriptApi.get_transcript(_id, languages=[lang])
        except NoTranscriptFound:
            print("Transkrypcja w języku polskim nie jest dostępna dla tego filmu.")


        if transcript:
            # Sprawdzenie czy mówca już występuje w legendzie
            nazwa_kanalu = clean_filename(yt.author)
            existing_mowca_entry = next((entry for entry in mowcy_legenda if entry['name'] == nazwa_kanalu), None)

            if existing_mowca_entry:
                id_mowcy = existing_mowca_entry['idM']
            else:
                id_mowcy = f"M{len(mowcy_legenda) + 1:02d}"
                mowcy_legenda.append({'idM': id_mowcy, 'name': nazwa_kanalu})

            # Sprawdzenie czy film już występuje w legendzie
            nazwa_filmu = clean_filename(yt.title)
            id_filmu = f"F{len(filmy_legenda) + 1:02d}"
            filmy_legenda.append({'idF': id_filmu, 'idM':id_mowcy, 'name': nazwa_filmu})



        audio_path, folder_mowcy, yt, audio_nazwa = pobierz_audio(f'{id_mowcy}', youtube_url)
        #wyrownaj_glosnosc(folder_mowcy, audio_nazwa)   #to chyba nic nie da - bo wyrownuje tylko plik główny, a nie wycinki
        zmien_probkowanie(audio_path, czestotliwosc_probkowania=16000)
        transcript = pobierz_transkrypcje(youtube_url, folder_mowcy, id_mowcy, id_filmu)


        if transcript:
            folder_wyjsciowy = f'{id_mowcy}'
            os.makedirs(folder_wyjsciowy, exist_ok=True)

            podziel_audio(audio_path, transcript, id_mowcy, folder_wyjsciowy, id_filmu)

        #usun_plik(audio_path)

    stworz_legende_mowca("Legendy", "mowcy_legenda.txt", mowcy_legenda)
    stworz_legende_filmy("Legendy", "filmy_legenda.txt", filmy_legenda)

if __name__ == "__main__":
    main()
