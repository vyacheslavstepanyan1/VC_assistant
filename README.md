
# VC assistant app
This is an assistant that can help you to find information about VC companies and find similar companies from database.

## Installation and Running
You can install and run this app locally or using [Docker](https://www.docker.com/)

### Local
#### Move to backend directory:
```bash

cd  api

```

#### Create Python virtual Environment:
```bash

python  -m  venv  .venv

.venv/Scrpts/activate #windows

source .venv/bin/activate #mac

```

#### Install Python dependencies:
```bash

cd  api

pip  install  -r  requirements.txt

```
#### Move to frontend directory:
```bash

cd  ../client

```

#### Install JavaScript dependencies:
```bash

npm  install

```
#### Run the server:
```bash

cd  ../api

uvicorn  main:app  --reload  --port  8000

```
#### Run the client:

```bash

npm  start

```

### Docker

#### Compose docker multi-container
```bash

docker-compose up --build

```

#### Run Docker
```bash

docker-compose up

```

### Environemnt
To be able to run the application you will need to create and environment .env in api folder.


```bash

OPENAI_API_KEY = 'YOUR API KEY HERE'
PINECONE_API_KEY = 'YOUR API KEY HERE'


```


After these steps either for local or docker, the application is available to be used locally on http://localhost:3000
Also you can see the backend on http://localhost:8000 and check FastAPI on http://localhost:3000/#docs

### P.S.
You may find some unnecessary functions defined. Those are for future work.