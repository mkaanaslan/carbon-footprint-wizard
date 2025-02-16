import openai
import json
import os

extract_prompt = """Extract the ingredients and their quantities from the following user message.

If the quantities are provided in units other than grams (such as tablespoons, cups, or pieces), convert them to a reasonable weight in grams based on typical measurements.

You can directly change milliliters to grams.

Provide the ingredients and quantities in the format required by the function 'process_ingredients'.

User Message: {user_message}
"""



functions = [
    {
        "name": "process_ingredients",
        "description": "Extracts and returns a list of ingredients and their quantities in grams from a user's message, converting units to grams where necessary using standard approximations.",
        "parameters": {
            "type": "object",
            "properties": {
                "ingredients": {
                    "type": "array",
                    "description": "An array of ingredient objects, each containing the ingredient's name and quantity in grams.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "The name of the ingredient as mentioned in the user's message."
                            },
                            "quantity": {
                                "type": "number",
                                "description": "The quantity of the ingredient in grams as a numeric value (without units)."
                            }
                        },
                        "required": ["name", "quantity"]
                    }
                }
            },
            "required": ["ingredients"]
        }
    }
]


def get_openai_client():
    key_path = 'openai_key.txt'
    if not os.path.exists(key_path):
        with open(key_path, 'w') as f:
            f.write(input('Please enter your OpenAI API key: ').strip())
    with open('openai_key.txt', 'r') as file:
        key = file.read()
    openai.api_key = key
    return openai.OpenAI(api_key=openai.api_key)


def extract_ingredients(extract_prompt, user_message, client, functions):
    cur_prompt = [{"role": "user", "content": extract_prompt.format(user_message=user_message)}]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=cur_prompt,
        temperature=1e-7,
        functions=functions,
        function_call={"name": "process_ingredients"}
    )

    function_call = response.choices[0].message.function_call
    function_args = json.loads(function_call.arguments)

    return function_args


