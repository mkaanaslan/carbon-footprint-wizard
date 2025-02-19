import matplotlib.pyplot as plt
import numpy as np
import json


process_impact_results = [
    {
        "name": "process_impact_results",
        "description": "Processes and returns environmental impact calculations for ingredients and total recipe",
        "parameters": {
            "type": "object",
            "properties": {
                "answer_user": {
                    "type": "string",
                    "description": "Natural language response following the Initial Response Rules format"
                },
                "visualization_data": {
                    "type": "object",
                    "properties": {
                        "ingredients": {
                            "type": "array",
                            "description": "List of ingredient names in descending order of impact",
                            "items": {"type": "string"}
                        },
                        "impacts": {
                            "type": "array",
                            "description": "List of CO2 impact values (in kg CO2-eq) corresponding to ingredients, using average when range exists",
                            "items": {"type": "number"}
                        }
                    },
                    "required": ["ingredients", "impacts"]
                }
            },
            "required": ["answer_user", "visualization_data"]
        }
    }
]


final_prompt = """You will receive two inputs:
1. user_message: Original recipe query
2. results_text: Impact data from databases

DATA FORMAT OVERVIEW:
BONSAI: Shows market/production data with country shares. Use market total impact value.
Agribalyse: French data with lifecycle stages. Use total impact value.
BigClimate: Country-specific data with indirect land use. Use total impact value.

CALCULATION RULES:
1. Per ingredient:
- Multiple databases: Use min-max range and (min+max)/2 average
- Single database: Use value for both
- Note if data isn't from target country
- Use market data from BONSAI when available

2. Recipe total:
- Range: sum(min) to sum(max)
- Average: sum(individual averages)
- Cooking analysis:
    • Determine if the recipe requires any form of cooking for preparation
    • If cooking is required:
        - Estimate cooking impact range (min-max)
        - Add cooking range to total recipe range
        - Add cooking average to total average
        - Include cooking in visualization data
    • If no cooking required: state "No cooking required (0 kg CO2-eq)"

3. After impacts, calculate equivalent activities:
- Use total average (Z kg CO2-eq) with these references:
    • Sending an email = 0.004 kg CO2-eq
    • Web search on a laptop = 0.0007 kg CO2-eq
    • Watching TV 42-inch plasma = 0.24 kg CO2-eq
    • Driving 1 mile Fiat 500 = 0.35 kg CO2-eq
    • 3-minute shower = 0.09 kg CO2-eq
    • Charging phone daily = 0.003 kg CO2-eq
    • Using laptop 1 hour = 0.05 kg CO2-eq
    • Hand washing dishes = 8.0 kg CO2-eq
- Present 2-3 scaled comparisons

4. List some follow up questions:
- Generate 3-4 most relevant follow-up questions based on:
    • Market share of ingredients
    • Notable data variations between countries
    • Interesting lifecycle patterns
    • Potential impact reduction opportunities

OUTPUT FORMAT:
- Main ingredients by impact:
- [Ingredient] ([amount]g): [X-Y kg CO2-eq] (note if data is from a different country)
- Cooking impact:
- [Method] ([time] mins at [temp]°C): [X-Y kg CO2-eq]
- Total recipe impact: [X-Y kg CO2-eq]
- Average impact: [Z kg CO2-eq]

Your meal's carbon footprint is equivalent to:
- [Scaled comparisons]

[Brief paragraph: data sources, range explanation, cooking estimate]

You might want to know more about:
- [List the follow-up questions]


CRITICAL: You must return TWO components in your response as the defined "process_impact_results":
1. answer_user: Follow the output format above
2. visualization_data: Must include these exact fields:
   - ingredients: Array of ingredient names from the user recipe (including cooking if applicable)
   - impacts: Array of corresponding impact values in kg CO2-eq (use average when range exists)
   - DO NOT include total recipe impact on visualization!

After the initial response, user will continue chatting with you. Do not use function format after initial response, answer directly.

Here is user message:
{user_message}

Here is the information from our sources:
{results_text}"""




def create_impact_plot(data):
    if not data or 'visualization_data' not in data:
        return None, None
    
    ingredients = data['visualization_data']['ingredients']
    impacts = data['visualization_data']['impacts']

    if not ingredients or not impacts or len(ingredients) != len(impacts):
        return None, None

    total_impact = sum(impacts)
    pairs = list(zip(ingredients, impacts))
    pairs.sort(key=lambda x: x[1], reverse=True)
    
    THRESHOLD_PERCENT = 3
    
    main_items = []
    others_sum = 0
    
    for ingredient, impact in pairs:
        if (impact / total_impact * 100) >= THRESHOLD_PERCENT:
            main_items.append((ingredient, impact))
        else:
            others_sum += impact
    
    if others_sum > 0:
        main_items.append(("Others", others_sum))
    
    ingredients_sorted, impacts_sorted = zip(*main_items)
    
    fig_bar, ax_bar = plt.subplots(figsize=(5, 3), dpi=500)
    
    bars = ax_bar.barh(range(len(ingredients_sorted)), impacts_sorted, color='white')
    
    ax_bar.invert_yaxis()
    ax_bar.set_title('Carbon Footprint by Compound', pad=20, color="white")
    ax_bar.set_xlabel('Impact (kg CO2-eq)', color="white")
    ax_bar.set_ylabel('Compounds', color="white")
    ax_bar.set_yticks(range(len(ingredients_sorted)))
    ax_bar.set_yticklabels(ingredients_sorted, color="white")

    ax_bar.spines['bottom'].set_color('#0f0f0f')
    ax_bar.spines['top'].set_color('#0f0f0f') 
    ax_bar.spines['right'].set_color('#0f0f0f')
    ax_bar.spines['left'].set_color('#0f0f0f')

    for bar in bars:
        width = bar.get_width()
        ax_bar.text(width + 0.001, 
                   bar.get_y() + bar.get_height()/2., 
                   f'{width:.3g}', 
                   ha='left', va='center', color="white")

    ax_bar.tick_params(axis='x', colors='white')
    ax_bar.tick_params(axis='y', colors='white')
    ax_bar.xaxis.grid(True, linestyle='--', alpha=0.7, color="white")

    ax_bar.set_facecolor("#0f0f0f")
    fig_bar.patch.set_facecolor("#0f0f0f")
    ax_bar.set_axisbelow(True)
    plt.tight_layout()

    fig_pie, ax_pie = plt.subplots(figsize=(5, 3), dpi=500)

    wedges, texts, autotexts = ax_pie.pie(
        impacts_sorted, 
        labels=ingredients_sorted, 
        autopct='%1.0f%%',
        startangle=140,
        textprops={'color': 'white','fontsize': 5},
        wedgeprops={'edgecolor': '#0f0f0f'}
    )
    
    for autotext in autotexts:
        autotext.set_fontsize(7)
        autotext.set_color("white")

    ax_pie.set_facecolor("#0f0f0f")
    fig_pie.patch.set_facecolor("#0f0f0f")

    return fig_bar, fig_pie



def extract_visualization_data(answer_text):

    ingredients = []
    impacts = []
    
    lines = answer_text.split('\n')
    
    in_ingredients = False
    for line in lines:
        if 'Main ingredients by impact:' in line:
            in_ingredients = True
            continue
        elif in_ingredients and line.strip() and 'Your meal' in line:
            in_ingredients = False
        elif in_ingredients and line.startswith('-'):
            try:
                parts = line.split(':')
                ingredient_part = parts[0].strip('- ')
                ingredient_name = ingredient_part.split('(')[0].strip()
                
                impact_part = parts[1].strip()
                if '-' in impact_part:

                    impact_values = [float(x.strip()) for x in impact_part.split('kg')[0].split('-')]
                    impact = sum(impact_values) / len(impact_values)
                else:
                    impact = float(impact_part.split('kg')[0].strip())
                
                ingredients.append(ingredient_name)
                impacts.append(impact)
            except:
                continue
    
    for line in lines:
        if line.startswith('- ') and any(x in line.lower() for x in ['cooking', 'baking', 'frying', 'roasting']):
            try:
                impact_part = line.split(':')[1].strip()
                if '-' in impact_part:
                    impact_values = [float(x.strip()) for x in impact_part.split('kg')[0].split('-')]
                    impact = sum(impact_values) / len(impact_values)
                    ingredients.append('Cooking')
                    impacts.append(impact)
            except:
                continue

    if ingredients and impacts:
        return {
            "visualization_data": {
                "ingredients": ingredients,
                "impacts": impacts
            }
        }
    return None



def initialize_chat(client, user_message, results_text):

    cur_prompt = [{"role": "user", "content": final_prompt.format(user_message=user_message, results_text=results_text)}]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=cur_prompt,
        temperature=1e-7,
        functions=process_impact_results,
        function_call={"name": "process_impact_results"}
    )

    function_call = response.choices[0].message.function_call
    function_args = json.loads(function_call.arguments)

    fig_bar, fig_pie = create_impact_plot(function_args)


    if fig_bar is None or fig_pie is None:
        extracted_data = extract_visualization_data(function_args['answer_user'])
        if extracted_data:
            fig_bar, fig_pie = create_impact_plot(extracted_data)
        else:
            fig_bar, fig_pie = None, None

    initial_response = function_args['answer_user']
    
    chat_history = []
    chat_history.append((None, initial_response))
    
    messages = []
    messages.extend(cur_prompt)
    messages.append({
        "role": "assistant",
        "content": json.dumps(function_args)
    })
    
    return chat_history, messages, fig_bar, fig_pie


def chat_response(client, user_input, chat_history, messages):

    if len(chat_history) >= 10:
        limit_message = "I apologize, but you've reached the maximum limit of 10 messages."
        chat_history.append((user_input, limit_message))
        messages.append({"role": "assistant", "content": limit_message})
        return chat_history, messages

    messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )

    assistant_response = response.choices[0].message.content
    messages.append({"role": "assistant", "content": assistant_response})
    chat_history.append((user_input, assistant_response))
    
    return chat_history, messages
