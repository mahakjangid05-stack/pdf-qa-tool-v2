import os
from dotenv import load_dotenv
import anthropic

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def build_prompt(question, chunks):
    context = "\n\n".join(chunks)
    return f"""Answer the question using ONLY the context below.
If the answer is not in the context, say: "I couldn't find this in the document."

Context:
{context}

Question: {question}"""


def ask_claude(question, chunks):
    if not chunks:
        return "I couldn't find this in the document."

    response = client.messages.create(
        model="claude-sonnet-5-5",
        max_tokens=1000,
        messages=[{"role": "user", "content": build_prompt(question, chunks)}],
    )
    return response.content[0].text


if __name__ == "__main__":
    test_chunks = ["Alphonse Daudet was a French novelist born in 1840."]
    print(ask_claude("Who is Alphonse Daudet?", test_chunks))