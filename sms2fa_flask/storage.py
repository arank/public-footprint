import os
import boto3
import uuid
from . import app

def store_file(file_bytes, file_id=None):
    client = boto3.client('s3', 
        endpoint_url = 'https://s3.wasabisys.com',
        aws_access_key_id=app.config['WASABI_ACCESS_KEY'],
        aws_secret_access_key=app.config['WASABI_SECRET_KEY'])
    
    if file_id is None:
        stored_file_id = str(uuid.uuid1())
    else:
        stored_file_id = file_id

    client.put_object(Bucket=app.config['WASABI_BUCKET_NAME'], Key=stored_file_id, Body=file_bytes)
    return stored_file_id

def remove_file(stored_file_id):
    client = boto3.client('s3',
        endpoint_url = 'https://s3.wasabisys.com',
        aws_access_key_id=app.config['WASABI_ACCESS_KEY'],
        aws_secret_access_key=app.config['WASABI_SECRET_KEY'])
    client.delete_object(Bucket=app.config['WASABI_BUCKET_NAME'], Key=stored_file_id)  

def retrieve_file(stored_file_id, local_path='.'):
    client = boto3.client('s3', 
        endpoint_url = 'https://s3.wasabisys.com',
        aws_access_key_id=app.config['WASABI_ACCESS_KEY'],
        aws_secret_access_key=app.config['WASABI_SECRET_KEY'])
    path = local_path+'/'+stored_file_id
    client.download_file(app.config['WASABI_BUCKET_NAME'], stored_file_id, path)
    return path