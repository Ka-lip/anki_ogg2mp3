# anki_ogg2mp3
## Fully automatic conversion for anki ogg notes.  
Since iOS does not support ogg format, users of iOS cannot hear the sound on iOS devices.  
This script can solve this issue. It also supports roll-back function in case the converted sound files are not satisfied.  

There are some other scripts doing the same thing. However, these scripts only handle the conversion of the ogg file. Users still need to replace the filename in notes in anki from *.ogg to *.mp3.  

Please note that ogg files in the media folder which are not used in anki notes will not be converted.

## Requirements
- Anki
- Anki connect
- FFMpeg

## Usage
Modify the settings in `ogg2mp3.py`
``` python
media_folder = r'C:\anki_userdata\main\collection.media'
ffmpeg_path = r'C:\ffmpeg\bin\ffmpeg.exe'
lang_code = 'Taiwanese' # 'Taiwanese' or 'Taiwanese_mandarin' or 'English'
```