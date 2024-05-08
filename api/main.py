from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from fastapi.responses import StreamingResponse
from pinecone import Pinecone, ServerlessSpec
from DLAIUtils import Utils
import functions as func
import json
from dotenv import load_dotenv
import db_init

index = db_init.main_init()

load_dotenv()

class Envs(BaseSettings):
    openai_api_key: str
    pinecone_api_key: str
    class Config:
        env_file = ".env"

envs = Envs()
utils = Utils()

openai_client = OpenAI(api_key=envs.openai_api_key)
pinecone = Pinecone(api_key=envs.pinecone_api_key)

tools = func.tools

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Stream Response
def get_streamed_ai_response(response):
    try:
        for chunk in response: 
            yield chunk.choices[0].delta.content or ""

    except StopIteration:
        return

class Message(BaseModel):
    role: str
    content: str


# Send message to GPT, communication logic
@app.post("/message")
async def send_message(messages: List[Message], background_tasks: BackgroundTasks):

    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[message.dict() for message in messages],
        stream=True,
        tools = tools,
        tool_choice='auto'
    )

    first_chunk = next(response)
    tool_name = func.check_toolcall(first_chunk)

    # Check if tool was used
    if tool_name:
            
        VC_records = func.read_vc_records()

        if tool_name == 'parse_link':
            link = ''
            # Load the link from stream response
            for chunk in response:
                if chunk.choices[0].delta.tool_calls:
                    if argument := chunk.choices[0].delta.tool_calls[0].function.arguments or "":
                        link += argument
            link_data = json.loads(link)
            link = link_data['link']

            for record in VC_records:
                if record['link'] == link:
                    VC_info = record['info']
                    VC_id = str(record['id'])
                    # VC_emb = index.fetch(ids=VC_id)
                    matches = func.get_similar(id = VC_id,top_k = 4)
                    matches = matches['matches'][1:]
                    sim_names = [match['metadata']['name'] for match in matches]
                    response = func.give_info(VC_info, sim_names)
                    return StreamingResponse(get_streamed_ai_response(response), media_type='text/event-stream')

            # Load text from link. Ask to check the link if unavailable.
            try:
                text,_ = func.get_text_links(link)
            except Exception:
                response = func.ask_check_link()
                return response
            
            # Extract information. Write to local record and vectorDB.
            response = await func.find_info(text)
            VC_info = response.choices[0].message.tool_calls[0].function.arguments
            
            # Generate better description and write to DB and records on background to minimize response delay
            background_tasks.add_task(func.write_record, record["id"]+1, link, text, VC_info, index)

            VC_desc = (func.write_description(text)).choices[0].message.content
            VC_emb = (func.get_embeddings(VC_desc)).data[0].embedding
            matches = func.get_similar(embedding=VC_emb, top_k = 3)
            matches = matches['matches']
            sim_names = [match['metadata']['name'] for match in matches]
            response = func.give_info(VC_info, sim_names)
            return StreamingResponse(get_streamed_ai_response(response), media_type='text/event-stream')
        
        elif tool_name == 'parse_name':
            name = ''
            # Load the name from stream response
            for chunk in response:
                if chunk.choices[0].delta.tool_calls:
                    if argument := chunk.choices[0].delta.tool_calls[0].function.arguments or "":
                        name += argument
            name_data = json.loads(name)
            name = name_data['name']

            # Open records and check if link in records
            for record in VC_records:
                if record['info']['name'].replace(" ", "").lower() == name.replace(" ", "").lower():
                    VC_info = record['info']
                    VC_id = str(record['id'])
                    matches = func.get_similar(id = VC_id, top_k = 4)
                    matches = matches['matches'][1:]
                    sim_names = [match['metadata']['name'] for match in matches]
                    response = func.give_info(VC_info, sim_names)
                    return StreamingResponse(get_streamed_ai_response(response), media_type='text/event-stream')
                
            # Ask for link if name was not found
            response = func.ask_link()
            return StreamingResponse(get_streamed_ai_response(response), media_type='text/event-stream')

    else:
        return StreamingResponse(get_streamed_ai_response(response), media_type='text/event-stream')