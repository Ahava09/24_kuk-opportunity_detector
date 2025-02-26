import openai

# Remplace par ta clé API
client = openai.OpenAI(api_key="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")

models = client.models.list()
for model in models.data:
    print(model.id)
# Utiliser l'API ChatGPT
# Appel à l'API avec la nouvelle syntaxe
response = client.chat.completions.create(
    model="gpt-3.5-turbo",  
    messages=[
        {"role": "system", "content": "Tu es un assistant utile."},
        {"role": "user", "content": "Bonjour, comment vas-tu ?"}
    ]
)
# Affichage de la réponse
print(response.choices[0].message.content)