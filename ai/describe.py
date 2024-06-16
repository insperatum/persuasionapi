from ai.util import openai_client
from tempfile import NamedTemporaryFile
import tempfile
import shutil
from celery.utils.log import get_task_logger
import subprocess
import os
logger = get_task_logger(__name__)
from contextlib import contextmanager

@contextmanager
def tempfilename(extension):
    dir = tempfile.mkdtemp()
    yield os.path.join(dir, 'tempoutput' + extension)
    shutil.rmtree(dir)

def transcribe_video(video_filename: str):
    logger.info(f"Video file name: {video_filename}")
    logger.info(f"Video file size: {os.path.getsize(video_filename)} bytes")

    with tempfilename(".wav") as audio_filename: #NamedTemporaryFile(delete=False, suffix=".wav").name
        command = f"ffmpeg -y -i {video_filename} -ab 160k -ac 2 -ar 44100 -vn {audio_filename}"
        subprocess.call(command, shell=True)

        logger.info(f"Audio file name: {audio_filename}")
        logger.info(f"Audio file size: {os.path.getsize(audio_filename)} bytes")

        with open(audio_filename, "rb") as file:
            transcription = openai_client().audio.transcriptions.create(
                model="whisper-1", 
                file=file
            )
    response = transcription.text

    return response