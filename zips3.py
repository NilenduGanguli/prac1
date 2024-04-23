import os
import shutil
import tempfile
import zipfile
from fastapi import FastAPI, UploadFile, File
import json

app = FastAPI()
sep = "/"
barebones = False
permissions = 0o777

#security issue
# def extract_zip(zip_file, extraction_path):
#     with zipfile.ZipFile(zip_file, 'r') as zip_ref:
#         zip_ref.extractall(extraction_path)

def extract_zip(zip_file, extraction_path, permissions=None):
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(extraction_path)
        if permissions is not None:
            for root, dirs, files in os.walk(extraction_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    os.chmod(file_path, permissions)

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

#old version
# def traverse_directory(directory):
#     result = {}
#     if directory.endswith('.zip'):
#             item_path_extracted = os.path.join(os.path.abspath(os.path.join(directory,"..")),"extrc_"+os.path.basename(directory)[:-4])
#             print(item_path_extracted)
#             extract_zip(directory, item_path_extracted)
#             directory = item_path_extracted
#     if os.path.isdir(directory):
#         for item in os.listdir(directory):
#             item_path = os.path.join(directory, item)
#             result[item] = traverse_directory(item_path)
#         return result
#     else :
#         return result

def traverse_directory(directory: str,parent_dir:str, flatten_directory :str, dir_struct_map: dict,flat_file_map:dict):
    result = {}
    if directory.endswith('.zip'):
            item_path_extracted = os.path.join(os.path.abspath(os.path.join(directory,"..")),"eexxtt_"+os.path.basename(directory)[:-4])
            extract_zip(directory, item_path_extracted)
            directory = item_path_extracted
    if os.path.isdir(directory):
        if os.path.basename(directory) not in dir_struct_map :
            dir_struct_map[os.path.basename(directory)] = 0
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            # print(dir_struct_map)
            item_rel_path_split = os.path.join(directory,item).split(parent_dir)[-1].split(os.path.sep)
            item_rel_path_list = []
            for rel_path in item_rel_path_split:
                if "eexxtt_" in rel_path:
                    item_rel_path_list.append(rel_path[7:] + ".zip")
                else : 
                    item_rel_path_list.append(rel_path)
            item_rel_path = sep.join(item_rel_path_list)
            item_parent_parts = directory.split(parent_dir)[-1].split(os.path.sep)[1:]
            item_new_name = ""
            if "." in item and not item.endswith(".zip"):
                dir_struct_map[os.path.basename(directory)] += 1
            for parent in item_parent_parts:
                temp_index = str(dir_struct_map[parent]) if dir_struct_map[parent] > 9 else "".join(["0",str(dir_struct_map[parent])])
                item_new_name = item_new_name + temp_index + "_"
            if "." in item and not item.endswith(".zip"):
                item_new_name = item_new_name + item
                flat_file_map[item_rel_path] = item_new_name
            try:
                if not os.path.isdir(item_path) and not item_path.endswith(".zip") : 
                    shutil.copyfile(item_path,os.path.join(flatten_directory,item_new_name))
                    print("Copied " + item_path + " to " + os.path.join(flatten_directory,item_new_name))
            except AttributeError:
                print("Warning: Cannot Copy Entity : "+item_path)
            result[item] = traverse_directory(item_path,parent_dir,flatten_directory,dir_struct_map,flat_file_map)
        return result
    else :
        return result


def create_json_structure(zip_path,flatten_directory):
    dir_struct_map = {}
    parent_dir = os.path.abspath(os.path.join(zip_path,".."))
    flat_file_map = {}
    json_structure = {os.path.basename(zip_path):traverse_directory(zip_path,parent_dir,flatten_directory,dir_struct_map,flat_file_map)}
    print(flat_file_map) ## use to maintain map
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
    # print(json.dumps(doc_list,indent=1))
    # print(json.dumps(entity_ancestor,indent=3))
    # print(json.dumps(ancestor_entity,indent=3))
    return table_data
        


@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    temp_dir = tempfile.mkdtemp()
    temp_flat_dir = tempfile.mkdtemp()
    try:
        temp_file_path = os.path.join(temp_dir, file.filename)
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(await file.read())
        json_structure = create_json_structure(temp_file_path,temp_flat_dir)
        # print(json_structure)
        return create_table_entries(json_structure,barebones=barebones)
    finally:
        shutil.rmtree(temp_dir)
        shutil.rmtree(temp_flat_dir)

@app.post("/upload_view/")
async def upload_file(file: UploadFile = File(...)):
    temp_dir = tempfile.mkdtemp()
    temp_flat_dir = tempfile.mkdtemp()
    try:
        temp_file_path = os.path.join(temp_dir, file.filename)
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(await file.read())
        dir_struct_map = {}
        parent_dir = os.path.abspath(os.path.join(temp_file_path,".."))
        flat_file_map = {}
        json_structure = {os.path.basename(temp_file_path):traverse_directory(temp_file_path,parent_dir,temp_flat_dir,dir_struct_map,flat_file_map)}
        print(flat_file_map) ## use to maintain map
        return json_structure
    finally:
        shutil.rmtree(temp_dir)
        shutil.rmtree(temp_flat_dir)
