#### Installation

###### Install Python dependencies:

```bash
pip install -r requirements.txt
```

###### Install JavaScript dependencies:

First:
```bash
cd ..
```
Then:
```bash
cd client
```

Then:
```bash
npm install
```

#### Run

###### Run the server:

```bash
cd ../api
uvicorn main:app --reload --port 8000
```

###### Run the client:

Then:
```bash
npm start
```
