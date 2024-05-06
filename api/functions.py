from openai import OpenAI
import requests
import json
import requests
from bs4 import BeautifulSoup
from pydantic_settings import BaseSettings
from DLAIUtils import Utils
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

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

INDEX_NAME = utils.create_dlai_index_name('vc')
if INDEX_NAME in [index.name for index in pinecone.list_indexes()]:
  index = pinecone.Index(INDEX_NAME)
else:
  pinecone.create_index(name=INDEX_NAME, dimension=1536, metric='cosine',
    spec=ServerlessSpec(cloud='aws', region='us-east-1'))
  index = pinecone.Index(INDEX_NAME)

tools = [
    {
    "type": "function",
    "function": {
        "name": "parse_link",
        "description": "Get link of VC to extract information and put it in standatized form",
        "parameters": {
            "type": "object",
            "properties": {
                "link": {
                    "type": "string",
                    "description": "The link of VC firm, it must be in the format https://www.a16z.com/. IMPORTANT TO INCLUDE 'https' and 'www'",
                }
             },
            "required": ["link"],
            },
        }
    },
        {
    "type": "function",
    "function": {
        "name": "parse_name",
        "description": "Get information about VC by name",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "name of the VC that user wrote asked for",
                }
             },
            "required": ["name"],
            },
        }
    }
]

def fetch_html(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser')
        else:
            print(f"Failed to fetch {url}: Status code {response.status_code}")
            return None
    except requests.RequestException as e:
        raise Exception(f"""Failed to read the website\n\nError: {e}""")
        return None
    
def extract_clean_text(soup):
    
    # Remove script and style elements
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()
    
    # Get text
    text = soup.get_text(separator=' ', strip=True)
    
    # Break into lines and remove leading and trailing space on each
    lines = (line.strip() for line in text.splitlines())
    # Break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # Drop blank lines
    text = '\n'.join(chunk for chunk in chunks if chunk)

    return text

def extract_unique_urls(soup):
    unique_urls = set()  # Use a set to store unique URLs

    if soup:
        links = soup.find_all('a')  # Find all anchor tags
        for link in links:
            href = link.get('href', None)  # Extract href attribute
            if href:  # Check if href is not None
                unique_urls.add(href)  # Add href to the set

    return list(unique_urls)  # Convert the set of unique URLs to a list and return it

def check_toolcall(chunk):
    # Here 'chunk' is already a ChatCompletionChunk object
    if chunk.choices[0].delta.tool_calls:
        return chunk.choices[0].delta.tool_calls[0].function.name
    return None
    
def get_text_links(link):

    site = fetch_html(link)
    if site != None:
        text = extract_clean_text(site)
        links = extract_unique_urls(site)
        if text and links:
            return text, links
        elif text:
            return text, None
        elif link:
            return None, text
        else:
            return None, None
    else:
        raise Exception(f"Site not found on {link}")

def find_info(text):
    messages = []
    messages.append({"role": "system", "content": "Find information about VC. Find VC name, contacts, industries that they invest in, investment rounds that they participate/lead. Don't make assumptions."})
    messages.append({"role": "user", "content": text})
    chat_response = openai_client.chat.completions.create(
        model="gpt-4-turbo",
        messages=messages,
        # stream=True,
        tools = [{"type": "function","function": {"name": "get_vc_info","description": "Extracts detailed information about a Venture Capital firm from given text. Fill only if values are present.","parameters": {"type": "object","properties": {"name": {"type": "string","description": "Name of the Venture Capital firm, e.g., Greylock Partners."},"contacts": {"type": "array","items": {"type": "string"},"description": "Contact information, e.g., phone : +48540234, email: myemail@mail.com, LinkedIn. : linkedin.com/username. KEEP THE FROMAT FROM EXAMPLE"},"investment_industries": {"type": "array","items": {"type": "string"},"description": "List of industries that the company invests in."},"investment_rounds": {"type": "array","items": {"type": "string"},"description": "List of investment rounds that they participate/lead."}}}}}],
        tool_choice={"type": "function","function": {"name": "get_vc_info","description": "Extracts detailed information about a Venture Capital firm from given text. Fill only if values are present.","parameters": {"type": "object","properties": {"name": {"type": "string","description": "Name of the Venture Capital firm, e.g., Greylock Partners."},"contacts": {"type": "array","items": {"type": "string"},"description": "Contact information, e.g., phone : +48540234, email: myemail@mail.com, LinkedIn. : linkedin.com/username. KEEP THE FORMAT FROM EXAMPLE"},"investment_industries": {"type": "array","items": {"type": "string"},"description": "List of industries that the company invests in."},"investment_rounds": {"type": "array","items": {"type": "string"},"description": "List of investment rounds that they participate/lead."}}}}}
        )
    return chat_response

def add_info(text, info, subject):
    messages = []
    messages.append({"role": "system", "content": f"Add information to {subject} of {info} from user input. Don't make assumptions. Reply in JSON format in codeblock"})
    messages.append({"role": "user", "content": text})
    chat_response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        tools = None,
        response_format={ "type": "json_object" },
    )
    return chat_response

def give_info(info,sim):
    messages = []
    messages.append({"role": "system", "content": f"Tell the user that you found the following information and show it in JSON format {info} in codeblock. Also tell that these are top 3 similar companies {sim} in bulletpoints"})
    chat_response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        stream = True
    )
    return chat_response

def validate_vc_info(input_data):

    required_fields = ["name", "contacts", "investment_industries", "investment_rounds"]
    missing_fields = [field for field in required_fields if (field not in input_data)]
    return missing_fields

def find_links(missings, links):

    messages = []
    links_str = ', '.join(links)
    messages.append({"role": "system", "content": f"Find the matching links"})
    messages.append({"role": "user", "content": f"Find links that have the needed content. Links -> {links_str}"})
    chat_response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages, 
        tools=tools,
        tool_choice=tools[2]
    )
    names_links = json.loads(chat_response.choices[0].message.tool_calls[0].function.arguments)
    required_names_links = {key:value for (key, value) in names_links.items() if key in missings}

    return required_names_links

def write_description(text,model = 'gpt-3.5-turbo'):
    messages = []
    messages.append({"role": "system", "content": "Write a description of VC company based on given text"})
    messages.append({"role": "user", "content": text})
    chat_response = openai_client.chat.completions.create(
        model=model,
        messages=messages
        )
    return chat_response

def get_embeddings(articles, model="text-embedding-3-small"):
   return openai_client.embeddings.create(input = articles, model=model)

def get_similar(embedding = None, top_k = 3, id = None):
    if id != None:
        res = index.query(id = id, top_k=top_k, include_metadata=True)
    else:
        res = index.query(vector=embedding, top_k=top_k, include_metadata=True)
    return res

def ask_link():
    messages = []
    messages.append({"role": "system", "content": f"You didn't can't find information about that VC by name. Ask for a link of the VC website"})
    chat_response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        stream = True
    )
    return chat_response

def ask_check_link():
    messages = []
    messages.append({"role": "system", "content": f"Ask user to check if the link was correct. Suggest to try to put the link in this format 'https://www.yourbestvcassistant.com/"})
    chat_response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        stream = True
    )
    return chat_response

async def write_record(record_id, link, text, VC_info, index):

    with open("VC_record.json", "r") as VC_json:
        VC_records = json.load(VC_json)

    # Avoid dublicate write even if somehow appeared here
    for record in VC_records:
        if record["link"] == link:
            return

    gpt4_response = write_description(text, model="gpt-4")
    VC_desc_gpt4 = gpt4_response.choices[0].message.content
    VC_emb = (get_embeddings(VC_desc_gpt4)).data[0].embedding
    VC_info = json.loads(VC_info)

    VC_record = {
        "id" : record_id,
        "link" : link,
        "description" : VC_desc_gpt4,
        "info" : VC_info
    }

    # Update the record and upload to database
    VC_records.append(VC_record)
    index.upsert([(str(record_id), VC_emb, VC_info)])

    with open("VC_record.json", "w") as VC_json:
        json.dump(VC_records, VC_json, indent=4)