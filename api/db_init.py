import json
from openai import OpenAI
from DLAIUtils import Utils
from pinecone import Pinecone, ServerlessSpec
import tqdm
import os

def initialize_db():

    # Get Environment APIs
    utils = Utils()
    PINECONE_API_KEY = utils.get_pinecone_api_key()
    OPENAI_API_KEY = utils.get_openai_api_key()
    pinecone = Pinecone(api_key=PINECONE_API_KEY)
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

    # Create index
    INDEX_NAME = utils.create_dlai_index_name('vc')
    if INDEX_NAME in [index.name for index in pinecone.list_indexes()]:
        return None
    else:
        pinecone.create_index(name=INDEX_NAME, dimension=1536, metric='cosine',
            spec=ServerlessSpec(cloud='aws', region='us-east-1'))
        index = pinecone.Index(INDEX_NAME)

    with open('VC_record.json', 'r') as f:
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

def main():
    init_flag_path = './api/data/init_flag'
    if not os.path.exists(init_flag_path):
        initialize_db()
        print('Database initialized')
        # Create a flag file
        with open(init_flag_path, 'w') as f:
            f.write('INITIALIZED')
    else:
        print('Database exists')
    # Continue with the rest of your application logic
    print("Starting main application...")

if __name__ == '__main__':
    main()
