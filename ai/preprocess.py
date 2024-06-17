from ai.util import openai_client
from tempfile import NamedTemporaryFile
import tempfile
import shutil
from celery.utils.log import get_task_logger
import subprocess
import os
logger = get_task_logger(__name__)
from contextlib import contextmanager
from ai.util import Content, Target

@contextmanager
def tempfilename(extension):
    dir = tempfile.mkdtemp()
    yield os.path.join(dir, 'tempoutput' + extension)
    shutil.rmtree(dir)

def transcribe_video(video_filename: str):
    with tempfilename(".wav") as audio_filename: #NamedTemporaryFile(delete=False, suffix=".wav").name
        command = f"ffmpeg -y -i {video_filename} -ab 160k -ac 2 -ar 44100 -vn {audio_filename}"
        subprocess.call(command, shell=True)
        with open(audio_filename, "rb") as file:
            transcription = openai_client().audio.transcriptions.create(
                model="whisper-1", 
                file=file
            )
    return transcription.text

def preprocess(model:str, content:Content, target:Target):
    if content.video is not None:
        video_file = NamedTemporaryFile(delete=False)
        video_file.write(content.video)
        video_file.close()
        text = transcribe_video(video_file.name)
        os.remove(video_file.name)
        content.message = text