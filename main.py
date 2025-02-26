import gradio as gr
import pandas as pd
from data_preprocessing import process_data

if not process_data():
    print("Error in data preprocessing. Exiting...")
    exit(1)

from data_handler import agribalyse, bigclimatedata, activities, locations, get_similar_items, get_results
from product_search import create_vector_database, search_top_k
from extraction import get_openai_client, extract_ingredients, extract_prompt, functions
from llm_loop import initialize_chat, chat_response

client = get_openai_client()

encoder, vector_database = create_vector_database(
    activities,
    agribalyse,
    bigclimatedata
)

MAX_INGREDIENTS = 30


def process_recipe(recipe_input, target_country):
    try:
        ingredients_list = extract_ingredients(
            extract_prompt,
            recipe_input,
            client,
            functions
        )['ingredients']
        df = pd.DataFrame(ingredients_list)
        df.columns = ['Ingredient', 'Amount (grams)']
        df['Ingredient'] = df['Ingredient'].str.capitalize()

        ing_opts = get_similar_items(search_top_k, ingredients_list, encoder, vector_database, target_country)
        checkbox_updates = []
        for ingredient, data in ing_opts.items():
            choices = []
            for opt in sorted(set([opt.capitalize() for opt in data['options']])):
                has_country_data = data['availability'].get(opt.lower(), False)
                if has_country_data:
                    choices.append(opt)
                else:
                    choices.append(f"{opt} *")  # Mark with asterisk if no country-specific data
            
            checkbox_updates.append(
                gr.update(
                    visible=True,
                    choices=choices,
                    label=f"{ingredient.capitalize()} ({data['amount']}g)",
                    value=None
                )
            )
        while len(checkbox_updates) < MAX_INGREDIENTS:
            checkbox_updates.append(gr.update(visible=False))

        # Add explanation for asterisk
        status_message = "✅ Ingredients successfully extracted!"
        
        return (
            df,
            gr.update(value=status_message),
            ing_opts,
            True,
            *checkbox_updates
        )
    
    except Exception as e:
        empty_updates = [gr.update(visible=False) for _ in range(MAX_INGREDIENTS)]
        return (
            pd.DataFrame(columns=['Ingredient', 'Amount (grams)']),
            gr.update(value=str(e)),
            {},
            False,
            *empty_updates
        )
    

def process_form(*inputs):
    selections = inputs[:-2]
    ing_opts = inputs[-2]
    country = inputs[-1]

    selected_items = []
    for s in selections:
        if s is None:
            selected_items.append([])
        else:
            selected_items.append(s)
      
    if not any(selected_items):
        return None, None, None
    
    try:
        search_query, results_text = get_results(selected_items, ing_opts, country)
        if not results_text:
            return None, None, None
        
        chat_history, messages, fig_bar, fig_pie = initialize_chat(client, search_query[0]['query'], results_text)
        return chat_history, messages, fig_bar, fig_pie
    
    except Exception as e:
        return None, None, None, None
    

def create_interface():
    with gr.Blocks() as app:
        gr.Markdown("# The Carbon Footprint Wizard")

        with gr.Tabs() as tabs:
            with gr.Tab("Recipe Input"):
                ingredient_options_state = gr.State({})
                gr.Markdown("### 1) Enter Your Recipe")
                with gr.Row():
                    with gr.Column(scale=6):
                        recipe_input = gr.Textbox(
                            label="Enter your recipe with ingredients and their quantities. You can specify quantities in grams, tablespoons, or other measurements.",
                            placeholder="Example: Could you estimate the environmental impact of my veggie pizza? Ingredients: 200g of pizza dough, a tablespoon of tomato paste...",
                            lines=5
                        )
                        countries = sorted(list(set(locations['name'].unique())))
                        target_country = gr.Dropdown(
                            choices=countries,
                            label="Select Target Country",
                            value="Netherlands"
                        )
                        submit_btn = gr.Button("Submit Recipe")
                    with gr.Column(scale=4):
                        status_md = gr.Markdown("Status will appear here...")
                        ingredients_df = gr.Dataframe(
                            headers=['Ingredient', 'Amount (grams)'],
                            interactive=False,
                            wrap=True
                        )
                continue_btn = gr.Button("Continue to Product Selection", visible=False, variant="primary", size="lg")

            with gr.Tab("Product Selection", id="products"):
                product_selection_visible = gr.Checkbox(visible=False)
                product_selection_mrk1 = gr.Markdown("### 2) Select Your Products", visible=False)
                product_selection_mrk2 = gr.Markdown("""
                *Select the most similar products for each ingredient listed. If multiple options are relevant, please choose all that apply to ensure accuracy.*
                
                **Note:** Items marked with an asterisk (*) don't have data specific to the selected country and will use estimates from other countries.
                """, visible=False)
                checkbox_groups = []
                for i in range(MAX_INGREDIENTS):
                    checkbox = gr.CheckboxGroup(
                        label=f"Ingredient {i+1}",
                        choices=[],
                        visible=False
                    )
                    checkbox_groups.append(checkbox)
                submit_selections = gr.Button("Select Products", visible=False, variant="primary")

            with gr.Tab("Chat with Assistant", id="chat"):
                messages_state = gr.State([])
                gr.Markdown("### 3) Carbon Footprint Analysis")
                with gr.Row():
                    impact_plot_bar = gr.Plot(container=False)
                    impact_plot_pie = gr.Plot(container=False)
                chat_history = gr.Chatbot(label="Chat with our Assistant",height=1000)
                with gr.Row():
                    msg = gr.Textbox(placeholder="Your Message",
                            label="",
                            show_label=False,
                            container=True,
                            scale=4
                        )
                    submit_msg = gr.Button("Send",
                            variant="primary",
                            scale=1
                        )

        submit_btn.click(
            fn=process_recipe,
            inputs=[recipe_input, target_country],
            outputs=[
                ingredients_df,
                status_md,
                ingredient_options_state,
                product_selection_visible,
                *checkbox_groups
            ]
        ).then(
            fn=lambda x: [gr.update(visible=x), gr.update(visible=x), gr.update(visible=x), gr.update(visible=x)],
            inputs=[product_selection_visible],
            outputs=[submit_selections, product_selection_mrk1, product_selection_mrk2, continue_btn]
        )

        continue_btn.click(
            fn=lambda: gr.Tabs(selected="products"),
            outputs=[tabs]
        )

        submit_selections.click(
            fn=lambda: gr.Tabs(selected="chat"),
            outputs=[tabs]
        ).then(
            fn=process_form,
            inputs=[*checkbox_groups, ingredient_options_state, target_country],
            outputs=[chat_history, messages_state, impact_plot_bar, impact_plot_pie]
        )


        submit_msg.click(
            fn=lambda message, history: (history + [(message, None)], ""),
            inputs=[msg, chat_history],
            outputs=[chat_history, msg]
        ).then(
            fn=lambda chat_history, messages: chat_response(client, chat_history[-1][0], chat_history[:-1], messages),
            inputs=[chat_history, messages_state],
            outputs=[chat_history, messages_state]
        )

        msg.submit(
            fn=lambda message, history: (history + [(message, None)], ""),
            inputs=[msg, chat_history],
            outputs=[chat_history, msg]
        ).then(
            fn=lambda chat_history, messages: chat_response(client, chat_history[-1][0], chat_history[:-1], messages),
            inputs=[chat_history, messages_state],
            outputs=[chat_history, messages_state]
        )
        
    return app

if __name__ == "__main__":
    demo = create_interface()
    demo.launch()

