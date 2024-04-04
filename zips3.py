import os
import shutil
import tempfile
import zipfile
from fastapi import FastAPI, UploadFile, File
import json

app = FastAPI()
sep = "/"
barebones = True

def extract_zip(zip_file, extraction_path):
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(extraction_path)

def flatten_json(json, parent_key='', sep=sep):
    items = []
    if len(json)!=0 :
        items.append(parent_key)
        for key,value in json.items():
            new_key = parent_key + sep + key
            items.extend(flatten_json(value, new_key, sep))
    else:
        items.extend([parent_key])
    return items

def traverse_directory(directory):
    result = {}
    if directory.endswith('.zip'):
            item_path_extracted = os.path.join(os.path.abspath(os.path.join(directory,"..")),"extrc_"+os.path.basename(directory)[:-4])
            extract_zip(directory, item_path_extracted)
            directory = item_path_extracted
    if os.path.isdir(directory):
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            result[item] = traverse_directory(item_path)
        return result
    else :
        return result

def create_json_structure(zip_path):
    json_structure = {os.path.basename(zip_path):traverse_directory(zip_path)}
    return flatten_json(json_structure)[1:]

def has_zip_child(entity,ancestor_entity):
    child_zips = []
    if entity in ancestor_entity :
        children = ancestor_entity[entity]
        for item in children:
            if item.endswith(".zip") :
                child_zips.append(item)
    return child_zips

def create_table_entries(doc_list,barebones = False):
    headers = ["entity","ancestor","has_zip"]
    ancestor_entity = {}
    entity_ancestor = {}
    table_data = ["  |  ".join(headers)]
    for item in doc_list :
        item_split = item.split(sep)[1:]
        ancestors = sep+sep.join(item_split[:-1]) if len(item_split)>1 else ''
        entity_ancestor[item] = ancestors
    for ent in entity_ancestor :
        anc = entity_ancestor[ent]
        if anc not in ancestor_entity:
            ancestor_entity[anc] = [] 
        ancestor_entity[anc].append(ent)
    for item in doc_list :
        entity = item.split(sep)[1:][-1] if barebones else item
        ancestors = entity_ancestor[item].split(sep)[-1] if barebones else entity_ancestor[item]
        has_zip = has_zip_child(item,ancestor_entity)
        if len(has_zip) == 0 :
            table_data.append("  |  ".join([entity,ancestors,'']))
        else :
            for child in has_zip :
                table_data.append("  |  ".join([entity,ancestors,child.split(sep)[-1] if barebones else child]))
    print(json.dumps(doc_list,indent=1))
    print(json.dumps(entity_ancestor,indent=3))
    print(json.dumps(ancestor_entity,indent=3))
    return table_data
        


@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    temp_dir = tempfile.mkdtemp()
    try:
        temp_file_path = os.path.join(temp_dir, file.filename)
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(await file.read())
        json_structure = create_json_structure(temp_file_path)
        return create_table_entries(json_structure,barebones=barebones)
    finally:
        shutil.rmtree(temp_dir)

@app.post("/upload_view/")
async def upload_file(file: UploadFile = File(...)):
    temp_dir = tempfile.mkdtemp()
    try:
        temp_file_path = os.path.join(temp_dir, file.filename)
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(await file.read())
        json_structure = {os.path.basename(temp_file_path):traverse_directory(temp_file_path)}
        return json_structure
    finally:
        # shutil.rmtree(temp_dir)
        print(temp_dir)
