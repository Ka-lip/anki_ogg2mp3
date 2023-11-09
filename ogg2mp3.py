import json
import urllib.request
import re
import os
import subprocess
from lang import lang

media_folder = r"C:\anki_userdata\main\collection.media"
ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"
lang_code = "Taiwanese"  # 'Taiwanese' or 'Taiwanese_mandarin' or 'English'

source_extension = ".ogg"
target_extension = ".ogg.mp3"
defaul_search_re = "\[sound:(.*?ogg)\]"
query_string = "re:\[sound:.*?ogg\]"

replace_from = source_extension + "]"
replace_to = target_extension + "]"


def request(action, **params):
    return {"action": action, "params": params, "version": 6}


def invoke(action, **params):
    requestJson = json.dumps(request(action, **params)).encode("utf-8")
    response = json.load(
        urllib.request.urlopen(
            urllib.request.Request("http://localhost:8765", requestJson)
        )
    )
    if len(response) != 2:
        raise Exception("response has an unexpected number of fields")
    if "error" not in response:
        raise Exception("response is missing required error field")
    if "result" not in response:
        raise Exception("response is missing required result field")
    if response["error"] is not None:
        raise Exception(response["error"])
    return response["result"]


def color_text(text, color="r"):
    if color == "r":
        return "\033[91m" + text + "\033[0m"
    if color == "g":
        return "\033[92m" + text + "\033[0m"


def get_notes_by_query(query_string=query_string):
    notes_list = invoke("findNotes", query=query_string)
    notes_info = invoke("notesInfo", notes=notes_list)
    return notes_info


def get_notes_by_nid(nids):  # support single nid or list of nids
    if type(nids) is list:
        return invoke("notesInfo", notes=nids)  # this returns a list of note dicts
    else:
        return invoke("notesInfo", notes=[nids])[0]  # this returns a note dict


def strip_fields(note, target_fields):  # support note_dict or nid
    if type(note) is int:
        note = get_notes_by_nid(note)
    result = {}
    for f in target_fields:
        result[f] = note["fields"][f]["value"]
    return result


def find_str(find_in, find_this_re=defaul_search_re):
    return re.findall(find_this_re, find_in)


def get_matched_fields(
    note, find_this_re=defaul_search_re
):  # note can be note_dict or nid
    fields_list = []
    if type(note) is dict:
        note_dict = note
    else:
        note_dict = get_notes_by_nid(note)
    for field_name, field_content in note_dict["fields"].items():
        find_result = find_str(field_content["value"], find_this_re)
        if find_result:
            fields_list.append(field_name)
    return fields_list


def filter_matched_note(
    note, find_this_re=defaul_search_re
):  # note can be note_dict or nid
    note_schema = {}
    target_fields = get_matched_fields(note, find_this_re)
    note_content = strip_fields(note, target_fields)
    note_schema["fields"] = note_content
    note_schema["nid"] = note["noteId"] if type(note) is dict else note
    return note_schema


def get_new_fields(note_schema, replace_from=replace_from, replace_to=replace_to):
    result_dict = {}
    fields_dict = note_schema["fields"]
    for k, v in fields_dict.items():
        result_dict[k] = v.replace(replace_from, replace_to)
    note_schema["new_fields"] = result_dict
    return note_schema


def get_file_names(note_schema, find_this_re=defaul_search_re):
    old_file_names = []
    for k in note_schema["fields"]:
        find_result = find_str(note_schema["fields"][k], find_this_re)
        old_file_names += find_result
    note_schema["file_names"] = old_file_names
    return note_schema


def get_new_file_names(note_schema, src=source_extension, tgt=target_extension):
    new_file_names = [i.replace(src, tgt) for i in note_schema["file_names"]]
    note_schema["new_file_names"] = new_file_names
    return note_schema


def show_notes_in_anki(notes_schema):
    if type(notes_schema) is dict:
        query_ids = ",".join([str(i) for i in notes_schema.keys()])
    if type(notes_schema) is list:
        query_ids = [str(i) for i in notes_schema]
    if type(notes_schema) in [int, str]:
        query_ids = str(note_schema)
    query_str = "nid:" + query_ids
    invoke("guiBrowse", query=query_str)


def convert_file(note):
    note_schema = note if type(note) is dict else ""
    source_files = note_schema["file_names"]
    destination_files = note_schema["new_file_names"]
    for s, d in zip(source_files, destination_files):
        source_file = os.path.join(media_folder, s)
        destination_file = os.path.join(media_folder, d)
        conversion_command = [
            ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            source_file,
            destination_file,
        ]
        try:
            subprocess.run(conversion_command, shell=True)
            print(f"Converted: {source_file} -> {destination_file}")
        except subprocess.CalledProcessError as e:
            print(f"Error converting {source_file}: {e}")


def rm_file(note_schema, undo=False):
    file_names = (
        note_schema["file_names"] if not undo else note_schema["new_file_names"]
    )
    for f in file_names:
        invoke("deleteMediaFile", filename=f)
        print("file {} has been deleted.".format(f))


def update_field(note_schema, undo=False):
    nid = note_schema["nid"]
    new_fields = (
        note_schema["new_fields"] if not undo else note_schema["fields"]
    )  # undo is for roll-back
    for f_name, f_text in new_fields.items():
        invoke("updateNoteFields", note={"id": nid, "fields": {f_name: f_text}})
        print(
            "note {}'s fields has been updated. Field of {} has become {}.".format(
                nid, f_name, f_text
            )
        )


def get_schemas(nid=None):
    if type(nid) in [int, str]:
        notes_list = [get_notes_by_nid(int(nid))]
    elif type(nid) is list:
        notes_list = [get_notes_by_nid(int(i)) for i in nid]
    else:
        notes_list = get_notes_by_query()
    note_schemas = {}
    for note in notes_list:
        current_dict = filter_matched_note(note)
        current_dict = get_new_fields(current_dict)
        current_dict = get_file_names(current_dict)
        current_dict = get_new_file_names(current_dict)
        note_schemas[current_dict["nid"]] = current_dict
    print("got schemas.")
    return note_schemas


def user_confirmed(notes_schema):
    show_notes_in_anki(notes_schema)
    user_say = input(color_text(lang[lang_code]["confirm"])).lower()
    return True if user_say == "delete" else False


def anki_open(lang_code=lang_code):
    while True:
        checkAnki = input(color_text(lang[lang_code]["open_anki"])).lower()
        if checkAnki == "yes":
            break
        if checkAnki == "en":
            lang_code = "English"
    return lang_code


def main():
    lang_code = anki_open()
    schemas = get_schemas()
    if len(schemas) == 0:
        print(color_text(lang[lang_code]["no_work"], color="g"))
        return 0

    for _, note in schemas.items():
        update_field(note)
        convert_file(note)

    if user_confirmed(schemas):
        for _, note in schemas.items():
            rm_file(note)
        print("all jobs done")
    else:
        for _, note in schemas.items():
            update_field(note, undo=True)
            rm_file(note, undo=True)
        print("all jobs rolled back")

    invoke("sync")
    print(color_text(lang[lang_code]["finish"], color="g"))


if __name__ == "__main__":
    main()
    subprocess.run(["pause"], shell=True)

