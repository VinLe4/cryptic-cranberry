import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def create_vector_store(name="OptiSigns Vector Store", metadata=None):
    response = client.vector_stores.create(
        name=name,
        metadata=metadata or {"source": "optibot", "env": "local"}
    )
    return response.id

def update_env(vector_store_id):
    env_path = ".env"
    lines = []

    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()

    lines = [line for line in lines if not line.startswith("VECTOR_STORE_ID=")]
    lines.append(f"VECTOR_STORE_ID={vector_store_id}\n")

    with open(env_path, "w") as f:
        f.writelines(lines)

if __name__ == "__main__":
    vs_id = create_vector_store()
    update_env(vs_id)
