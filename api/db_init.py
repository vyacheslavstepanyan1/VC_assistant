import json
from openai import OpenAI
from DLAIUtils import Utils
from pinecone import Pinecone, ServerlessSpec, PineconeApiException
import tqdm
import os
import sys
import time
import threading
import warnings

# Get Environment APIs
utils = Utils()
PINECONE_API_KEY = utils.get_pinecone_api_key()
OPENAI_API_KEY = utils.get_openai_api_key()
pinecone = Pinecone(api_key=PINECONE_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)
INDEX_NAME = 'test'#utils.create_dlai_index_name('vc')


def rotating_slash(delay=0.1):
    """Rotates a slash in the terminal to create a spinning effect."""
    try:
        while True:
            for char in "|/-\\":
                sys.stdout.write('\r' + char)
                sys.stdout.flush()
                time.sleep(delay)
    except KeyboardInterrupt:
        # When interrupted, move to a new line
        sys.stdout.write('\r ')
        sys.stdout.flush()

def animated_loading(prefix="Loading"):
    """Displays an animated loading indicator next to a specified prefix text."""
    chars = "|/-\\"
    idx = 0
    while not stop_thread:
        sys.stdout.write('\r' + prefix + ' ' + chars[idx % len(chars)])
        sys.stdout.flush()
        idx += 1
        time.sleep(0.1)
    # Clear line after finishing
    sys.stdout.write('\r' + ' ' * (len(prefix) + 2) + '\r')
    sys.stdout.flush()

# Global flag to control thread
stop_thread = False

def long_running_operation():
    # Placeholder for a long-running operation
    time.sleep(5)  # Simulate long process


def initialize_db():

    # Create index
    pinecone.create_index(name=INDEX_NAME, dimension=1536, metric='cosine',
        spec=ServerlessSpec(cloud='aws', region='us-east-1'))
    index = pinecone.Index(INDEX_NAME)
    with open('./data/VC_record.json', 'r') as f:
        VC_json = json.loads(f.read())
    def get_embeddings(articles, model="text-embedding-3-small"):
        return openai_client.embeddings.create(input = articles, model=model)
    data = []
    for VC in tqdm.tqdm(VC_json, desc = 'Filling the Database'):
        VC_text = VC['description']
        VC_id = VC['id']
        VC_info = VC['info']
        embedding = get_embeddings(VC_text).data[0].embedding
        data.append({'id': str(VC_id),
                    'values': embedding,
                    'metadata': VC_info}) 
    index.upsert(data)

    return index

def main_init():
    global stop_thread
    init_flag_path = './data/init_flag'
    print('Connecting to database')
    if not os.path.exists(init_flag_path):
        thread = threading.Thread(target=animated_loading, args=("Initializing database",))
        thread.start()
        try:
            index = initialize_db()
            stop_thread = True
            thread.join()
            print('Database initialized')
            with open(init_flag_path, 'w') as f:
                f.write('INITIALIZED')
        except PineconeApiException as e:
            if "Resource  already exists" in e.body:
                stop_thread = True
                thread.join()
                print("\033[93mWARNING\033[0m: VC database already exists. Make sure that it is not empty. If empty, delete it and run the app again.")
                index = pinecone.Index(INDEX_NAME)
                with open(init_flag_path, 'w') as f:
                    f.write('INITIALIZED')
    else:
        if INDEX_NAME in [index.name for index in pinecone.list_indexes()]:
            index = pinecone.Index(INDEX_NAME)
        else:
            thread = threading.Thread(target=animated_loading, args=("Initializing database",))
            thread.start()
            index = initialize_db()
            stop_thread = True
            thread.join()
            print('Database initialized')
        
    # Continue with the rest of your application logic
    print("Starting main application...")

    return index

# if __name__ == '__main__':
#     main_init()
